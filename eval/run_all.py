
"""One command -> every benchmark -> eval/results/METRICS_REPORT.md."""
from __future__ import annotations

import argparse
import datetime
import platform
import sys

import common
import decision_metrics
import faithfulness_eval
import manual_baseline
import perf_bench
import retrieval_eval


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--llm-judge", action="store_true")
    ap.add_argument("--narration", action="store_true")
    ap.add_argument("--with-llm-latency", action="store_true")
    args = ap.parse_args()

    common.load_env()
    from backend.agents.llm_writer import get_client

    provider = get_client().provider
    engine, cold = common.build_engine()
    cases = common.load_cases()
    responses = common.run_in_process(engine, cases)
    chunks = faithfulness_eval.load_chunks()

    retrieval = retrieval_eval.run(engine.retriever)
    decisions = decision_metrics.compute(cases, responses)
    citations = faithfulness_eval.deterministic(responses, chunks)
    judge = (
        faithfulness_eval.llm_judge(responses, chunks)
        if args.llm_judge else None
    )
    narration = (
        faithfulness_eval.narration_check(engine, cases, responses)
        if args.narration else None
    )
    perf_core = perf_bench.run_in_process(
        engine, cold, runs=args.runs, llm_off=True
    )
    common.write_json("perf_bench.json", perf_core)

    perf_llm = (
        perf_bench.run_in_process(engine, cold, runs=1, warmup=0, llm_off=False)
        if args.with_llm_latency and provider != "none"
        else None
    )
    manual = manual_baseline.run()

    common.write_json(
        "all_metrics.json",
        {
            "retrieval": retrieval,
            "decision": decisions,
            "citations": citations,
            "llm_judge": judge,
            "narration": narration,
            "perf_core": perf_core,
            "perf_with_llm": perf_llm,
            "manual": manual,
        },
    )

    hybrid = retrieval["summary"]["hybrid"]["overall"]
    hybrid_rerank = retrieval["summary"]["hybrid_rerank"]["overall"]
    sparse = retrieval["summary"]["sparse"]["overall"]
    end_to_end = perf_core["end_to_end"]
    ci = decisions["accuracy_ci95"]
    legacy_pay = decisions["legacy_payable_comparison"]

    headline = [
        f"Decision accuracy **{decisions['correct']}/{decisions['n_cases']}** "
        f"(95% CI {ci[0]:.0%}-{ci[1]:.0%}); "
        f"macro-F1 {common.fmt(decisions['macro_f1'], 2)}",
        f"Unsafe approvals **{decisions['unsafe_approval']['count']}/"
        f"{decisions['unsafe_approval']['of']}** should-not-pay cases "
        f"(95% upper bound "
        f"{common.fmt(decisions['unsafe_approval']['ci95_upper_bound'], 2)})",
        f"Auto-decided **{decisions['straight_through_rate']:.0%}** of claims; "
        f"abstention precision/recall "
        f"{common.fmt(decisions['abstention']['precision'], 2)}/"
        f"{common.fmt(decisions['abstention']['recall'], 2)}",
        "Legacy payable comparison only (not policy-aware): "
        f"{legacy_pay['predicted']}/{legacy_pay['gold_eligible']} predictions; "
        f"exact match {legacy_pay['exact_match']}; "
        f"MAE INR {common.fmt(legacy_pay['mae_inr'], 0)}",
        f"Retrieval (hybrid RRF production, {retrieval['n_queries']} labeled queries): "
        f"Hit@3 {hybrid['hit@3']:.2f}, Recall@3 {hybrid['recall@3']:.2f}, "
        f"MRR@5 {hybrid['mrr']:.2f} "
        f"(BM25-only MRR@5 {sparse['mrr']:.2f}; "
        f"experimental reranker MRR@5 {hybrid_rerank['mrr']:.2f})",
        f"Latency, deterministic core: p50 {end_to_end['p50_ms']:.0f} ms, "
        f"p95 {end_to_end['p95_ms']:.0f} ms, "
        f"p99 {end_to_end['p99_ms']:.0f} ms "
        f"(n={end_to_end['n']}); cold start {cold:.0f} ms",
        f"Citation numeric support: "
        f"{citations['numeric_supported']}/{citations['numeric_checked']}",
    ]

    if perf_llm:
        llm_latency = perf_llm["end_to_end"]
        headline.append(
            f"Latency with LLM narration ({provider}): "
            f"p50 {llm_latency['p50_ms']:.0f} ms, "
            f"p95 {llm_latency['p95_ms']:.0f} ms "
            f"(n={llm_latency['n']})"
        )

    markdown = [
        "# Metrics report",
        "",
        f"Generated {datetime.date.today()} on `{platform.platform()}`, "
        f"Python {platform.python_version()}. "
        f"Sparse=`{retrieval['backends']['sparse']}`, "
        f"dense=`{retrieval['backends']['dense']}`, "
        f"reranker=`{retrieval['backends']['reranker']}`, "
        f"LLM provider=`{provider}`.",
        "",
        "> **These numbers are valid only for the environment above and this "
        "synthetic benchmark.** Decision metrics use policy-aware expected "
        "outcomes. Historical payable comparison uses legacy gold and is not "
        "a policy-aware payable accuracy score. See docs/METRICS.md.",
        "",
        "## Headline numbers",
        "",
        *[f"- {item}" for item in headline],
        "",
        "## 1. Decision quality",
        "",
        decision_metrics.to_markdown(decisions),
        "",
        "## 2. Retrieval (ablation)",
        "",
        retrieval_eval.to_markdown(retrieval),
        "",
        "## 3. Citation correctness / faithfulness",
        "",
        faithfulness_eval.to_markdown(citations, judge, narration),
        "",
        "## 4. Latency",
        "",
        perf_bench.to_markdown(perf_core),
    ]

    if perf_llm:
        markdown += [
            "",
            "With LLM narration enabled (one pass, so percentiles are rough):",
            "",
            perf_bench.to_markdown(perf_llm),
        ]

    markdown += [
        "",
        "## 5. Manual-effort baseline",
        "",
        manual_baseline.to_markdown(manual),
        "",
    ]

    common.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (common.OUT_DIR / "METRICS_REPORT.md").write_text("\n".join(markdown))
    print("\n".join(markdown))


if __name__ == "__main__":
    sys.exit(main())
