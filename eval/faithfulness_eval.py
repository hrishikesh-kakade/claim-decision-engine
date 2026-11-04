"""Citation correctness / faithfulness checks.

1. NUMERIC SUPPORT (deterministic): checks whether every number in a
   citation's claim text also appears in the cited policy chunk.
   Score = supported / checked unique claim-chunk pairs containing numbers.
   This checks numeric presence, not semantic correctness.

2. LLM-AS-JUDGE (optional, --llm-judge): an LLM evaluates whether the
   cited excerpt supports the claim. Results are estimates, not ground truth.
   Review unsupported examples manually.

3. NARRATION GUARDRAIL (optional, --narration): checks whether generated
   narration preserves every number from the deterministic finding it rephrases.
   This evaluates narration reliability, not citation correctness.
"""
from __future__ import annotations

import argparse
import json
import re

import common

NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WORD_RE = re.compile(r"[A-Za-z]{4,}")
STOP = {"with", "that", "this", "from", "under", "over", "into", "than", "which", "where", "when",
        "such", "each", "only", "have", "been", "will", "their", "other", "these", "shall", "sum", "insured"}

JUDGE_SYSTEM = (
    "You are a strict insurance-policy auditor. Evaluate whether the POLICY EXCERPT "
    "fully supports the CLAIM. The excerpt is the only source of truth. "
    "Check every material assertion, including amounts, percentages, limits, "
    "time periods, conditions, exceptions, definitions, and qualifiers. "
    "A claim is supported only if all its material details are supported by the excerpt. "
    "Mark it unsupported if it omits a material restriction, overstates coverage, "
    "changes a condition, or uses terminology not established as equivalent by the excerpt. "
    "Do not assume that Sum Insured, Basic Sum Insured, and Sum Assured are interchangeable. "
    "Do not use outside knowledge or infer missing policy terms. "
    "If the excerpt supports only part of the claim, mark it unsupported. "
    "Answer with ONLY valid JSON in this format: "
    '{"supported": true or false, "reason": "brief explanation, max 20 words"}.'
)


def numbers(text: str) -> set[float]:
    return {float(x) for x in NUM_RE.findall(text.replace(",", ""))}


def numbers_preserved(original: str, rephrased: str) -> bool:
    return numbers(original) <= numbers(rephrased)

def parse_judge(text: str | None):
    result = parse_judge_detail(text)
    return result["supported"] if result is not None else None


def parse_judge_detail(text: str | None) -> dict | None:
    if not text:
        return None

    m = re.search(r"\{.*?\}", text, re.DOTALL)
    if not m:
        return None

    try:
        result = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

    supported = result.get("supported")
    if not isinstance(supported, bool):
        return None

    reason = result.get("reason")
    return {
        "supported": supported,
        "reason": reason if isinstance(reason, str) else None,
    }


def load_chunks() -> dict[str, str]:
    return {
        c["chunk_id"]: c["text"]
        for c in json.loads(common.CHUNKS.read_text(encoding="utf-8"))
    }


def unique_pairs(responses: list[dict]) -> list[tuple[str, str]]:
    return sorted({(c["claim"], c["chunk_id"]) for r in responses for c in r["citations"]})


def deterministic(responses: list[dict], chunks: dict[str, str]) -> dict:
    pairs = unique_pairs(responses)
    n_total = sum(len(r["citations"]) for r in responses)
    unresolved, failures = [], []
    num_checked = num_ok = 0
    for claim, cid in pairs:
        text = chunks.get(cid)
        if text is None:
            unresolved.append({"claim": claim, "chunk_id": cid}); continue
        nums = numbers(claim)
        if nums:
            num_checked += 1
            if nums <= numbers(text):
                num_ok += 1
            else:
                failures.append({"claim": claim, "chunk_id": cid, "numbers_missing_from_chunk": sorted(nums - numbers(text))})

    return {"citations_total": n_total, "unique_claim_chunk_pairs": len(pairs), "unresolvable_chunk_ids": len(unresolved),
            "numeric_checked": num_checked, "numeric_supported": num_ok,
            "numeric_support_rate": num_ok / num_checked if num_checked else None,
            "numeric_failures": failures}


def make_llm_judge():
    from backend.llm import LLMClient
    client = LLMClient()
    if not client.available:
        return None

    def judge(claim: str, excerpt: str):
        response = client.complete(
            JUDGE_SYSTEM,
            f"POLICY EXCERPT:\n{excerpt[:1500]}\n\nCLAIM:\n{claim}",
            max_tokens=400,
        )
        return parse_judge_detail(response)

    judge.client = client
    return judge


def llm_judge(
    responses: list[dict],
    chunks: dict[str, str],
    judge=None,
    max_pairs: int | None = None,
) -> dict:
    judge = judge or make_llm_judge()
    if judge is None:
        return {"skipped": "no LLM configured (set GROQ_API_KEY / LLM_PROVIDER)"}

    eligible = [
        p for p in unique_pairs(responses)
        if p[1] in chunks
    ]
    pairs = eligible[:max_pairs]

    yes = no = unparsed = 0
    results = []

    for claim, cid in pairs:
        raw = judge(claim, chunks[cid])

        if isinstance(raw, dict):
            verdict = raw.get("supported")
            reason = raw.get("reason")
        else:
            verdict = raw if isinstance(raw, bool) else None
            reason = None

        if verdict is True:
            yes += 1
        elif verdict is False:
            no += 1
        else:
            unparsed += 1

        results.append({
            "claim": claim,
            "chunk_id": cid,
            "supported": verdict,
            "reason": reason,
        })

    judged = yes + no
    client = getattr(judge, "client", None)
    call_info = getattr(client, "last_call_info", {})

    return {
        "eligible_pairs": len(eligible),
        "pairs": len(pairs),
        "judged": judged,
        "supported": yes,
        "unsupported_count": no,
        "unparseable": unparsed,
        "evaluation_coverage": judged / len(eligible) if eligible else None,
        "parse_rate": judged / len(pairs) if pairs else None,
        "faithfulness": yes / judged if judged else None,
        "provider": call_info.get("provider"),
        "model": call_info.get("model"),
        "unsupported": [
            r for r in results if r["supported"] is False
        ],
        "results": results,
    }


def narration_check(engine, cases: list[dict], responses: list[dict], narrate_fn=None) -> dict:
    from backend.agents.case_analysis import analyze_case
    from backend.agents.coverage_exclusion import assess
    from backend.agents.llm_writer import get_client, narrate_findings
    from backend.models import ClaimCase
    if narrate_fn is None:
        if not get_client().available:
            return {"skipped": "no LLM configured (set GROQ_API_KEY / LLM_PROVIDER)"}
        narrate_fn = narrate_findings
    attempted = accepted = lines_total = lines_ok = 0
    errors: dict[str, int] = {}
    for raw, resp in zip(cases, responses):
        case = ClaimCase.model_validate(raw)
        cov = assess(case, analyze_case(case), engine.policy_params)
        lines, info = narrate_fn(cov.findings, resp["decision"])
        attempted += 1
        if lines is None:
            key = (info or {}).get("error") or "unknown"
            errors[key[:90]] = errors.get(key[:90], 0) + 1
            continue
        accepted += 1
        for f, line in zip(cov.findings, lines):
            lines_total += 1
            lines_ok += numbers_preserved(f.statement, line)
    return {"attempted": attempted, "accepted_by_guardrail": accepted,
            "acceptance_rate": accepted / attempted if attempted else None,
            "lines_checked": lines_total, "numbers_preserved": lines_ok,
            "number_preservation_rate": lines_ok / lines_total if lines_total else None, "rejection_reasons": errors}


def to_markdown(det: dict, judge: dict | None = None, narr: dict | None = None) -> str:
    f = common.fmt

    L = [
        f"- Numeric consistency check: **{det['numeric_supported']}/{det['numeric_checked']}** "
        f"unique claim/chunk pairs with numbers pass the number-presence check "
        f"({f(det['numeric_support_rate'])})",
        f"- Unresolvable chunk ids: {det['unresolvable_chunk_ids']} "
        f"(of {det['unique_claim_chunk_pairs']} unique claim/chunk pairs, "
        f"{det['citations_total']} citations total)",
    ]

    for fl in det["numeric_failures"]:
        L.append(
            f"  - FAIL: \"{fl['claim']}\" cites {fl['chunk_id']} "
            f"but {fl['numbers_missing_from_chunk']} not in chunk"
        )

    if judge:
        if "skipped" in judge:
            L.append(f"- LLM-judge faithfulness: {judge['skipped']}")
        else:
            L.append(
                f"- LLM-judge faithfulness: **{judge['supported']}/{judge['judged']} "
                f"= {f(judge['faithfulness'])}**"
            )
            L.append(
                f"  - Evaluation coverage: {judge['judged']}/{judge['eligible_pairs']} "
                f"eligible pairs ({f(judge['evaluation_coverage'])})"
            )
            L.append(
                f"  - Parse rate: {f(judge['parse_rate'])} "
                f"({judge['judged']}/{judge['pairs']} attempted pairs parsed)"
            )
            L.append(
                f"  - Unsupported: {judge['unsupported_count']}; "
                f"unparseable: {judge['unparseable']}"
            )

            provider = judge.get("provider")
            model = judge.get("model")
            if provider or model:
                L.append(
                    f"  - LLM configuration: provider={provider or 'unknown'}, "
                    f"model={model or 'unknown'}"
                )

            for u in (judge.get("unsupported") or [])[:5]:
                reason = u.get("reason")
                detail = f" — {reason}" if reason else ""
                L.append(
                    f"  - Judged unsupported: \"{u['claim']}\" "
                    f"-> {u['chunk_id']}{detail} (verify by hand)"
                )

            unparsed_results = [
                r for r in judge.get("results", [])
                if r.get("supported") is None
            ]
            for u in unparsed_results[:5]:
                L.append(
                    f"  - Unparseable verdict: \"{u['claim']}\" "
                    f"-> {u['chunk_id']}"
                )

    if narr:
        L.append(
            "- LLM narration guardrail: "
            + (
                narr["skipped"]
                if "skipped" in narr
                else (
                    f"{narr['accepted_by_guardrail']}/{narr['attempted']} responses "
                    f"accepted ({f(narr['acceptance_rate'])}); "
                    f"numbers preserved in {narr['numbers_preserved']}/"
                    f"{narr['lines_checked']} lines "
                    f"({f(narr['number_preservation_rate'])})"
                )
            )
        )

    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-judge", action="store_true")
    ap.add_argument("--narration", action="store_true")
    ap.add_argument("--max-pairs", type=int, default=60)
    a = ap.parse_args()
    common.load_env()
    engine, _ = common.build_engine()
    cases = common.load_cases()
    responses = common.run_in_process(engine, cases)
    chunks = load_chunks()
    det = deterministic(responses, chunks)
    judge = llm_judge(responses, chunks, max_pairs=a.max_pairs) if a.llm_judge else None
    narr = narration_check(engine, cases, responses) if a.narration else None
    common.write_json("faithfulness.json", {"deterministic": det, "llm_judge": judge, "narration": narr})
    print(to_markdown(det, judge, narr))
