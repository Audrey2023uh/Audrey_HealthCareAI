"""FAISS vector store build + evidence-tier hybrid search."""
from __future__ import annotations

import json
from typing import Any

import faiss
import numpy as np

from src.config import CANDIDATE_K, CHUNKS_JSON, FAISS_INDEX, INDEX_DIR, TOP_K
from src.embeddings import TfidfEmbedder, get_embedder
from src.evidence_rank import annotate_missing_metadata, rerank_hits
from src.ingest import chunks_to_dicts, documents_to_chunks, load_seed_documents


class VectorStore:
    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.chunks: list[dict[str, Any]] = []
        self.embedder: Any = None
        self.embedder_name = ""
        self.meta: dict[str, Any] = {}

    def build_from_seed(self, force: bool = False) -> dict[str, Any]:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        docs = load_seed_documents()
        chunks = documents_to_chunks(docs)
        chunk_dicts = [annotate_missing_metadata(c) for c in chunks_to_dicts(chunks)]
        texts = [c["text"] for c in chunk_dicts]

        embedder, name = get_embedder(prefer_api=False)
        if not isinstance(embedder, TfidfEmbedder):
            embedder, name = TfidfEmbedder(), "local:tfidf"
        vectors = embedder.fit(texts) if isinstance(embedder, TfidfEmbedder) else embedder.embed_documents(texts)

        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(vectors.astype(np.float32))

        faiss.write_index(index, str(FAISS_INDEX))
        CHUNKS_JSON.write_text(json.dumps(chunk_dicts, indent=2), encoding="utf-8")

        import pickle

        tfidf_path = INDEX_DIR / "tfidf.pkl"
        with open(tfidf_path, "wb") as f:
            pickle.dump(embedder, f)

        tier_counts: dict[str, int] = {}
        for c in chunk_dicts:
            t = str(c.get("evidence_tier", "?"))
            tier_counts[t] = tier_counts.get(t, 0) + 1

        meta = {
            "n_docs": len(docs),
            "n_chunks": len(chunk_dicts),
            "dim": dim,
            "embedder": name,
            "sources": sorted({d.source_type for d in docs}),
            "ranking": "priority_1_to_7_then_quality_within_priority",
            "tier_chunk_counts": tier_counts,
            "n_superseded": sum(1 for d in docs if d.superseded),
        }
        (INDEX_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        self.index = index
        self.chunks = chunk_dicts
        self.embedder = embedder
        self.embedder_name = name
        self.meta = meta
        return meta

    def load(self) -> None:
        if not FAISS_INDEX.exists() or not CHUNKS_JSON.exists():
            self.build_from_seed()
            return
        import pickle

        self.index = faiss.read_index(str(FAISS_INDEX))
        self.chunks = [annotate_missing_metadata(c) for c in json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))]
        tfidf_path = INDEX_DIR / "tfidf.pkl"
        if tfidf_path.exists():
            with open(tfidf_path, "rb") as f:
                self.embedder = pickle.load(f)
            self.embedder_name = "local:tfidf"
        else:
            self.embedder, self.embedder_name = get_embedder()
        meta_path = INDEX_DIR / "meta.json"
        self.meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    def search(
        self,
        query: str,
        top_k: int = TOP_K,
        candidate_k: int = CANDIDATE_K,
        use_tier_rerank: bool = True,
    ) -> list[dict[str, Any]]:
        if self.index is None:
            self.load()
        assert self.index is not None and self.embedder is not None

        pool = min(max(candidate_k, top_k), len(self.chunks))
        q = self.embedder.embed_query(query).astype(np.float32).reshape(1, -1)
        scores, idxs = self.index.search(q, pool)

        hits: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0:
                continue
            item = dict(self.chunks[int(idx)])
            item["semantic_score"] = float(score)
            item["score"] = float(score)
            hits.append(item)

        if not use_tier_rerank:
            return hits[:top_k]

        return rerank_hits(hits, query=query, top_k=top_k)


_STORE: VectorStore | None = None


def get_store() -> VectorStore:
    global _STORE
    if _STORE is None:
        _STORE = VectorStore()
        _STORE.load()
    return _STORE
