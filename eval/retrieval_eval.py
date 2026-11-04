
"""
Retrieval quality and ablation:
BM25-only vs dense-only vs hybrid (RRF) vs hybrid + reranking.

Production retrieval is hybrid RRF without reranking.
Hybrid + lexical reranking remains an experimental comparison.

Metrics:
  Hit@3, Hit@5 = 1 if any relevant chunk is in top-k
  Recall@3, Recall@5 = |relevant intersection top-k| / |relevant|
  MRR@5 = reciprocal rank of the first relevant chunk
  nDCG@5 = DCG / ideal DCG with binary relevance
  latency = wall-clock ms per search() call after warm-up

Datasets:
  original = original 30-query benchmark
  dev      = combined 70-query development benchmark (default)
  heldout  = separate 20-query held-out benchmark

Run:
  uv run python eval/retrieval_eval.py
  uv run python eval/retrieval_eval.py --dataset original
  uv run python eval/retrieval_eval.py --dataset heldout
  uv run python eval/retrieval_eval.py --validate-gold
"""

from __future__ import annotations

import argparse
import json
import re
import time

import common
import metrics_lib as M


MODES = ["sparse", "dense", "hybrid", "hybrid_rerank"]

LABELS = {
    "sparse": "BM25 only",
    "dense": "Dense only",
    "hybrid": "Hybrid (BM25+dense, RRF) — production",
    "hybrid_rerank": "Hybrid + lexical rerank (experimental)",
}

PRODUCTION_MODE = "hybrid"
EXPERIMENTAL_MODE = "hybrid_rerank"
KS = (3, 5)


def load_gold(dataset: str = "dev") -> list[dict]:
    """Load one of the available retrieval gold datasets."""

    gold_paths = {
        "original": common.RETRIEVAL_GOLD_ORIGINAL,
        "dev": common.RETRIEVAL_GOLD_DEV,
        "heldout": common.RETRIEVAL_GOLD_HELDOUT,
    }

    if dataset not in gold_paths:
        raise ValueError(
            f"Unknown dataset '{dataset}'. "
            f"Choose from: {', '.join(gold_paths)}"
        )

    path = gold_paths[dataset]

    if not path.exists():
        raise FileNotFoundError(
            f"Retrieval gold dataset not found: {path}"
        )

    data = json.loads(path.read_text(encoding="utf-8"))

    if "queries" not in data:
        raise ValueError(
            f"Invalid gold dataset format: {path} "
            "does not contain a 'queries' field."
        )

    return data["queries"]


def normalize_text(value: str) -> str:
    """Normalize whitespace and case for evidence-term validation."""

    return re.sub(r"\s+", " ", value).strip().casefold()


def validate_gold(dataset: str = "dev") -> int:
    """
    Validate chunk references and evidence terms.

    Every evidence term must appear in at least one of the query's
    relevant chunks. Whitespace differences are ignored.
    """

    chunk_data = json.loads(
        common.CHUNKS.read_text(encoding="utf-8")
    )

    chunks = {
        chunk["chunk_id"]: normalize_text(chunk["text"])
        for chunk in chunk_data
    }

    gold = load_gold(dataset)
    bad = 0

    seen_ids = set()
    seen_queries = set()

    for query in gold:
        query_id = query["id"]
        query_text = normalize_text(query["query"])

        if query_id in seen_ids:
            print(f"[{query_id}] duplicate query ID")
            bad += 1
        seen_ids.add(query_id)

        if query_text in seen_queries:
            print(f"[{query_id}] duplicate query text")
            bad += 1
        seen_queries.add(query_text)

        relevant = query.get("relevant", [])
        evidence_terms = query.get("evidence_terms", [])

        if not relevant:
            print(f"[{query_id}] no relevant chunks specified")
            bad += 1
            continue

        if not evidence_terms:
            print(f"[{query_id}] no evidence terms specified")
            bad += 1
            continue

        missing_chunks = [
            chunk_id
            for chunk_id in relevant
            if chunk_id not in chunks
        ]

        if missing_chunks:
            print(
                f"[{query_id}] unknown chunk IDs: "
                f"{missing_chunks}"
            )
            bad += 1

        valid_relevant_texts = [
            chunks[chunk_id]
            for chunk_id in relevant
            if chunk_id in chunks
        ]

        for term in evidence_terms:
            normalized_term = normalize_text(term)

            if not normalized_term:
                print(f"[{query_id}] empty evidence term")
                bad += 1
                continue

            found = any(
                normalized_term in chunk_text
                for chunk_text in valid_relevant_texts
            )

            if not found:
                print(
                    f"[{query_id}] evidence term not found "
                    f"in relevant chunks: {term!r}"
                )
                bad += 1

    print(
        f"{dataset} gold validation: "
        f"{'OK' if bad == 0 else f'{bad} problem(s)'}"
    )
    print(f"Queries checked: {len(gold)}")

    return bad


def run(
    retriever,
    top_k: int = 5,
    dataset: str = "dev",
) -> dict:
    """Evaluate all retrieval modes against the selected gold dataset."""

    gold = load_gold(dataset)

    if not gold:
        raise ValueError(
            f"The '{dataset}' retrieval dataset contains no queries."
        )

    # Warm up every mode before measuring latency.
    # This excludes initial cache/model warm-up from measured calls.
    for query in gold:
        for mode in MODES:
            retriever.search(
                query["query"],
                top_k_each=15,
                top_k_final=top_k,
                mode=mode,
            )

    per_mode: dict[str, dict] = {}

    for mode in MODES:
        rows = []

        for query in gold:
            t0 = time.perf_counter()

            results = retriever.search(
                query["query"],
                top_k_each=15,
                top_k_final=top_k,
                mode=mode,
            )

            ms = (time.perf_counter() - t0) * 1000

            ranked = [
                item.chunk_id
                for item in results
            ]

            row = {
                "id": query["id"],
                "group": query["group"],
                "ranked": ranked,
                "ms": ms,
                "mrr": M.reciprocal_rank(
                    ranked,
                    query["relevant"],
                    top_k,
                ),
                "ndcg5": M.ndcg_at_k(
                    ranked,
                    query["relevant"],
                    5,
                ),
            }

            for k in KS:
                row[f"hit@{k}"] = M.hit_at_k(
                    ranked,
                    query["relevant"],
                    k,
                )

                row[f"recall@{k}"] = M.recall_at_k(
                    ranked,
                    query["relevant"],
                    k,
                )

            rows.append(row)

        per_mode[mode] = {"rows": rows}

    def aggregate(rows: list[dict]) -> dict:
        if not rows:
            raise ValueError(
                "Cannot aggregate metrics for an empty query group."
            )

        keys = (
            [f"hit@{k}" for k in KS]
            + [f"recall@{k}" for k in KS]
            + ["mrr", "ndcg5"]
        )

        output = {
            key: sum(row[key] for row in rows) / len(rows)
            for key in keys
        }

        output["n_queries"] = len(rows)

        output["latency"] = M.summarize_latency(
            [row["ms"] for row in rows]
        )

        lo, hi = M.bootstrap_ci(
            [row["recall@3"] for row in rows]
        )

        output["recall@3_ci95"] = [lo, hi]

        return output

    summary = {}

    for mode in MODES:
        rows = per_mode[mode]["rows"]

        summary[mode] = {
            "overall": aggregate(rows),
            "pipeline": aggregate(
                [
                    row
                    for row in rows
                    if row["group"] == "pipeline"
                ]
            ),
            "natural": aggregate(
                [
                    row
                    for row in rows
                    if row["group"] == "natural"
                ]
            ),
        }

    # Production misses are calculated using hybrid RRF,
    # not the experimental reranker.
    query_by_id = {
        query["id"]: query
        for query in gold
    }

    misses = [
        {
            "id": row["id"],
            "query": query_by_id[row["id"]]["query"],
            "expected": query_by_id[row["id"]]["relevant"],
            "got": row["ranked"],
        }
        for row in per_mode[PRODUCTION_MODE]["rows"]
        if row["hit@5"] == 0
    ]

    return {
        "dataset": dataset,
        "backends": {
            "sparse": getattr(
                retriever,
                "sparse_backend",
                "?",
            ),
            "dense": getattr(
                retriever,
                "dense_backend",
                "?",
            ),
            "reranker": retriever.reranker.name,
        },
        "production_mode": PRODUCTION_MODE,
        "experimental_mode": EXPERIMENTAL_MODE,
        "n_queries": len(gold),
        "top_k": top_k,
        "summary": summary,
        "production_total_misses_at_5": misses,
    }


def to_markdown(res: dict) -> str:
    """Render the retrieval evaluation results as Markdown."""

    f = common.fmt

    lines = [
        f"Dataset: **{res['dataset']}**.",
        f"Production retrieval: **{res['production_mode']}**. "
        f"Experimental comparison: **{res['experimental_mode']}**.",
        "",
        f"Backends: sparse=`{res['backends']['sparse']}`, "
        f"dense=`{res['backends']['dense']}`, "
        f"experimental reranker=`{res['backends']['reranker']}`; "
        f"{res['n_queries']} hand-labeled queries, "
        f"top-{res['top_k']}.",
        "",
        "| Retriever | Hit@3 | Hit@5 | Recall@3 (95% CI) | "
        "Recall@5 | MRR@5 | nDCG@5 | p50 ms |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for mode in MODES:
        overall = res["summary"][mode]["overall"]
        ci = overall["recall@3_ci95"]

        lines.append(
            f"| {LABELS[mode]} | "
            f"{f(overall['hit@3'])} | "
            f"{f(overall['hit@5'])} | "
            f"{f(overall['recall@3'])} "
            f"({f(ci[0], 2)}-{f(ci[1], 2)}) | "
            f"{f(overall['recall@5'])} | "
            f"{f(overall['mrr'])} | "
            f"{f(overall['ndcg5'])} | "
            f"{f(overall['latency']['p50_ms'], 1)} |"
        )

    lines += [
        "",
        "By query group (production retriever = Hybrid RRF):",
        "",
        "| Group | Hit@3 | Recall@3 | MRR@5 |",
        "|---|---|---|---|",
    ]

    for group in ("pipeline", "natural"):
        overall = res["summary"][PRODUCTION_MODE][group]

        lines.append(
            f"| {group} ({overall['n_queries']} q) | "
            f"{f(overall['hit@3'])} | "
            f"{f(overall['recall@3'])} | "
            f"{f(overall['mrr'])} |"
        )

    misses = res["production_total_misses_at_5"]

    if misses:
        lines += [
            "",
            "Queries where production retrieval found "
            "NO relevant chunk in the top 5:",
        ]

        for miss in misses:
            lines.append(
                f"- {miss['id']} \"{miss['query']}\" "
                f"expected {miss['expected']} "
                f"got {miss['got']}"
            )

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset",
        choices=["original", "dev", "heldout"],
        default="dev",
        help="Retrieval gold dataset to evaluate (default: dev).",
    )

    parser.add_argument(
        "--validate-gold",
        action="store_true",
        help="Validate the selected retrieval gold dataset.",
    )

    args = parser.parse_args()

    if args.validate_gold:
        raise SystemExit(
            validate_gold(args.dataset)
        )

    common.load_env()
    engine, _ = common.build_engine()

    result = run(
        engine.retriever,
        dataset=args.dataset,
    )

    output_name = (
        f"retrieval_metrics_{args.dataset}.json"
    )

    common.write_json(
        output_name,
        result,
    )

    print(to_markdown(result))

    print(
        f"\nSaved results to eval/results/{output_name}"
    )
