"""Embeddings: OpenAI-compatible API or local TF-IDF fallback."""
from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_EMBEDDING_MODEL, llm_configured


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


class TfidfEmbedder:
    """Offline embedder so the prototype always runs without sentence-transformers."""

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=4096,
            ngram_range=(1, 2),
            stop_words="english",
        )
        self._fitted = False
        self._matrix: np.ndarray | None = None

    def fit(self, texts: list[str]) -> np.ndarray:
        mat = self._vectorizer.fit_transform(texts)
        self._fitted = True
        arr = mat.astype(np.float32).toarray()
        # L2 normalize for inner-product = cosine
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        self._matrix = arr / norms
        return self._matrix

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            return self.fit(texts)
        arr = self._vectorizer.transform(texts).astype(np.float32).toarray()
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        return arr / norms

    def embed_query(self, text: str) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfEmbedder must be fit on corpus first")
        return self.embed_documents([text])[0]


class OpenAIEmbedder:
    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.model = model or OPENAI_EMBEDDING_MODEL or "text-embedding-3-small"
        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        out = []
        batch = 64
        for i in range(0, len(texts), batch):
            resp = self.client.embeddings.create(model=self.model, input=texts[i : i + batch])
            out.extend([d.embedding for d in resp.data])
        arr = np.array(out, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
        return arr / norms

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


def get_embedder(prefer_api: bool = True) -> tuple[object, str]:
    if prefer_api and llm_configured() and OPENAI_EMBEDDING_MODEL:
        try:
            return OpenAIEmbedder(), f"openai:{OPENAI_EMBEDDING_MODEL}"
        except Exception:
            pass
    return TfidfEmbedder(), "local:tfidf"


def fingerprint(texts: list[str]) -> str:
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]
