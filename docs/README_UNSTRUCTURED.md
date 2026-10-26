# ShopSphere unstructured document corpus (Phase 4)

Synthetic documents for the ShopSphere AI Returns Agent's RAG index (Phase 5). Every ID, serial number, date, status and amount comes from `backend/shopsphere.db`. Documents never contradict SQLite; the only intended cross-document conflict is **R110** (two inspection reports that disagree, matching its two inspection rows).

## Regenerate

```bash
backend/.venv/Scripts/python scripts/generate_unstructured_documents.py
```

The generator is deterministic and idempotent: re-running it produces byte-identical files. It reads SQLite read-only, regenerates every file under `data/unstructured/` in place, rebuilds `data/ground_truth/document_manifest.csv` and this README, then runs the verification checks and exits non-zero if any fail. Any file in `data/unstructured/` that the generator did not produce is reported as a failure, so files are never silently duplicated. Dependencies are `reportlab`, `python-docx` and `pypdf` (for the PDF text check), all listed in `backend/requirements.txt`. Code: `scripts/unstructured/`.

## Counts by folder

| Folder | document_type | Files | Target | Formats |
|---|---|---:|---:|---|
| `data/unstructured/policies/` | `return_policy` | 5 | 5 | DOCX 2, PDF 3 |
| `data/unstructured/warranties/` | `warranty` | 10 | 10 | DOCX 5, PDF 5 |
| `data/unstructured/inspections/` | `inspection_report` | 30 | 30 | PDF 30 |
| `data/unstructured/complaints/` | `customer_complaint` | 50 | 50 | EML 30, TXT 20 |
| `data/unstructured/supplier_reports/` | `supplier_defect_report` | 10 | 10 | DOCX 5, PDF 5 |
| `data/unstructured/communications/` | `support_communication` | 30 | 30 | EML 30 |
| `data/unstructured/refurbishment/` | `refurbishment_guideline` | 5 | 5 | DOCX 2, PDF 3 |
| **Total** | | **140** | **140** | |

## Manifest

`data/ground_truth/document_manifest.csv` has one row per file, with columns `filename,document_type,return_id,product_id,policy_version,effective_date,file_path`. Paths use forward slashes and are relative to the repository root. `policy_version` is filled for version-controlled documents (policies, warranties, refurbishment guidelines). `effective_date` is the policy effective date or the document date. Empty `return_id`/`product_id` means the document is not tied to one return or product.

## Scenario coverage (R101–R115)

| Return | Scenario | Product (SQLite) | Inspection | Complaint | Support comms | Other | Key evidence |
|---|---|---|---:|---:|---:|---|---|
| R101 | Valid return | FlexFit USB-C Hub 7-in-1 (`P_R101`) | 1 | 1 | 1 | — | Within window (5 days); no inconsistencies |
| R102 | Serial-number mismatch | SoundPeak Wireless Headphones Pro (`P_R102`) | 1 | 2 | 3 | — | Inspection: purchased HP9081 vs received HP9012, additional verification required |
| R103 | Outside return window | SoundPeak Wireless Headphones Pro (`P_R103`) | 1 | 1 | 1 | — | Requested 55 days after delivery, outside the electronics 30-day window |
| R104 | Delivery damage | HomeHive Air Purifier 300 (`P_R104`) | 1 | 1 | 2 | — | Cites the delivery scan note: carton crushed, impact damage |
| R105 | Verified defect | FlexFit USB-C Hub 7-in-1 (`P_R105`) | 1 | 1 | 1 | supplier_defect_report | PD/HDMI defect verified; supplier report SDR-2026-027 |
| R106 | Already refunded | FlexFit USB-C Hub 7-in-1 (`P_R106`) | 1 | 1 | 4 | — | Comms: refund already completed on 2026-03-07; no second refund |
| R107 | Repeated inconsistencies | SoundPeak Wireless Headphones Pro (`P_R107`) | 1 | 1 | 1 | — | Serial HP7710 vs HP7799, missing accessories, reason mismatch |
| R108 | Repairable product | TechNova Ultrabook 14 (`P_R108`) | 1 | 1 | 3 | refurbishment_guideline | Keyboard damage, repairable; laptop repair-and-resell guideline |
| R109 | Missing accessories | FlexFit USB-C Hub 7-in-1 (`P_R109`) | 1 | 1 | 1 | — | Travel pouch and user guide missing |
| R110 | Conflicting inspection reports | HomeHive Air Purifier 300 (`P_R110`) | 2 | 1 | 2 | supplier_defect_report | Two inspection reports disagree (verified Yes vs No) |
| R111 | Wrong product delivered | UrbanWeave Classic Cotton Shirt (`P_R111`) | 1 | 1 | 1 | supplier_defect_report | SKU label does not match the ordered item |
| R112 | Warranty claim | TechNova Ultrabook 14 (`P_R112`) | 1 | 1 | 1 | supplier_defect_report | Verified failure within the 24-month warranty |
| R113 | Missing inspection | FlexFit USB-C Hub 7-in-1 (`P_R113`) | 0 | 1 | 2 | — | No inspection document (evidence gap); comms flag the missing inspection |
| R114 | Incorrect return record | UrbanWeave Classic Cotton Shirt (`P_R114`) | 1 | 1 | 1 | — | Return reason, system note and line item disagree |
| R115 | Unsafe product | HomeHive Air Purifier 300 (`P_R115`) | 1 | 1 | 2 | refurbishment_guideline, supplier_defect_report | Unsafe: scorch/melt at inlet; no resale, recycle or dispose only |

Supplier defect reports also cover scenario returns that are not their primary `return_id`: R102, R103, R104, R106, R107, R108, R113 (listed for information only, as it has no inspection) and R114.

## Non-scenario documents

- Inspections: 15 reports for real non-scenario inspection rows, spread across categories and condition codes: R197, R187, R220, R116, R168, R309, R497, R121, R123, R127, R130, R167, R124, R134, R139.
- Complaints: 34 complaints, chosen round-robin across all nine return reasons: R116, R117, R118, R119, R120, R121, R122, R123, R124, R125, R126, R127, R128, R129, R130, R131, R132, R133, R134, R136, R137, R138, R139, R140, R150, R157, R162, R164, R169, R172, R177, R189, R195, R196.
- Support communications: 4 lifecycle emails (refund processed, pickup scheduled, inspection in progress, under review): R117, R119, R124, R129.
- Supplier reports: the four non-scenario suppliers with the most fault-related returns (damaged, defective, not_functioning), preferring one per category. Return evidence tables come from SQLite.

## Acceptance checklist (computed at generation time)

- [x] At least 140 files under data/unstructured/ — 140 files
- [x] policies/ has 5 files — 5 files
- [x] warranties/ has 10 files — 10 files
- [x] inspections/ has 30 files — 30 files
- [x] complaints/ has 50 files — 50 files
- [x] supplier_reports/ has 10 files — 10 files
- [x] communications/ has 30 files — 30 files
- [x] refurbishment/ has 5 files — 5 files
- [x] Manifest rows = files on disk — 140 rows / 140 files
- [x] Every manifest file_path exists
- [x] No unlisted files on disk
- [x] Manifest filenames are unique
- [x] document_type values match DocumentType enum
- [x] document_type matches folder
- [x] Manifest return_ids exist in SQLite
- [x] Manifest product_ids exist in SQLite
- [x] effective_date is YYYY-MM-DD
- [x] SQLite: R102 purchased HP9081, returned HP9012
- [x] SQLite: R106 has exactly one completed refund
- [x] SQLite: R113 has no inspection row
- [x] SQLite: R110 has two inspection rows that disagree
- [x] Each inspection document maps to a SQLite inspection row — 30 docs; 400 rows in DB
- [x] Manifest: no inspection_report row for R113
- [x] R102 inspection states HP9081 vs HP9012 mismatch
- [x] R110 has two conflicting inspection documents
- [x] R106 communication states refund already completed
- [x] R108 inspection records keyboard damage, repairable
- [x] R108 laptop refurbishment guideline present
- [x] R115 inspection: unsafe / no resale
- [x] R115 safety guideline: no resale, recycle/dispose only
- [x] R103 complaint/communication cites >30 days after delivery
- [x] R104 documents cite the recorded delivery issue
- [x] Electronics policy: 30 days from delivery
- [x] Inspection reports have at least 200 words — min 290 words
- [x] No fraud accusations or prompt-injection phrases
- [x] No real-world brand names
- [x] All email addresses use .invalid domains
- [x] DOCX files have extractable text
- [x] PDF files have extractable text
- [x] PDF text extracts without replacement characters

## SQLite observations relevant to Phase 5

The structured data was rebuilt with a status-driven generator (`backend/app/synthetic/bulk.py`), so the bulk returns (R116+) are internally consistent. The documents follow SQLite throughout. Notes for evaluation:

- **Scenarios are fixed.** R101-R115 are hand-designed and byte-identical to the original dataset; only R107's account history and the explicit open refund requests for R107, R108 and R110 were made explicit.
- **R107 account history:** customer C00107 has earlier returns in SQLite (one with a serial mismatch), so the R107 inspection report cites them as context for the analyst. Each return is still assessed on its own evidence.
- **Refunds follow status.** Only R106 has a completed refund among R101-R115. Completed refunds elsewhere exist only on resolved/closed returns; open refund requests exist only on returns still being worked; returns not yet received have no refund.
- **Incomplete evidence is normal.** About 100 returns are not yet inspected (still requested, in transit, or received and awaiting inspection). R113 is one of the received-but-uninspected returns.
- **Inspection result codes:** `pass` means the defect was verified (or the unit is unsafe); `fail` means the findings do not support the claim; `inconclusive` means no defect could be confirmed or none was claimed; `pending` means testing is in progress. The reports repeat this legend.
- **R114 system note** says the line item is an "accessory SKU", but the order line is a fashion SKU (UrbanWeave shirt). The inspection report quotes the note verbatim and flags it as a data-correction issue.
- **Catalogue:** bulk products use fictional brands with realistic names and prices (for example `Ampere Gaming Laptop 15`); customer descriptions and inspector notes are written from the return reason and inspection facts, not placeholder text.

## Conventions

- File names are lowercase with underscores. Return IDs keep their canonical form, for example `inspection_R102_serial_mismatch.pdf` and `support_R106_refund_already_processed.eml`.
- Email files are RFC 5322 messages (UTF-8, 8-bit bodies) with `Message-ID`, `In-Reply-To`/`References` threading and `X-ShopSphere-Return-ID`/`X-ShopSphere-Order-ID` headers. All addresses use `.invalid` domains.
- PDF and DOCX files have real text layers. Inspection report IDs follow `IR-2026-<inspection_id>`, so every report links to its SQLite `inspections` row.
- Language is neutral. Records that disagree are described as "additional verification required" and never attributed to customer intent.
