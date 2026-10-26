"""Load document_manifest.csv into SQLite document_metadata."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.models.tables import DocumentMetadata, Product, Return

MANIFEST_PATH = PROJECT_ROOT / "data" / "ground_truth" / "document_manifest.csv"


@dataclass
class ManifestLoadReport:
    rows_read: int
    rows_inserted: int
    missing_files: list[str]
    invalid_return_ids: list[str]
    invalid_product_ids: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_files and not self.invalid_return_ids and not self.invalid_product_ids


def _parse_effective_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    parsed = datetime.strptime(raw, "%Y-%m-%d")
    return parsed.replace(tzinfo=timezone.utc)


def load_document_metadata_from_manifest(
    session: Session,
    manifest_path: Path | None = None,
    *,
    clear_existing: bool = True,
) -> ManifestLoadReport:
    path = manifest_path or MANIFEST_PATH
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    valid_returns = set(session.execute(select(Return.return_id)).scalars().all())
    valid_products = set(session.execute(select(Product.product_id)).scalars().all())

    missing_files: list[str] = []
    invalid_return_ids: list[str] = []
    invalid_product_ids: list[str] = []
    rows_to_insert: list[dict] = []

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            file_path = row["file_path"].strip().replace("\\", "/")
            absolute = (PROJECT_ROOT / file_path).resolve()
            if not absolute.is_file():
                missing_files.append(file_path)
                continue

            return_id = (row.get("return_id") or "").strip() or None
            product_id = (row.get("product_id") or "").strip() or None
            if return_id and return_id not in valid_returns:
                invalid_return_ids.append(return_id)
            if product_id and product_id not in valid_products:
                invalid_product_ids.append(product_id)

            policy_version = (row.get("policy_version") or "").strip() or None
            effective = _parse_effective_date(row.get("effective_date", ""))
            created_at = effective or datetime.now(timezone.utc)

            rows_to_insert.append(
                {
                    "filename": row["filename"].strip(),
                    "document_type": row["document_type"].strip(),
                    "return_id": return_id,
                    "product_id": product_id,
                    "created_at": created_at,
                    "policy_version": policy_version,
                    "effective_date": effective,
                    "file_path": file_path,
                }
            )

    if missing_files or invalid_return_ids or invalid_product_ids:
        return ManifestLoadReport(
            rows_read=len(rows_to_insert) + len(missing_files),
            rows_inserted=0,
            missing_files=missing_files,
            invalid_return_ids=invalid_return_ids,
            invalid_product_ids=invalid_product_ids,
        )

    if clear_existing:
        session.execute(delete(DocumentMetadata))
        session.flush()

    session.bulk_insert_mappings(DocumentMetadata, rows_to_insert)
    session.commit()

    return ManifestLoadReport(
        rows_read=len(rows_to_insert),
        rows_inserted=len(rows_to_insert),
        missing_files=[],
        invalid_return_ids=[],
        invalid_product_ids=[],
    )
