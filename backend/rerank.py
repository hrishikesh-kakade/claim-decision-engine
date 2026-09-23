"""
Reranking stage applied to the fused hybrid-retrieval shortlist.

We implement a lightweight, dependency-free lexical reranker by default so
the pipeline runs in fully offline environments, but the interface is
deliberately narrow (`rerank(query, candidates) -> candidates`) so a real
cross-encoder (BAAI/bge-reranker-base, Cohere rerank, etc.) is a drop-in
replacement -- see `CrossEncoderReranker` below, used automatically when
`sentence-transformers`'s CrossEncoder is importable.

The lexical reranker scores each candidate by:
  * query-term coverage (how many distinct query terms appear in the chunk),
  * a small positional/section prior (DEFINITIONS chunks that define a term
    the query is *asking about* get a boost; numbered EXCLUSIONS/limits
    chunks get a boost when the query mentions "limit", "exclude", "waiting"
    etc.), and
  * an inverse-length penalty so a giant chunk doesn't win purely by
    containing many query words by chance.
This is intentionally simple and auditable -- the point of this stage is to
demonstrably re-order the fused candidates, not to add a black box.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .retrieval import RetrievedChunk

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]+")

SECTION_PRIOR_TERMS = {
    "DEFINITIONS": {"mean", "definition", "define", "what is"},
    "EXCLUSIONS": {"exclude", "exclusion", "not covered", "waiting", "reject"},
    "SCOPE_OF_COVER": {"limit", "sub-limit", "sublimit", "cover", "payable", "cap"},
    "STANDARD_TERMS": {"portability", "renewal", "contribution", "cancellation"},
}


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text)}


class LexicalReranker:
    name = "lexical-overlap-rerank-v1"

    def rerank(self, query: str, candidates: list["RetrievedChunk"]) -> list["RetrievedChunk"]:
        q_tokens = _tokenize(query)
        q_lower = query.lower()
        for c in candidates:
            c_tokens = _tokenize(c.text)
            overlap = len(q_tokens & c_tokens)
            coverage = overlap / max(len(q_tokens), 1)
            length_penalty = 1.0 / (1.0 + len(c.text) / 800.0)
            prior = 0.0
            for term in SECTION_PRIOR_TERMS.get(c.section, ()):
                if term in q_lower:
                    prior += 0.15
            c.rerank_score = round(coverage * 0.7 + length_penalty * 0.15 + prior + c.fused_score * 2, 6)
        candidates.sort(key=lambda x: -x.rerank_score)
        return candidates


class CrossEncoderReranker:
    """Optional real cross-encoder reranker; used only if available."""

    name = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(self.name)

    def rerank(self, query: str, candidates: list["RetrievedChunk"]) -> list["RetrievedChunk"]:
        pairs = [(query, c.text) for c in candidates]
        scores = self.model.predict(pairs)
        for c, s in zip(candidates, scores):
            c.rerank_score = float(s)
        candidates.sort(key=lambda x: -x.rerank_score)
        return candidates


def get_reranker():
    try:
        return CrossEncoderReranker()
    except Exception:
        return LexicalReranker()
