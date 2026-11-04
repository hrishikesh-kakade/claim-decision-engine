"""Diagnose how lexical reranking changes Hybrid RRF rankings."""

from __future__ import annotations

import json
from copy import deepcopy

import common
import metrics_lib as M
from backend.rerank import SECTION_PRIOR_TERMS, _tokenize


TOP_K = 5
CANDIDATE_K = 15


def score_components(query: str, chunk) -> dict:
    q_tokens = _tokenize(query)
    q_lower = query.lower()
    c_tokens = _tokenize(chunk.text)

    overlap = len(q_tokens & c_tokens)
    coverage = overlap / max(len(q_tokens), 1)
    length_penalty = 1.0 / (1.0 + len(chunk.text) / 800.0)

    matched_prior_terms = [
        term
        for term in SECTION_PRIOR_TERMS.get(chunk.section, ())
        if term in q_lower
    ]
    prior = len(matched_prior_terms) * 0.15

    coverage_component = coverage * 0.7
    length_component = length_penalty * 0.15
    fused_component = chunk.fused_score * 2

    total = (
        coverage_component
        + length_component
        + prior
        + fused_component
    )

    return {
        "query_token_count": len(q_tokens),
        "overlap_count": overlap,
        "coverage": round(coverage, 6),
        "coverage_component": round(coverage_component, 6),
        "length_penalty": round(length_penalty, 6),
        "length_component": round(length_component, 6),
        "section_prior": round(prior, 6),
        "matched_prior_terms": matched_prior_terms,
        "fused_score": round(chunk.fused_score, 8),
        "fused_component": round(fused_component, 6),
        "calculated_total": round(total, 6),
    }


def rank_positions(chunks: list) -> dict[str, int]:
    return {
        chunk.chunk_id: position
        for position, chunk in enumerate(chunks, start=1)
    }


def evaluate(ranked_ids: list[str], relevant: list[str]) -> dict:
    return {
        "hit_at_3": M.hit_at_k(ranked_ids, relevant, 3),
        "hit_at_5": M.hit_at_k(ranked_ids, relevant, 5),
        "recall_at_3": M.recall_at_k(ranked_ids, relevant, 3),
        "recall_at_5": M.recall_at_k(ranked_ids, relevant, 5),
        "mrr_at_5": M.reciprocal_rank(ranked_ids, relevant, 5),
        "ndcg_at_5": M.ndcg_at_k(ranked_ids, relevant, 5),
    }


def aggregate(rows: list, key: str) -> dict:
    metric_names = [
        "hit_at_3",
        "hit_at_5",
        "recall_at_3",
        "recall_at_5",
        "mrr_at_5",
        "ndcg_at_5",
    ]

    return {
        metric: round(
            sum(row[key][metric] for row in rows) / max(len(rows), 1),
            6,
        )
        for metric in metric_names
    }


def run(retriever) -> dict:
    gold_path = common.GOLD_DIR / "retrieval_gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))["queries"]

    rows = []

    for query_data in gold:
        query = query_data["query"]
        relevant = query_data["relevant"]

        original_candidates = retriever.search(
            query,
            top_k_each=15,
            top_k_final=CANDIDATE_K,
            mode="hybrid",
        )

        reranked_candidates = retriever.reranker.rerank(
            query,
            deepcopy(original_candidates),
        )

        original_top5 = original_candidates[:TOP_K]
        reranked_top5 = reranked_candidates[:TOP_K]

        original_ids = [c.chunk_id for c in original_top5]
        reranked_ids = [c.chunk_id for c in reranked_top5]

        original_positions = rank_positions(original_candidates)
        reranked_positions = rank_positions(reranked_candidates)

        relevant_movement = []

        for chunk_id in relevant:
            before = original_positions.get(chunk_id)
            after = reranked_positions.get(chunk_id)

            if before is None:
                movement = "not_in_candidate_pool"
            elif after is None:
                movement = "missing_after_reranking"
            elif after < before:
                movement = "moved_up"
            elif after > before:
                movement = "moved_down"
            else:
                movement = "unchanged"

            relevant_movement.append({
                "chunk_id": chunk_id,
                "hybrid_rank": before,
                "reranked_rank": after,
                "movement": movement,
            })

        candidate_diagnostics = []

        for chunk in reranked_candidates:
            components = score_components(query, chunk)

            candidate_diagnostics.append({
                "chunk_id": chunk.chunk_id,
                "section": chunk.section,
                "hybrid_rank": original_positions[chunk.chunk_id],
                "reranked_rank": reranked_positions[chunk.chunk_id],
                "rerank_score": round(chunk.rerank_score, 6),
                "score_components": components,
                "is_relevant": chunk.chunk_id in relevant,
            })

        rows.append({
            "id": query_data["id"],
            "group": query_data["group"],
            "query": query,
            "relevant": relevant,
            "hybrid_top5": original_ids,
            "reranked_top5": reranked_ids,
            "hybrid_metrics": evaluate(original_ids, relevant),
            "reranked_metrics": evaluate(reranked_ids, relevant),
            "relevant_movement": relevant_movement,
            "candidates": candidate_diagnostics,
        })

    movement_counts = {
        "moved_up": 0,
        "moved_down": 0,
        "unchanged": 0,
        "not_in_candidate_pool": 0,
        "missing_after_reranking": 0,
    }

    for row in rows:
        for movement in row["relevant_movement"]:
            movement_counts[movement["movement"]] += 1

    return {
        "n_queries": len(rows),
        "candidate_pool_size": CANDIDATE_K,
        "top_k_evaluated": TOP_K,
        "production_retrieval": "hybrid",
        "experimental_reranker": retriever.reranker.name,
        "hybrid_overall": aggregate(rows, "hybrid_metrics"),
        "reranked_overall": aggregate(rows, "reranked_metrics"),
        "relevant_chunk_movement_counts": movement_counts,
        "queries": rows,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# Reranker diagnostics",
        "",
        f"- Queries: {result['n_queries']}",
        f"- Candidate pool: {result['candidate_pool_size']}",
        f"- Evaluated ranking depth: {result['top_k_evaluated']}",
        f"- Production: {result['production_retrieval']}",
        f"- Experimental reranker: {result['experimental_reranker']}",
        "",
        "## Aggregate comparison",
        "",
        "| Metric | Hybrid RRF | Hybrid + reranker |",
        "|---|---:|---:|",
    ]

    for metric, label in [
        ("hit_at_3", "Hit@3"),
        ("hit_at_5", "Hit@5"),
        ("recall_at_3", "Recall@3"),
        ("recall_at_5", "Recall@5"),
        ("mrr_at_5", "MRR@5"),
        ("ndcg_at_5", "nDCG@5"),
    ]:
        before = result["hybrid_overall"][metric]
        after = result["reranked_overall"][metric]
        lines.append(f"| {label} | {before:.3f} | {after:.3f} |")

    lines += [
        "",
        "## Relevant chunk movement",
        "",
        "| Movement | Count |",
        "|---|---:|",
    ]

    for movement, count in result["relevant_chunk_movement_counts"].items():
        lines.append(f"| {movement} | {count} |")

    lines += ["", "## Per-query comparison", ""]

    for row in result["queries"]:
        lines += [
            f"### {row['id']} — {row['group']}",
            "",
            f"**Query:** {row['query']}",
            "",
            f"**Relevant chunks:** {row['relevant']}",
            "",
            f"**Hybrid top 5:** {row['hybrid_top5']}",
            "",
            f"**Reranked top 5:** {row['reranked_top5']}",
            "",
            "| Relevant chunk | Hybrid rank | Reranked rank | Movement |",
            "|---|---:|---:|---|",
        ]

        for movement in row["relevant_movement"]:
            lines.append(
                f"| {movement['chunk_id']} | "
                f"{movement['hybrid_rank'] or 'Not retrieved'} | "
                f"{movement['reranked_rank'] or 'Not retrieved'} | "
                f"{movement['movement']} |"
            )

        lines += [
            "",
            "| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]

        for candidate in row["candidates"]:
            components = candidate["score_components"]
            lines.append(
                f"| {candidate['chunk_id']} | "
                f"{candidate['hybrid_rank']} | "
                f"{candidate['reranked_rank']} | "
                f"{components['coverage_component']:.4f} | "
                f"{components['section_prior']:.2f} | "
                f"{components['fused_component']:.4f} | "
                f"{candidate['rerank_score']:.6f} |"
            )

        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    common.load_env()
    engine, _ = common.build_engine()

    result = run(engine.retriever)

    common.write_json("rerank_diagnostics.json", result)

    report = to_markdown(result)
    report_path = common.OUT_DIR / "RERANK_DIAGNOSTICS.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nDetailed JSON: {common.OUT_DIR / 'rerank_diagnostics.json'}")
    print(f"Markdown report: {report_path}")
