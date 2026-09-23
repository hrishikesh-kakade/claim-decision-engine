"""
End-to-end evaluation script. Runs every supplied public case plus every
candidate-created case through the ClaimEngine in-process (fast,
reproducible, zero network calls needed), scores decision accuracy against
`eval/expected_outcomes.json`, extracts the retrieval citation-hit-rate
that the orchestrator already computes per case, and writes both a
machine-readable JSON report and a human-readable Markdown summary.

Run:
    python eval/run_eval.py
    python eval/run_eval.py --api-url http://localhost:8000   # hit a running API instead
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from backend.models import ClaimCase  # noqa: E402
from backend.orchestrator import ClaimEngine  # noqa: E402

CASES_PUBLIC = ROOT / "data" / "public_test_cases.json"
CASES_CUSTOM = ROOT / "eval" / "cases" / "custom_cases.json"
EXPECTED = ROOT / "eval" / "expected_outcomes.json"
OUT_DIR = ROOT / "eval" / "results"

HIT_RATE_RE = re.compile(r"Citation/retrieval overlap: (\d+)/(\d+)")


def load_cases() -> list[dict]:
    cases = json.loads(CASES_PUBLIC.read_text())
    cases += json.loads(CASES_CUSTOM.read_text())
    return cases


def run_in_process(cases: list[dict]) -> list[dict]:
    engine = ClaimEngine()
    results = []
    for raw in cases:
        case = ClaimCase.model_validate(raw)
        resp = engine.analyze(case)
        results.append(json.loads(resp.model_dump_json()) if hasattr(resp, "model_dump_json") else resp.dict())
    return results


def run_via_api(cases: list[dict], api_url: str) -> list[dict]:
    import requests

    results = []
    for raw in cases:
        r = requests.post(f"{api_url.rstrip('/')}/analyze", json=raw, timeout=60)
        r.raise_for_status()
        results.append(r.json())
    return results


def extract_hit_rate(trace: list[dict]) -> tuple[int, int] | None:
    for step in trace:
        m = HIT_RATE_RE.search(step.get("detail", ""))
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-url", default=None, help="If set, POSTs to a running API instead of running in-process.")
    args = ap.parse_args()

    cases = load_cases()
    expected = json.loads(EXPECTED.read_text())

    if args.api_url:
        results = run_via_api(cases, args.api_url)
    else:
        results = run_in_process(cases)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    n_correct = 0
    n_needs_review_expected = 0
    n_needs_review_actual = 0
    n_validation_pass = 0
    hit_num_total, hit_den_total = 0, 0

    for raw, resp in zip(cases, results):
        cid = raw["case_id"]
        exp = expected.get(cid, {})
        exp_decision = exp.get("expected_decision")
        actual_decision = resp["decision"]
        correct = (exp_decision == actual_decision) if exp_decision else None
        if correct:
            n_correct += 1
        if exp_decision == "NEEDS_REVIEW":
            n_needs_review_expected += 1
        if actual_decision == "NEEDS_REVIEW":
            n_needs_review_actual += 1
        if resp["validation"]["status"] == "PASS":
            n_validation_pass += 1
        hr = extract_hit_rate(resp.get("trace", []))
        if hr:
            hit_num_total += hr[0]
            hit_den_total += hr[1]

        rows.append({
            "case_id": cid,
            "expected_decision": exp_decision,
            "actual_decision": actual_decision,
            "match": correct,
            "confidence": resp["confidence"],
            "payable_estimate_inr": resp.get("payable_estimate_inr"),
            "validation_status": resp["validation"]["status"],
            "citation_hit_rate": f"{hr[0]}/{hr[1]}" if hr else None,
            "rationale_expected": exp.get("rationale"),
        })

    n_total = len(cases)
    n_scored = sum(1 for r in rows if r["expected_decision"])
    summary = {
        "total_cases": n_total,
        "decision_accuracy": round(n_correct / n_scored, 3) if n_scored else None,
        "correct": n_correct,
        "scored": n_scored,
        "needs_review_expected": n_needs_review_expected,
        "needs_review_actual": n_needs_review_actual,
        "validation_pass_rate": round(n_validation_pass / n_total, 3),
        "citation_hit_rate_overall": round(hit_num_total / hit_den_total, 3) if hit_den_total else None,
    }

    (OUT_DIR / "eval_results.json").write_text(json.dumps({"summary": summary, "cases": rows}, indent=2))

    lines = ["# Evaluation Results", "", "## Summary", ""]
    for k, v in summary.items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## Per-case", "", "| case_id | expected | actual | match | confidence | payable_inr | validation | citation_hit_rate |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['case_id']} | {r['expected_decision']} | {r['actual_decision']} | "
            f"{'✅' if r['match'] else ('❌' if r['match'] is False else '—')} | {r['confidence']:.2f} | "
            f"{r['payable_estimate_inr']} | {r['validation_status']} | {r['citation_hit_rate']} |"
        )
    (OUT_DIR / "eval_results.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_DIR / 'eval_results.json'} and eval_results.md")


if __name__ == "__main__":
    main()
