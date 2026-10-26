"""Batch E: verification checks and docs/README_UNSTRUCTURED.md."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .context import SCENARIO_IDS, ShopSphereData
from .corpus import FOLDER_BY_TYPE, Corpus

TARGET_COUNTS = {
    "policies": 5,
    "warranties": 10,
    "inspections": 30,
    "complaints": 50,
    "supplier_reports": 10,
    "communications": 30,
    "refurbishment": 5,
}

FORBIDDEN = re.compile(
    r"\bfraud\w*|\bscam\w*|ignore (all |any |previous |prior )?instructions|approve (the )?refunds? automatically|"
    r"auto-?approve|system prompt|disregard (the )?(policy|rules)",
    re.IGNORECASE,
)
REAL_BRANDS = re.compile(
    r"\b(apple|samsung|sony|bose|dell|lenovo|xiaomi|philips|dyson|nike|adidas|levi'?s|oneplus|jbl|asus|acer|whirlpool)\b",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[\w-]+")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def _load_document_types(repo_root: Path) -> set[str]:
    sys.path.insert(0, str(repo_root / "backend"))
    from app.models.enums import DocumentType  # noqa: PLC0415

    return {member.value for member in DocumentType}


def _extract_pdf_text(path: Path) -> str | None:
    try:
        from pypdf import PdfReader  # noqa: PLC0415
    except ImportError:
        return None
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def _extract_docx_text(path: Path) -> str:
    from docx import Document  # noqa: PLC0415

    document = Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts += [cell.text for cell in row.cells]
    return "\n".join(parts)


def verify(corpus: Corpus, data: ShopSphereData) -> list[Check]:
    root = corpus.repo_root
    checks: list[Check] = []
    rows = corpus.rows

    # 1. File counts
    on_disk = sorted(p for p in corpus.unstructured.rglob("*") if p.is_file())
    checks.append(Check("At least 140 files under data/unstructured/", len(on_disk) >= 140, f"{len(on_disk)} files"))
    per_folder = Counter(p.parent.name for p in on_disk)
    for folder, target in TARGET_COUNTS.items():
        checks.append(Check(f"{folder}/ has {target} files", per_folder[folder] == target, f"{per_folder[folder]} files"))

    # 2. Manifest consistency (read back from disk, not memory)
    manifest_path = root / "data" / "ground_truth" / "document_manifest.csv"
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    disk_paths = {p.relative_to(root).as_posix() for p in on_disk}
    manifest_paths = [m["file_path"] for m in manifest]
    checks.append(Check("Manifest rows = files on disk", len(manifest) == len(on_disk), f"{len(manifest)} rows / {len(on_disk)} files"))
    checks.append(Check("Every manifest file_path exists", all((root / p).is_file() for p in manifest_paths)))
    checks.append(Check("No unlisted files on disk", disk_paths == set(manifest_paths), ", ".join(sorted(disk_paths - set(manifest_paths))) or ""))
    checks.append(Check("Manifest filenames are unique", len({m["filename"] for m in manifest}) == len(manifest)))
    valid_types = _load_document_types(root)
    checks.append(Check("document_type values match DocumentType enum", all(m["document_type"] in valid_types for m in manifest)))
    checks.append(
        Check(
            "document_type matches folder",
            all(Path(m["file_path"]).parent.name == FOLDER_BY_TYPE[m["document_type"]] for m in manifest),
        )
    )
    checks.append(Check("Manifest return_ids exist in SQLite", all(not m["return_id"] or m["return_id"] in data.returns for m in manifest)))
    checks.append(Check("Manifest product_ids exist in SQLite", all(not m["product_id"] or m["product_id"] in data.products for m in manifest)))
    checks.append(Check("effective_date is YYYY-MM-DD", all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", m["effective_date"]) for m in manifest)))

    # 3. SQLite scenario checks
    r102, r106, r110, r113 = (data.get(x) for x in ("R102", "R106", "R110", "R113"))
    checks.append(
        Check(
            "SQLite: R102 purchased HP9081, returned HP9012",
            r102["purchased_serial_number"] == "HP9081" and r102.inspections[0]["returned_serial_number"] == "HP9012",
        )
    )
    checks.append(Check("SQLite: R106 has exactly one completed refund", sum(r["refund_status"] == "completed" for r in r106.refunds) == 1))
    checks.append(Check("SQLite: R113 has no inspection row", len(r113.inspections) == 0))
    checks.append(
        Check(
            "SQLite: R110 has two inspection rows that disagree",
            len(r110.inspections) == 2 and len({i["defect_verified"] for i in r110.inspections}) == 2,
        )
    )
    inspection_rows_in_db = sum(len(ctx.inspections) for ctx in data.returns.values())
    insp_docs = [r for r in rows if r.document_type == "inspection_report"]
    checks.append(Check("Each inspection document maps to a SQLite inspection row", all(data.get(r.return_id).inspections for r in insp_docs), f"{len(insp_docs)} docs; {inspection_rows_in_db} rows in DB"))

    # 4. Scenario content checks (manifest + text)
    def texts(return_id: str, doc_type: str) -> list[str]:
        return [r.text for r in rows if r.return_id == return_id and r.document_type == doc_type]

    checks.append(Check("Manifest: no inspection_report row for R113", not any(m["return_id"] == "R113" and m["document_type"] == "inspection_report" for m in manifest)))
    checks.append(Check("R102 inspection states HP9081 vs HP9012 mismatch", any("HP9081" in t and "HP9012" in t and "MISMATCH" in t for t in texts("R102", "inspection_report"))))
    r110_docs = texts("R110", "inspection_report")
    checks.append(
        Check(
            "R110 has two conflicting inspection documents",
            len(r110_docs) == 2 and any("Defect verified: Yes" in t for t in r110_docs) and any("Defect verified: No" in t for t in r110_docs),
        )
    )
    checks.append(Check("R106 communication states refund already completed", any("already been completed" in t for t in texts("R106", "support_communication"))))
    checks.append(Check("R108 inspection records keyboard damage, repairable", any("keyboard" in t.lower() and "repairable" in t.lower() for t in texts("R108", "inspection_report"))))
    checks.append(Check("R108 laptop refurbishment guideline present", bool(texts("R108", "refurbishment_guideline"))))
    checks.append(Check("R115 inspection: unsafe / no resale", any("unsafe" in t.lower() and "NO RESALE" in t for t in texts("R115", "inspection_report"))))
    checks.append(Check("R115 safety guideline: no resale, recycle/dispose only", any("never be resold" in t for t in texts("R115", "refurbishment_guideline"))))
    checks.append(Check("R103 complaint/communication cites >30 days after delivery", any("55 days" in t for t in texts("R103", "support_communication") + texts("R103", "inspection_report"))))
    delivery_issue = data.get("R104")["delivery_issue"]
    checks.append(Check("R104 documents cite the recorded delivery issue", any(delivery_issue in t for r in ("support_communication", "inspection_report") for t in texts("R104", r))))
    elec = [r.text for r in rows if r.filename.startswith("return_policy_electronics")]
    checks.append(Check("Electronics policy: 30 days from delivery", bool(elec) and "30 days from delivery" in elec[0]))
    word_counts = [len(r.text.split()) for r in insp_docs]
    checks.append(Check("Inspection reports have at least 200 words", min(word_counts) >= 200, f"min {min(word_counts)} words"))

    # 5. Safety of content
    bad = [r.filename for r in rows if FORBIDDEN.search(r.text)]
    checks.append(Check("No fraud accusations or prompt-injection phrases", not bad, ", ".join(bad)))
    brands = [r.filename for r in rows if REAL_BRANDS.search(r.text)]
    checks.append(Check("No real-world brand names", not brands, ", ".join(brands)))
    eml_addresses = []
    for path in on_disk:
        if path.suffix in (".eml", ".txt"):
            eml_addresses += [m.group(0) for m in EMAIL.finditer(path.read_text(encoding="utf-8"))]
    non_invalid = sorted({a for a in eml_addresses if not a.endswith(".invalid")})
    checks.append(Check("All email addresses use .invalid domains", not non_invalid, ", ".join(non_invalid)))

    # 6. Extractable text from binary documents (read back from disk)
    docx_ok = all(len(_extract_docx_text(p).split()) > 50 for p in on_disk if p.suffix == ".docx")
    checks.append(Check("DOCX files have extractable text", docx_ok))
    pdfs = [p for p in on_disk if p.suffix == ".pdf"]
    sample = _extract_pdf_text(pdfs[0]) if pdfs else ""
    if sample is None:
        checks.append(Check("PDF files have extractable text", True, "skipped: pypdf not installed"))
    else:
        extracted = {p.name: _extract_pdf_text(p) or "" for p in pdfs}
        empty = [name for name, text in extracted.items() if len(text.split()) < 50]
        checks.append(Check("PDF files have extractable text", not empty, ", ".join(empty)))
        garbled = [name for name, text in extracted.items() if "�" in text]
        checks.append(Check("PDF text extracts without replacement characters", not garbled, ", ".join(garbled)))
    return checks


# --------------------------------------------------------------------- README


def write_readme(corpus: Corpus, data: ShopSphereData, checks: list[Check], bulk_inspection_ids: list[str]) -> Path:
    rows = sorted(corpus.rows, key=lambda r: r.file_path)
    by_folder: dict[str, list] = defaultdict(list)
    for row in rows:
        by_folder[Path(row.file_path).parent.name].append(row)

    lines: list[str] = []
    add = lines.append
    add("# ShopSphere unstructured document corpus (Phase 4)")
    add("")
    add("Synthetic documents for the ShopSphere AI Returns Agent's RAG index (Phase 5). Every ID, serial number, date, status and amount comes from `backend/shopsphere.db`. Documents never contradict SQLite; the only intended cross-document conflict is **R110** (two inspection reports that disagree, matching its two inspection rows).")
    add("")
    add("## Regenerate")
    add("")
    add("```bash")
    add("backend/.venv/Scripts/python scripts/generate_unstructured_documents.py")
    add("```")
    add("")
    add("The generator is deterministic and idempotent: re-running it produces byte-identical files. It reads SQLite read-only, regenerates every file under `data/unstructured/` in place, rebuilds `data/ground_truth/document_manifest.csv` and this README, then runs the verification checks and exits non-zero if any fail. Any file in `data/unstructured/` that the generator did not produce is reported as a failure, so files are never silently duplicated. Dependencies are `reportlab`, `python-docx` and `pypdf` (for the PDF text check), all listed in `backend/requirements.txt`. Code: `scripts/unstructured/`.")
    add("")
    add("## Counts by folder")
    add("")
    add("| Folder | document_type | Files | Target | Formats |")
    add("|---|---|---:|---:|---|")
    type_by_folder = {v: k for k, v in FOLDER_BY_TYPE.items()}
    for folder, target in TARGET_COUNTS.items():
        files = by_folder[folder]
        formats = Counter(Path(r.filename).suffix.lstrip(".").upper() for r in files)
        fmt = ", ".join(f"{k} {v}" for k, v in sorted(formats.items()))
        add(f"| `data/unstructured/{folder}/` | `{type_by_folder[folder]}` | {len(files)} | {target} | {fmt} |")
    add(f"| **Total** | | **{len(rows)}** | **{sum(TARGET_COUNTS.values())}** | |")
    add("")
    add("## Manifest")
    add("")
    add("`data/ground_truth/document_manifest.csv` has one row per file, with columns `filename,document_type,return_id,product_id,policy_version,effective_date,file_path`. Paths use forward slashes and are relative to the repository root. `policy_version` is filled for version-controlled documents (policies, warranties, refurbishment guidelines). `effective_date` is the policy effective date or the document date. Empty `return_id`/`product_id` means the document is not tied to one return or product.")
    add("")
    add("## Scenario coverage (R101–R115)")
    add("")
    add("| Return | Scenario | Product (SQLite) | Inspection | Complaint | Support comms | Other | Key evidence |")
    add("|---|---|---|---:|---:|---:|---|---|")
    from app.synthetic.scenarios import SCENARIO_BY_RETURN_ID  # noqa: PLC0415 (backend on sys.path after verify)

    key_evidence = {
        "R101": "Within window (5 days); no inconsistencies",
        "R102": "Inspection: purchased HP9081 vs received HP9012, additional verification required",
        "R103": "Requested 55 days after delivery, outside the electronics 30-day window",
        "R104": "Cites the delivery scan note: carton crushed, impact damage",
        "R105": "PD/HDMI defect verified; supplier report SDR-2026-027",
        "R106": "Comms: refund already completed on 2026-03-07; no second refund",
        "R107": "Serial HP7710 vs HP7799, missing accessories, reason mismatch",
        "R108": "Keyboard damage, repairable; laptop repair-and-resell guideline",
        "R109": "Travel pouch and user guide missing",
        "R110": "Two inspection reports disagree (verified Yes vs No)",
        "R111": "SKU label does not match the ordered item",
        "R112": "Verified failure within the 24-month warranty",
        "R113": "No inspection document (evidence gap); comms flag the missing inspection",
        "R114": "Return reason, system note and line item disagree",
        "R115": "Unsafe: scorch/melt at inlet; no resale, recycle or dispose only",
    }
    for rid in SCENARIO_IDS:
        ctx = data.get(rid)
        mine = [r for r in rows if r.return_id == rid]
        count = Counter(r.document_type for r in mine)
        other = sorted({r.document_type for r in mine} - {"inspection_report", "customer_complaint", "support_communication"})
        add(
            f"| {rid} | {SCENARIO_BY_RETURN_ID[rid].title} | {ctx['product_name']} (`{ctx['product_id']}`) | "
            f"{count['inspection_report']} | {count['customer_complaint']} | {count['support_communication']} | "
            f"{', '.join(other) or '—'} | {key_evidence[rid]} |"
        )
    add("")
    add("Supplier defect reports also cover scenario returns that are not their primary `return_id`: R102, R103, R104, R106, R107, R108, R113 (listed for information only, as it has no inspection) and R114.")
    add("")
    add("## Non-scenario documents")
    add("")
    add(f"- Inspections: {len(bulk_inspection_ids)} reports for real non-scenario inspection rows, spread across categories and condition codes: {', '.join(bulk_inspection_ids)}.")
    bulk_complaints = sorted({r.return_id for r in rows if r.document_type == 'customer_complaint' and r.return_id not in SCENARIO_IDS}, key=lambda x: int(x[1:]))
    add(f"- Complaints: {len(bulk_complaints)} complaints, chosen round-robin across all nine return reasons: {', '.join(bulk_complaints)}.")
    bulk_comms = sorted({r.return_id for r in rows if r.document_type == 'support_communication' and r.return_id not in SCENARIO_IDS}, key=lambda x: int(x[1:]))
    add(f"- Support communications: {len(bulk_comms)} lifecycle emails (refund processed, pickup scheduled, inspection in progress, under review): {', '.join(bulk_comms)}.")
    add("- Supplier reports: the four non-scenario suppliers with the most fault-related returns (damaged, defective, not_functioning), preferring one per category. Return evidence tables come from SQLite.")
    add("")
    add("## Acceptance checklist (computed at generation time)")
    add("")
    for check in checks:
        detail = f" — {check.detail}" if check.detail else ""
        add(f"- [{'x' if check.ok else ' '}] {check.name}{detail}")
    add("")
    add("## SQLite observations relevant to Phase 5")
    add("")
    add("The structured data was rebuilt with a status-driven generator (`backend/app/synthetic/bulk.py`), so the bulk returns (R116+) are internally consistent. The documents follow SQLite throughout. Notes for evaluation:")
    add("")
    add("- **Scenarios are fixed.** R101-R115 are hand-designed and byte-identical to the original dataset; only R107's account history and the explicit open refund requests for R107, R108 and R110 were made explicit.")
    add("- **R107 account history:** customer C00107 has earlier returns in SQLite (one with a serial mismatch), so the R107 inspection report cites them as context for the analyst. Each return is still assessed on its own evidence.")
    add("- **Refunds follow status.** Only R106 has a completed refund among R101-R115. Completed refunds elsewhere exist only on resolved/closed returns; open refund requests exist only on returns still being worked; returns not yet received have no refund.")
    add("- **Incomplete evidence is normal.** About 100 returns are not yet inspected (still requested, in transit, or received and awaiting inspection). R113 is one of the received-but-uninspected returns.")
    add("- **Inspection result codes:** `pass` means the defect was verified (or the unit is unsafe); `fail` means the findings do not support the claim; `inconclusive` means no defect could be confirmed or none was claimed; `pending` means testing is in progress. The reports repeat this legend.")
    add("- **R114 system note** says the line item is an \"accessory SKU\", but the order line is a fashion SKU (UrbanWeave shirt). The inspection report quotes the note verbatim and flags it as a data-correction issue.")
    add("- **Catalogue:** bulk products use fictional brands with realistic names and prices (for example `Ampere Gaming Laptop 15`); customer descriptions and inspector notes are written from the return reason and inspection facts, not placeholder text.")
    add("")
    add("## Conventions")
    add("")
    add("- File names are lowercase with underscores. Return IDs keep their canonical form, for example `inspection_R102_serial_mismatch.pdf` and `support_R106_refund_already_processed.eml`.")
    add("- Email files are RFC 5322 messages (UTF-8, 8-bit bodies) with `Message-ID`, `In-Reply-To`/`References` threading and `X-ShopSphere-Return-ID`/`X-ShopSphere-Order-ID` headers. All addresses use `.invalid` domains.")
    add("- PDF and DOCX files have real text layers. Inspection report IDs follow `IR-2026-<inspection_id>`, so every report links to its SQLite `inspections` row.")
    add("- Language is neutral. Records that disagree are described as \"additional verification required\" and never attributed to customer intent.")
    add("")

    path = corpus.repo_root / "docs" / "README_UNSTRUCTURED.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path
