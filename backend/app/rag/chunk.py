"""Split extracted text into overlapping chunks for embedding."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.extract import ExtractedDocument, TextSegment

# ~600 tokens at ~4 characters per token
DEFAULT_CHUNK_SIZE = 2400
DEFAULT_CHUNK_OVERLAP = 300


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    text: str
    page: int | None
    section: str | None


def chunk_document(
    extracted: ExtractedDocument,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for segment in extracted.segments:
        for piece in _split_segment_text(segment.text, chunk_size, overlap):
            chunks.append(
                DocumentChunk(
                    chunk_index=chunk_index,
                    text=piece,
                    page=segment.page,
                    section=segment.section,
                )
            )
            chunk_index += 1

    if not chunks and extracted.full_text:
        chunks.append(
            DocumentChunk(
                chunk_index=0,
                text=extracted.full_text[:chunk_size],
                page=None,
                section=None,
            )
        )
    return chunks


def _split_segment_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return pieces
