"""Ingest document_metadata rows into ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.models.enums import DocumentType
from app.models.tables import DocumentMetadata, Product
from app.rag.chunk import chunk_document
from app.rag.embeddings import Embedder, get_embedder
from app.rag.extract import extract_document
from app.rag.store import get_document_collection, reset_document_collection

POLICY_CATEGORY_KEYWORDS: dict[str, str] = {
    "electronics": "electronics",
    "fashion": "fashion",
    "home_appliances": "home_appliances",
    "accessories": "accessories",
    "damaged": "damaged_products",
}


@dataclass
class IngestReport:
    documents_processed: int
    chunks_indexed: int
    failures: list[str]


def _infer_policy_category(file_path: str, product_category: str | None) -> str | None:
    lowered = file_path.lower()
    for keyword, category in POLICY_CATEGORY_KEYWORDS.items():
        if keyword in lowered:
            return category
    return product_category


def ingest_all_documents(
    session: Session,
    *,
    embedder: Embedder | None = None,
    reset_index: bool = True,
) -> IngestReport:
    embedder = embedder or get_embedder()
    collection = reset_document_collection() if reset_index else get_document_collection()

    documents = session.execute(select(DocumentMetadata).order_by(DocumentMetadata.document_id)).scalars().all()
    product_categories = {
        product_id: category
        for product_id, category in session.execute(select(Product.product_id, Product.category)).all()
    }

    failures: list[str] = []
    total_chunks = 0
    processed = 0

    for document in documents:
        absolute_path = (PROJECT_ROOT / document.file_path).resolve()
        try:
            extracted = extract_document(absolute_path)
            chunks = chunk_document(extracted)
            if not chunks:
                failures.append(f"{document.file_path}: no chunks produced")
                continue

            product_category = (
                product_categories.get(document.product_id) if document.product_id else None
            )
            policy_category = None
            if document.document_type == DocumentType.RETURN_POLICY.value:
                policy_category = _infer_policy_category(document.file_path, product_category)

            ids: list[str] = []
            texts: list[str] = []
            metadatas: list[dict] = []

            for chunk in chunks:
                chunk_id = f"doc{document.document_id}:chunk{chunk.chunk_index}"
                ids.append(chunk_id)
                texts.append(chunk.text)
                metadatas.append(
                    _chunk_metadata(
                        document=document,
                        chunk_index=chunk.chunk_index,
                        page=chunk.page,
                        section=chunk.section,
                        policy_category=policy_category,
                    )
                )

            embeddings = embedder.embed_documents(texts)
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            processed += 1
            total_chunks += len(chunks)
        except Exception as exc:  # noqa: BLE001 — collect per-file failures for batch ingest
            failures.append(f"{document.file_path}: {exc}")

    return IngestReport(
        documents_processed=processed,
        chunks_indexed=total_chunks,
        failures=failures,
    )


def _chunk_metadata(
    *,
    document: DocumentMetadata,
    chunk_index: int,
    page: int | None,
    section: str | None,
    policy_category: str | None,
) -> dict:
    effective = document.effective_date.isoformat() if document.effective_date else ""
    metadata = {
        "document_id": document.document_id,
        "filename": document.filename,
        "document_type": document.document_type,
        "return_id": document.return_id or "",
        "product_id": document.product_id or "",
        "policy_version": document.policy_version or "",
        "effective_date": effective,
        "file_path": document.file_path,
        "chunk_index": chunk_index,
        "page": page if page is not None else -1,
        "section": section or "",
        "policy_category": policy_category or "",
    }
    return metadata
