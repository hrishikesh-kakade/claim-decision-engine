
"""Run the policy-aware decision evaluation over public and custom cases."""
from __future__ import annotations

import argparse
import json
import re

import common

HIT_RATE_RE = re.compile(r"Citation/retrieval overlap: (\d+)/(\d+)")


def extract_hit_rate(trace: list[dict]) -> tuple[int, int] | None:
    for step in trace:
        match = HIT_RATE_RE.search(step.get("detail", ""))
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def run_via_api(cases: list[dict], api_url: str) -> list[dict]:
    import requests

    results = []
    for raw in cases:
        response = requests.post(
            f"{api_url.rstrip('/')}/analyze",
            json=raw,
            timeout=60,
        )
        response.raise_for_status()
        results.append(response.json())
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-url",
        default=None,
        help="POST to a running API instead of running in-process.",
    )
    args = parser.parse_args()

    cases = common.load_cases()
    expected = json.loads(common.EXPECTED.read_text())

    case_ids = [case["case_id"] for case in cases]
    expected_ids = set(expected) - {"_method"}

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate case IDs found in input cases")

    if set(case_ids) != expected_ids:
        raise ValueError(
            "Expected-outcome coverage mismatch. "
            f"Missing: {sorted(expected_ids - set(case_ids))}; "
            f"unexpected: {sorted(set(case_ids) - expected_ids)}"
        )

    for cid in case_ids:
        if "expected_decision" not in expected[cid]:
            raise ValueError(f"Missing expected_decision for {cid}")

    if args.api_url:
        results = run_via_api(cases, args.api_url)
    else:
        engine, _ = common.build_engine()
        results = common.run_in_process(engine, cases)

    if len(results) != len(cases):
        raise ValueError(
            f"Case/response count mismatch: {len(cases)} cases, "
            f"{len(results)} responses"
        )

    rows = []
    hit_num_total = 0
    hit_den_total = 0
    validation_pass = 0
    correct = 0
    needs_review_expected = 0
    needs_review_actual = 0

    for raw, response in zip(cases, results):
        cid = raw["case_id"]
        if response.get("case_id") != cid:
            raise ValueError(
                f"Response order/ID mismatch: expected {cid}, "
                f"received {response.get('case_id')}"
            )

        expected_decision = expected[cid]["expected_decision"]
        actual_decision = response["decision"]
        match = expected_decision == actual_decision

        correct += int(match)
        needs_review_expected += int(expected_decision == "NEEDS_REVIEW")
        needs_review_actual += int(actual_decision == "NEEDS_REVIEW")
        validation_pass += int(response["validation"]["status"] == "PASS")

        hit_rate = extract_hit_rate(response.get("trace", []))
        if hit_rate:
            hit_num_total += hit_rate[0]
            hit_den_total += hit_rate[1]

        rows.append({
            "case_id": cid,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "match": match,
            "confidence": response.get("confidence"),
            "payable_estimate_inr": response.get("payable_estimate_inr"),
            "validation_status": response["validation"]["status"],
            "citation_hit_rate": (
                f"{hit_rate[0]}/{hit_rate[1]}" if hit_rate else None
            ),
            "rationale_expected": expected[cid].get("rationale"),
        })

    total = len(cases)
    summary = {
        "total_cases": total,
        "decision_accuracy": correct / total if total else None,
        "correct": correct,
        "scored": total,
        "needs_review_expected": needs_review_expected,
        "needs_review_actual": needs_review_actual,
        "validation_pass_rate": validation_pass / total if total else None,
        "citation_hit_rate_overall": (
            hit_num_total / hit_den_total if hit_den_total else None
        ),
        "expectation_source": str(common.EXPECTED.relative_to(common.ROOT)),
    }

    report = {"summary": summary, "cases": rows}
    common.write_json("eval_results.json", report)

    lines = [
        "# Evaluation Results",
        "",
        f"Expected decisions: `{summary['expectation_source']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- **{key}**: {value}")

    lines += [
        "",
        "## Per-case",
        "",
        "| case_id | expected | actual | match | confidence | payable_inr | validation | citation_hit_rate |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['expected_decision']} | "
            f"{row['actual_decision']} | {row['match']} | "
            f"{row['confidence']} | {row['payable_estimate_inr']} | "
            f"{row['validation_status']} | {row['citation_hit_rate']} |"
        )

    report_path = common.OUT_DIR / "eval_results.md"
    report_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
