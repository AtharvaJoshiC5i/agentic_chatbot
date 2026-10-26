"""Retrieval-augmented generation: extract, chunk, embed, search."""

from app.rag.search import DocumentSearchResult, get_applicable_policy, search_documents

__all__ = ["DocumentSearchResult", "get_applicable_policy", "search_documents"]
