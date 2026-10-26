"""ChromaDB persistent vector store."""

from __future__ import annotations

import os
from functools import lru_cache

# Avoid posthog telemetry crashes/noise on some dependency combos (Chroma 0.5.x).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.config import get_settings

COLLECTION_NAME = "shopsphere_documents"


@lru_cache
def get_chroma_client() -> ClientAPI:
    settings = get_settings()
    settings.chroma_directory.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_directory))


def get_document_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_document_collection() -> Collection:
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except (ValueError, chromadb.errors.NotFoundError):
        pass
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_document_count() -> int:
    return get_document_collection().count()


def clear_chroma_cache() -> None:
    get_chroma_client.cache_clear()
