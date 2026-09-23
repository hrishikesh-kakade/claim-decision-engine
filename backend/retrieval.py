"""
Hybrid retrieval over the policy chunk store.

  * Sparse: BM25 (rank_bm25) over tokenised chunk text.
  * Dense: a persistent Chroma vector store (free, open-source, embedded --
    see vector_store.py) holding sentence-transformer embeddings. Falls
    back to an in-memory sentence-transformers matrix, then to TF-IDF
    cosine, if chromadb / sentence-transformers aren't available, so the
    pipeline always runs end-to-end and still produces two genuinely
    different rankings to fuse -- this is logged via `dense_backend` so
    it's never silently pretended to be persistent when it isn't.
  * Fusion: Reciprocal Rank Fusion (RRF) over the two rankings.
  * Rerank: a lightweight cross-encoder-style lexical-overlap + section-prior
    reranker (see rerank.py) is applied to the fused shortlist before it is
    handed to the reasoning agents. Swap in a real cross-encoder
    (e.g. BAAI/bge-reranker-base) by implementing `Reranker` in rerank.py --
    the interface is already isolated for that.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .rerank import LexicalReranker

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


@dataclass
class RetrievedChunk:
    chunk_id: str
    section: str
    subsection: Optional[str]
    page_start: int
    page_end: int
    text: str
    sparse_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    fused_score: float = 0.0
    rerank_score: float = 0.0

    def as_citation(self, source_name: str) -> dict:
        page = self.page_start if self.page_start == self.page_end else self.page_start
        return {
            "source": source_name,
            "page": page,
            "section": self.section,
            "subsection": self.subsection,
            "chunk_id": self.chunk_id,
        }


class HybridRetriever:
    def __init__(self, chunks_path: Path, source_name: str = "USGIC-CSC-2017-2018.pdf"):
        self.source_name = source_name
        self.chunks: list[dict] = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
        self._build_sparse()
        self._build_dense()
        self.reranker = LexicalReranker()

    # ---------------------------------------------------------------- sparse
    def _build_sparse(self):
        self._tokenized = [tokenize(c["text"]) for c in self.chunks]
        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(self._tokenized)
            self.sparse_backend = "rank_bm25.BM25Okapi"
        except Exception:
            # Vendored minimal BM25Okapi so the pipeline still runs with zero
            # third-party deps in fully offline sandboxes. Same Okapi BM25
            # formula (k1=1.5, b=0.75); swapped for the real library
            # automatically whenever it's installed.
            self._bm25 = _MiniBM25(self._tokenized)
            self.sparse_backend = "vendored-mini-bm25"

    # ----------------------------------------------------------------- dense
    def _build_dense(self):
        self.dense_backend = "tfidf"
        self._st_model = None
        self._vector_store = None
        self._id_to_idx = {c["chunk_id"]: i for i, c in enumerate(self.chunks)}

        try:
            from .vector_store import ChromaVectorStore

            vs = ChromaVectorStore()
            if not vs.is_populated(len(self.chunks)):
                vs.rebuild(self.chunks)
            self._vector_store = vs
            self.dense_backend = f"chromadb (persistent) / {vs.embedding_backend}"
            return
        except Exception:
            pass  # chromadb not installed / failed to init -- fall through

        try:
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._dense_matrix = self._st_model.encode(
                [c["text"] for c in self.chunks], normalize_embeddings=True
            )
            self.dense_backend = "sentence-transformers/all-MiniLM-L6-v2 (in-memory, not persisted)"
            return
        except Exception:
            pass

        # Fallback dense model: TF-IDF + cosine. Still a distinct signal
        # from BM25's term-frequency/length-normalised ranking because it
        # uses smooth idf + L2-normalised cosine rather than BM25's
        # saturation function, so fusing the two is meaningful.
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._tfidf = TfidfVectorizer(tokenizer=tokenize, lowercase=False)
            self._dense_matrix = self._tfidf.fit_transform([c["text"] for c in self.chunks])
            self.dense_backend = "tfidf/sklearn (in-memory, not persisted)"
        except Exception:
            # Vendored minimal TF-IDF (no scikit-learn dependency).
            self._tfidf = _MiniTfidf(tokenize)
            self._dense_matrix = self._tfidf.fit_transform([c["text"] for c in self.chunks])
            self.dense_backend = "tfidf/vendored (in-memory, not persisted)"

    def _dense_query_vec(self, query: str):
        if self._st_model is not None:
            return self._st_model.encode([query], normalize_embeddings=True)[0]
        return self._tfidf.transform([query])

    def _dense_scores(self, query: str) -> np.ndarray:
        qv = self._dense_query_vec(query)
        if self._st_model is not None:
            return self._dense_matrix @ qv
        if hasattr(qv, "toarray"):
            qv = qv.toarray()
        qv = np.asarray(qv).reshape(-1)
        if hasattr(self._dense_matrix, "toarray"):
            sims = self._dense_matrix @ qv  # sparse @ dense-vector -> dense ndarray
            sims = np.asarray(sims).ravel()
        else:
            sims = np.asarray(self._dense_matrix) @ qv
        return sims

    def _dense_rank(self, query: str, top_k: int) -> dict[int, int]:
        """Returns {chunk_index: rank (1-based, best first)} for the top_k
        dense hits, regardless of which dense backend is active."""
        if self._vector_store is not None:
            hits = self._vector_store.query(query, top_k)  # [(chunk_id, distance), ...] best first
            return {
                self._id_to_idx[cid]: r + 1
                for r, (cid, _dist) in enumerate(hits)
                if cid in self._id_to_idx
            }
        dense_scores = self._dense_scores(query)
        dense_order = np.argsort(-dense_scores)[:top_k]
        return {int(idx): r + 1 for r, idx in enumerate(dense_order)}

    # --------------------------------------------------------------- search
    def search(self, query: str, top_k_each: int = 15, top_k_final: int = 6) -> list[RetrievedChunk]:
        bm25_scores = self._bm25.get_scores(tokenize(query))
        sparse_order = np.argsort(-bm25_scores)[:top_k_each]
        sparse_rank = {int(idx): r + 1 for r, idx in enumerate(sparse_order)}
        dense_rank = self._dense_rank(query, top_k_each)

        candidates = set(sparse_rank) | set(dense_rank)
        k_rrf = 60
        fused: list[RetrievedChunk] = []
        for idx in candidates:
            c = self.chunks[idx]
            sr = sparse_rank.get(idx)
            dr = dense_rank.get(idx)
            score = 0.0
            if sr is not None:
                score += 1.0 / (k_rrf + sr)
            if dr is not None:
                score += 1.0 / (k_rrf + dr)
            fused.append(
                RetrievedChunk(
                    chunk_id=c["chunk_id"],
                    section=c["section"],
                    subsection=c.get("subsection"),
                    page_start=c["page_start"],
                    page_end=c["page_end"],
                    text=c["text"],
                    sparse_rank=sr,
                    dense_rank=dr,
                    fused_score=score,
                )
            )
        fused.sort(key=lambda x: -x.fused_score)
        shortlist = fused[: max(top_k_final * 3, 10)]

        reranked = self.reranker.rerank(query, shortlist)
        return reranked[:top_k_final]

    def search_many(self, queries: list[str], top_k_each: int = 15, top_k_final: int = 4) -> dict[str, list[RetrievedChunk]]:
        return {q: self.search(q, top_k_each=top_k_each, top_k_final=top_k_final) for q in queries}


# --------------------------------------------------------------------------- #
# Vendored minimal implementations, used only when rank_bm25 / scikit-learn   #
# are not installed, so this module has zero hard third-party dependencies   #
# beyond numpy. Both are swapped out automatically for the real library      #
# whenever it's importable (see _build_sparse / _build_dense above).         #
# --------------------------------------------------------------------------- #
class _MiniBM25:
    """Minimal Okapi BM25 (k1=1.5, b=0.75) over pre-tokenized documents."""

    def __init__(self, tokenized_docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = tokenized_docs
        self.doc_lens = [len(d) for d in tokenized_docs]
        self.avgdl = sum(self.doc_lens) / max(len(tokenized_docs), 1)
        self.df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        for doc in tokenized_docs:
            counts: dict[str, int] = {}
            for t in doc:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                self.df[t] = self.df.get(t, 0) + 1
        n = len(tokenized_docs)
        self.idf = {t: np.log(1 + (n - df + 0.5) / (df + 0.5)) for t, df in self.df.items()}

    def get_scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(len(self.docs))
        for i, (counts, dl) in enumerate(zip(self.tf, self.doc_lens)):
            s = 0.0
            for t in query_tokens:
                if t not in counts:
                    continue
                idf = self.idf.get(t, 0.0)
                f = counts[t]
                denom = f + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1e-9))
                s += idf * (f * (self.k1 + 1)) / max(denom, 1e-9)
            scores[i] = s
        return scores


class _MiniTfidf:
    """Minimal TF-IDF vectorizer with L2-normalised output (dense numpy),
    API-compatible enough with sklearn's TfidfVectorizer for this module's
    needs (fit_transform / transform)."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None

    def fit_transform(self, docs: list[str]) -> np.ndarray:
        tokenized = [self.tokenizer(d) for d in docs]
        vocab_set = sorted({t for doc in tokenized for t in doc})
        self.vocab = {t: i for i, t in enumerate(vocab_set)}
        n_docs, n_terms = len(docs), len(vocab_set)
        tf = np.zeros((n_docs, n_terms))
        for i, doc in enumerate(tokenized):
            for t in doc:
                tf[i, self.vocab[t]] += 1
        df = (tf > 0).sum(axis=0)
        self.idf = np.log((1 + n_docs) / (1 + df)) + 1
        mat = tf * self.idf
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return mat / norms

    def transform(self, docs: list[str]) -> np.ndarray:
        tokenized = [self.tokenizer(d) for d in docs]
        n_docs, n_terms = len(docs), len(self.vocab)
        tf = np.zeros((n_docs, n_terms))
        for i, doc in enumerate(tokenized):
            for t in doc:
                if t in self.vocab:
                    tf[i, self.vocab[t]] += 1
        mat = tf * self.idf
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return mat / norms
