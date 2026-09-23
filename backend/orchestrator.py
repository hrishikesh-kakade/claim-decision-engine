"""
Orchestrator: a small explicit Python state machine (no framework
dependency) that runs the five agents in sequence and exchanges typed
Pydantic objects between them -- this is the "structured state" the
agents hand off, not shared free-text prompts.

    ClaimCase
        -> Case Analysis Agent      -> CaseAnalysis
        -> Policy Evidence Agent    -> {query: [RetrievedChunk]}   (hybrid retrieval + rerank)
        -> Coverage & Exclusion Agent -> CoverageAssessment        (cites PolicyParameters, cross-checked against retrieval)
        -> Decision Agent           -> DecisionResponse (draft)
        -> Validation Agent         -> ValidationResult (attached to the response)

Each step is timed and logged into `trace` as a TraceStep so the caller
gets an auditable, non-chain-of-thought record of what happened.
"""
from __future__ import annotations

import time
from pathlib import Path

from .agents.case_analysis import analyze_case
from .agents.coverage_exclusion import assess
from .agents.decision import decide
from .agents.validation import validate
from .models import ClaimCase, DecisionResponse, TraceStep
from .policy_rules import PolicyParameters
from .retrieval import HybridRetriever

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class ClaimEngine:
    def __init__(self, chunks_path: Path | None = None):
        chunks_path = chunks_path or (DATA_DIR / "policy_chunks.json")
        self.retriever = HybridRetriever(chunks_path)
        self.policy_params = PolicyParameters(chunks_path)

    def analyze(self, case: ClaimCase) -> DecisionResponse:
        trace: list[TraceStep] = []

        t0 = time.perf_counter()
        analysis = analyze_case(case)
        trace.append(TraceStep(
            agent="CaseAnalysisAgent", action="extract_facts_and_plan",
            detail=f"{len(analysis.decision_dimensions)} decision dimensions identified; "
                   f"{len(analysis.missing_fields)} missing-field flag(s).",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))

        t0 = time.perf_counter()
        retrieved_by_query = self.retriever.search_many(analysis.search_queries, top_k_each=15, top_k_final=4)
        total_retrieved = sum(len(v) for v in retrieved_by_query.values())
        trace.append(TraceStep(
            agent="PolicyEvidenceAgent", action="hybrid_retrieve_and_rerank",
            detail=(
                f"Ran {len(analysis.search_queries)} quer(y/ies) through BM25 + "
                f"{self.retriever.dense_backend} dense retrieval, fused with RRF, reranked "
                f"({self.retriever.reranker.name})."
            ),
            retrieval_count=total_retrieved,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))

        t0 = time.perf_counter()
        coverage = assess(case, analysis, self.policy_params)
        retrieved_chunk_ids = {c.chunk_id for chunks in retrieved_by_query.values() for c in chunks}
        cited_chunk_ids = {c.chunk_id for f in coverage.findings for c in f.citations}
        recall_hits = len(cited_chunk_ids & retrieved_chunk_ids)
        citation_hit_rate = recall_hits / len(cited_chunk_ids) if cited_chunk_ids else None
        trace.append(TraceStep(
            agent="CoverageExclusionAgent", action="apply_policy_rules",
            detail=(
                f"{len(coverage.findings)} finding(s), {len(coverage.applicable_limits)} applicable limit(s). "
                f"Citation/retrieval overlap: {recall_hits}/{len(cited_chunk_ids)}"
                + (f" ({citation_hit_rate:.0%})" if citation_hit_rate is not None else "")
            ),
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))

        t0 = time.perf_counter()
        response = decide(coverage, case.expenses_inr.total)
        llm_info = response.llm_narration or {}
        if llm_info.get("succeeded"):
            llm_detail = f"LLM narration USED (provider={llm_info.get('provider')}, model={llm_info.get('model')})."
        elif llm_info.get("called"):
            llm_detail = f"LLM narration attempted but FAILED (provider={llm_info.get('provider')}): {llm_info.get('error')}. Used deterministic findings."
        else:
            llm_detail = f"LLM narration SKIPPED (provider={llm_info.get('provider')}): {llm_info.get('error')}. Used deterministic findings."
        trace.append(TraceStep(
            agent="DecisionAgent", action="combine_findings",
            detail=f"Decision: {response.decision} (confidence {response.confidence:.2f}). {llm_detail}",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))

        t0 = time.perf_counter()
        validation = validate(response, coverage, self.policy_params)
        trace.append(TraceStep(
            agent="ValidationAgent", action="verify_citations",
            detail=f"{validation.status}; {len(validation.unsupported_claims)} unsupported claim(s).",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))

        response.validation = validation
        if validation.status == "FAIL" and response.decision != "NEEDS_REVIEW":
            response.decision = "NEEDS_REVIEW"
            response.confidence = min(response.confidence, 0.4)
            response.missing_evidence.append(
                "Validation agent could not confirm citations for one or more material findings; "
                "downgraded to NEEDS_REVIEW."
            )
        response.trace = trace
        return response
