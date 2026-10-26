"""Corpus registry: writes files and records one manifest row per file."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .render import Doc, Email, write_docx, write_eml, write_pdf, write_txt

MANIFEST_COLUMNS = (
    "filename",
    "document_type",
    "return_id",
    "product_id",
    "policy_version",
    "effective_date",
    "file_path",
)

FOLDER_BY_TYPE = {
    "return_policy": "policies",
    "warranty": "warranties",
    "inspection_report": "inspections",
    "customer_complaint": "complaints",
    "supplier_defect_report": "supplier_reports",
    "support_communication": "communications",
    "refurbishment_guideline": "refurbishment",
}


@dataclass
class ManifestRow:
    filename: str
    document_type: str
    return_id: str
    product_id: str
    policy_version: str
    effective_date: str
    file_path: str
    text: str  # flattened content, kept in memory for verification only


class Corpus:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.unstructured = repo_root / "data" / "unstructured"
        self.rows: list[ManifestRow] = []

    def _target(self, document_type: str, filename: str) -> Path:
        # Lowercase with underscores; return IDs keep their canonical form (R102).
        if not re.fullmatch(r"[a-z0-9_.]+", re.sub(r"R\d{3}", "", filename)):
            raise ValueError(f"Filenames must be lowercase with underscores: {filename}")
        if any(row.filename == filename for row in self.rows):
            raise ValueError(f"Duplicate filename: {filename}")
        return self.unstructured / FOLDER_BY_TYPE[document_type] / filename

    def _record(
        self,
        path: Path,
        document_type: str,
        effective_date: str,
        text: str,
        return_id: str = "",
        product_id: str = "",
        policy_version: str = "",
    ) -> None:
        self.rows.append(
            ManifestRow(
                filename=path.name,
                document_type=document_type,
                return_id=return_id,
                product_id=product_id,
                policy_version=policy_version,
                effective_date=effective_date,
                file_path=path.relative_to(self.repo_root).as_posix(),
                text=text,
            )
        )

    def add_doc(self, doc: Doc, filename: str, document_type: str, effective_date: str, **meta: str) -> None:
        path = self._target(document_type, filename)
        if filename.endswith(".pdf"):
            write_pdf(doc, path)
        elif filename.endswith(".docx"):
            write_docx(doc, path)
        else:
            raise ValueError(f"Unsupported document format: {filename}")
        self._record(path, document_type, effective_date, doc.plain_text(), **meta)

    def add_email(self, email: Email, filename: str, document_type: str, **meta: str) -> None:
        path = self._target(document_type, filename)
        write_eml(email, path)
        text = f"{email.subject}\n{email.body}"
        self._record(path, document_type, email.sent_at.strftime("%Y-%m-%d"), text, **meta)

    def add_text(self, text: str, filename: str, document_type: str, effective_date: str, **meta: str) -> None:
        path = self._target(document_type, filename)
        write_txt(text, path)
        self._record(path, document_type, effective_date, text, **meta)

    def write_manifest(self) -> Path:
        path = self.repo_root / "data" / "ground_truth" / "document_manifest.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(self.rows, key=lambda r: r.file_path)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(MANIFEST_COLUMNS)
            for row in rows:
                writer.writerow([getattr(row, column) for column in MANIFEST_COLUMNS])
        return path
