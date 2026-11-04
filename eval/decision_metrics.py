
"""Decision-quality metrics and explicitly labelled legacy payable comparison."""
from __future__ import annotations

import json

import common
import metrics_lib as M

LABELS = [
    "ADMISSIBLE",
    "ADMISSIBLE_WITH_LIMITS",
    "PARTIALLY_ADMISSIBLE",
    "NOT_ADMISSIBLE",
    "NEEDS_REVIEW",
]
APPROVING = {
    "ADMISSIBLE",
    "ADMISSIBLE_WITH_LIMITS",
    "PARTIALLY_ADMISSIBLE",
}


def compute(cases: list[dict], responses: list[dict]) -> dict:
    expected = json.loads(common.EXPECTED.read_text())

    # Historical gold amounts use assumptions that are not valid as
    # policy-aware payable ground truth. Keep them clearly segregated.
    gold_path = common.GOLD_DIR / "payable_gold.json"
    legacy_gold_pay = json.loads(gold_path.read_text()) if gold_path.exists() else {}

    if len(cases) != len(responses):
        raise ValueError(
            f"Case/response count mismatch: {len(cases)} cases, "
            f"{len(responses)} responses"
        )

    case_ids = [c["case_id"] for c in cases]
    response_ids = [r["case_id"] for r in responses]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Duplicate case IDs found in input cases")

    if len(response_ids) != len(set(response_ids)):
        raise ValueError("Duplicate case IDs found in responses")

    if case_ids != response_ids:
        raise ValueError(
            "Case/response ID or ordering mismatch. "
            "Check that each response belongs to its corresponding input case."
        )

    expected_ids = set(expected) - {"_method"}
    if set(case_ids) != expected_ids:
        raise ValueError(
            "Expected-outcome coverage mismatch. "
            f"Missing: {sorted(expected_ids - set(case_ids))}; "
            f"unexpected: {sorted(set(case_ids) - expected_ids)}"
        )

    valid_labels = set(LABELS)
    pairs = []

    for case, response in zip(cases, responses):
        cid = case["case_id"]
        expected_label = expected[cid]["expected_decision"]
        predicted_label = response["decision"]

        if expected_label not in valid_labels:
            raise ValueError(f"Invalid expected label for {cid}: {expected_label}")
        if predicted_label not in valid_labels:
            raise ValueError(f"Invalid predicted label for {cid}: {predicted_label}")

        pairs.append((cid, expected_label, predicted_label, response))

    n = len(pairs)
    if n == 0:
        raise ValueError("Cannot evaluate an empty case set")

    correct = sum(1 for _, e, p, _ in pairs if e == p)
    lo, hi = M.wilson_interval(correct, n)

    cm = {e: {p: 0 for p in LABELS} for e in LABELS}
    for _, e, p, _ in pairs:
        cm[e][p] += 1

    per_class = {}
    for lab in LABELS:
        tp = cm[lab][lab]
        fp = sum(cm[o][lab] for o in LABELS if o != lab)
        fn = sum(cm[lab][o] for o in LABELS if o != lab)
        support = tp + fn
        per_class[lab] = {**M.prf(tp, fp, fn), "support": support, "fp": fp}

    f1s = [
        v["f1"]
        for v in per_class.values()
        if v["f1"] is not None and (v["support"] or v["fp"])
    ]
    represented_classes = len(f1s)
    macro_f1 = sum(f1s) / represented_classes if represented_classes else None

    should_not_pay = [
        t for t in pairs if t[1] in ("NOT_ADMISSIBLE", "NEEDS_REVIEW")
    ]
    unsafe = [t for t in should_not_pay if t[2] in APPROVING]
    should_pay = [t for t in pairs if t[1] in APPROVING]
    false_reject = [t for t in should_pay if t[2] == "NOT_ADMISSIBLE"]
    over_abstain = [
        t for t in pairs if t[1] != "NEEDS_REVIEW" and t[2] == "NEEDS_REVIEW"
    ]
    decided = [t for t in pairs if t[2] != "NEEDS_REVIEW"]
    decided_correct = sum(1 for _, e, p, _ in decided if e == p)

    # This is a legacy diagnostic only, not a policy-aware payable score.
    legacy_pay_rows = []
    for cid, _, _, response in pairs:
        gold = legacy_gold_pay.get(cid, {}).get("payable_inr")
        if gold is None:
            continue
        predicted = response.get("payable_estimate_inr")
        abs_err = None if predicted is None else abs(predicted - gold)
        legacy_pay_rows.append({
            "case_id": cid,
            "legacy_gold_inr": gold,
            "predicted_inr": predicted,
            "absolute_error_inr": abs_err,
        })

    legacy_scored = [r for r in legacy_pay_rows if r["absolute_error_inr"] is not None]
    legacy_exact = sum(1 for r in legacy_scored if r["absolute_error_inr"] < 0.5)

    over_abstain_denominator = n - sum(
        1 for t in pairs if t[1] == "NEEDS_REVIEW"
    )

    return {
        "n_cases": n,
        "correct": correct,
        "accuracy": correct / n,
        "accuracy_ci95": [lo, hi],
        "macro_f1": macro_f1,
        "macro_f1_classes_evaluated": represented_classes,
        "macro_f1_classes_total": len(LABELS),
        "per_class": per_class,
        "confusion_matrix": cm,
        "unsafe_approval": {
            "count": len(unsafe),
            "of": len(should_not_pay),
            "rate": len(unsafe) / len(should_not_pay) if should_not_pay else None,
            "ci95_upper_bound": (
                M.wilson_interval(len(unsafe), len(should_not_pay))[1]
                if should_not_pay else None
            ),
        },
        "false_rejection": {
            "count": len(false_reject),
            "of": len(should_pay),
            "rate": len(false_reject) / len(should_pay) if should_pay else None,
        },
        "over_abstention": {
            "count": len(over_abstain),
            "of": over_abstain_denominator,
            "rate": (
                len(over_abstain) / over_abstain_denominator
                if over_abstain_denominator else None
            ),
        },
        "abstention": per_class["NEEDS_REVIEW"],
        "straight_through_rate": len(decided) / n,
        "decided_accuracy": (
            decided_correct / len(decided) if decided else None
        ),
        "legacy_payable_comparison": {
            "warning": (
                "Historical payable gold; not policy-aware ground truth. "
                "Do not present as current payable accuracy."
            ),
            "gold_eligible": len(legacy_pay_rows),
            "predicted": len(legacy_scored),
            "missing_prediction": len(legacy_pay_rows) - len(legacy_scored),
            "exact_match": legacy_exact,
            "exact_match_rate": (
                legacy_exact / len(legacy_scored) if legacy_scored else None
            ),
            "mae_inr": (
                sum(r["absolute_error_inr"] for r in legacy_scored) / len(legacy_scored)
                if legacy_scored else None
            ),
            "rows": legacy_pay_rows,
        },
    }


def to_markdown(r: dict) -> str:
    f = common.fmt
    ci = r["accuracy_ci95"]
    unsafe = r["unsafe_approval"]
    over = r["over_abstention"]

    lines = [
        f"- Decision accuracy: **{r['correct']}/{r['n_cases']} = {r['accuracy']:.1%}** "
        f"(95% Wilson CI {ci[0]:.1%} to {ci[1]:.1%}); "
        f"macro-F1 {f(r['macro_f1'])} "
        f"({r['macro_f1_classes_evaluated']}/{r['macro_f1_classes_total']} represented classes)",
        f"- Unsafe-approval rate: **{unsafe['count']}/{unsafe['of']}** "
        f"(95% upper bound {f(unsafe['ci95_upper_bound'], 1)}) - "
        "cases that should not be paid but were",
        f"- False-rejection rate: {r['false_rejection']['count']}/{r['false_rejection']['of']}; "
        f"over-abstention: {over['count']}/{over['of']} "
        f"({f(over['rate'], 1)})",
        f"- Abstention (NEEDS_REVIEW) precision {f(r['abstention']['precision'])} / "
        f"recall {f(r['abstention']['recall'])} / F1 {f(r['abstention']['f1'])}",
        f"- Straight-through rate: **{r['straight_through_rate']:.1%}**; "
        f"accuracy on auto-decided cases: {f(r['decided_accuracy'])}",
        "",
        "**Legacy payable comparison only — not policy-aware ground truth.**",
        f"- Legacy gold eligible: {r['legacy_payable_comparison']['gold_eligible']}; "
        f"predictions available: {r['legacy_payable_comparison']['predicted']}; "
        f"exact match: {r['legacy_payable_comparison']['exact_match']}; "
        f"MAE INR: {f(r['legacy_payable_comparison']['mae_inr'], 1)}",
        "",
        "Confusion matrix (rows = expected, columns = predicted):",
        "",
        "| expected \\ predicted | " + " | ".join(l.replace("_", " ")[:12] for l in LABELS) + " |",
        "|---|" + "---|" * len(LABELS),
    ]

    for expected_label in LABELS:
        lines.append(
            f"| {expected_label} | " +
            " | ".join(
                str(r["confusion_matrix"][expected_label][predicted_label])
                for predicted_label in LABELS
            ) + " |"
        )

    lines += [
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]
    for label in LABELS:
        c = r["per_class"][label]
        lines.append(
            f"| {label} | {f(c['precision'])} | {f(c['recall'])} | "
            f"{f(c['f1'])} | {c['support']} |"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    common.load_env()
    engine, _ = common.build_engine()
    cases = common.load_cases()
    responses = common.run_in_process(engine, cases)
    result = compute(cases, responses)
    common.write_json("decision_metrics.json", result)
    print(to_markdown(result))
