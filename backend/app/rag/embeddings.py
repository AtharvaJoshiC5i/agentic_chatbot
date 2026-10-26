"""Embedding model wrapper (configurable via settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode([text], show_progress_bar=False, normalize_embeddings=True)[0]
        return vector.tolist()


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return SentenceTransformerEmbedder(settings.embedding_model)


def clear_embedder_cache() -> None:
    get_embedder.cache_clear()
