"""
Persistent vector store for the dense half of hybrid retrieval, using
Chroma (free, open-source, embedded -- no external server/process
required, just a local directory). This replaces the earlier fully
in-memory embedding matrix, which had to be rebuilt from scratch on every
process restart; a production deployment should not re-embed 100+ policy
chunks on every cold start.

Falls back automatically (see retrieval.py) to the in-memory
sentence-transformers/TF-IDF matrix if `chromadb` isn't installed, so the
system still runs with zero extra services in constrained environments --
but production deployments should keep `chromadb` in requirements.txt
(already added) to get real persistence.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_PERSIST_DIR = Path(
    os.getenv("VECTOR_DB_DIR", str(Path(__file__).resolve().parent.parent / "data" / "chroma"))
)
COLLECTION_NAME = "policy_chunks"


class ChromaVectorStore:
    """Thin wrapper around a local, persistent Chroma collection."""

    def __init__(self, persist_dir: Path = DEFAULT_PERSIST_DIR):
        import chromadb
        from chromadb.utils import embedding_functions

        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))

        try:
            self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            )
            self.embedding_backend = f"sentence-transformers/{os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')}"
        except Exception:
            # Chroma's bundled default embedding function (onnx MiniLM) --
            # still free/local, just a different weights source.
            self.embed_fn = embedding_functions.DefaultEmbeddingFunction()
            self.embedding_backend = "chromadb-default-onnx-minilm"

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.embed_fn,
        )

    def is_populated(self, expected_count: int) -> bool:
        try:
            return self.collection.count() == expected_count
        except Exception:
            return False

    def rebuild(self, chunks: list[dict]):
        """Clear and re-populate so a re-ingested policy never leaves stale
        chunks behind (Chroma collections are additive/upsert by default)."""
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self.embed_fn,
        )
        ids = [c["chunk_id"] for c in chunks]
        docs = [c["text"] for c in chunks]
        metas = [
            {
                "section": c["section"],
                "subsection": c.get("subsection") or "",
                "page_start": c["page_start"],
                "page_end": c["page_end"],
            }
            for c in chunks
        ]
        batch = 100  # stay well under backend per-call batch limits
        for i in range(0, len(ids), batch):
            self.collection.add(
                ids=ids[i:i + batch], documents=docs[i:i + batch], metadatas=metas[i:i + batch],
            )

    def query(self, text: str, top_k: int) -> list[tuple[str, float]]:
        """Returns [(chunk_id, distance), ...] ordered best (smallest distance) first."""
        res = self.collection.query(query_texts=[text], n_results=top_k)
        ids = res["ids"][0]
        dists = res["distances"][0]
        return list(zip(ids, dists))
