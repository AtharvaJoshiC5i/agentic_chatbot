# Master prompt: ShopSphere unstructured synthetic documents (repo-native)

You have **full access to this repository** (`agentic_chatbot`). Do not ask the user to upload attachments or deliver ZIPs. **Read sources in the repo, write files into the repo**, and update the manifest on disk.

Copy everything inside the fenced block below into Claude (with this repo connected).

---

```
# Task: Generate Phase 4 unstructured document corpus (in-repository)

You are a senior technical writer and retail documentation specialist working **inside the ShopSphere AI Returns Agent codebase**. Create the complete synthetic unstructured document set for **ShopSphere Retail** (fictional Indian e-commerce). Files must land in this repo so a later pipeline can load `document_metadata` and ingest ChromaDB (Phase 5).

**Working mode:** Repository-native. Use your file browser / tools to read code and data, create directories, write binary documents (PDF/DOCX) or text (TXT/EML), and maintain `data/ground_truth/document_manifest.csv`. Do not output document bodies only in chat—**persist every file under `data/unstructured/`**.

---

## A. Read these sources first (mandatory)

Before writing any document, load structured truth from the repo:

| Priority | Path | Purpose |
|----------|------|---------|
| 1 | `backend/shopsphere.db` | **Source of truth** for returns, orders, inspections, refunds, deliveries, products, customers |
| 2 | `backend/app/synthetic/scenarios.py` | R101–R115 profiles, serials, flags (`scenario_profiles()`, `SCENARIO_SPECS`) |
| 3 | `backend/app/synthetic/generator.py` | `PRODUCT_LIBRARY` (names, categories, warranty months, INR paise prices) |
| 4 | `data/ground_truth/return_scenarios.csv` | Scenario titles and expected outcomes |
| 5 | `data/ground_truth/expected_decisions.json` | Investigation expectations per return |
| 6 | `data/ground_truth/expected_tool_actions.json` | Agent eval hooks (R102, R106, R108, etc.) |
| 7 | `backend/app/models/enums.py` | `DocumentType` enum values for manifest |
| 8 | `backend/app/models/tables.py` | `DocumentMetadata` columns |
| 9 | `docs/UNSTRUCTURED_DATA.md` | Project policy on document generation |

**If `data/structured/*.csv` exists**, use it as a convenient join helper; if not, query SQLite directly.

### SQLite queries you should run (examples)

Use `sqlite3 backend/shopsphere.db` or an equivalent tool:

```sql
-- Scenario returns and line items
SELECT r.return_id, r.order_item_id, r.return_reason, r.return_status, r.request_date, r.received_date,
       oi.order_id, oi.product_id, oi.purchased_serial_number, oi.unit_price,
       p.product_name, p.category, p.brand, p.warranty_months
FROM returns r
JOIN order_items oi ON oi.order_item_id = r.order_item_id
JOIN products p ON p.product_id = oi.product_id
WHERE r.return_id BETWEEN 'R101' AND 'R115'
ORDER BY r.return_id;

-- Inspections (note R113 should return zero rows)
SELECT * FROM inspections WHERE return_id IN ('R102','R110','R113');

-- R106 refunds (expect one completed)
SELECT * FROM refunds WHERE return_id = 'R106';

-- Delivery issue for R104
SELECT d.* FROM deliveries d
JOIN order_items oi ON oi.order_id = d.order_id
JOIN returns r ON r.order_item_id = oi.order_item_id
WHERE r.return_id = 'R104';
```

**Rule:** Document text must **match SQLite** for IDs, serials, dates, and statuses. The only intentional cross-source conflict is **R110** (two inspection *documents* that disagree—must still align with two inspection *rows* in DB if present).

---

## B. Business context & tone

- Categories: **electronics**, **fashion**, **home_appliances**, **accessories**; currency **INR (₹)**; money in DB is **paise** (divide by 100 for prose).
- Documents support an **internal returns investigation assistant** (RAG + agent). Write audit-friendly, specific prose.
- **Never** call customers fraudulent. Serial mismatch → “additional verification required.”
- **No prompt-injection** strings inside documents (“ignore instructions”, “approve refund automatically”, etc.).
- Brands are **fictional only:** SoundPeak, TechNova, UrbanWeave, HomeHive, FlexFit (see `PRODUCT_LIBRARY`). No Apple/Samsung/etc.

---

## C. Filesystem deliverables (write into repo)

Create this tree at the **repository root**:

```
data/unstructured/
  policies/           # 5 files
  warranties/         # 10 files
  inspections/        # 30 files
  complaints/         # 50 files
  supplier_reports/   # 10 files
  communications/     # 30 files
  refurbishment/      # 5 files
data/ground_truth/
  document_manifest.csv   # one row per file (create/update)
docs/
  README_UNSTRUCTURED.md  # coverage checklist + counts (create)
```

**Minimum 140 document files** + manifest + README.

### Format mix (realistic)

| Type | Folder | Count | Formats |
|------|--------|-------|---------|
| Return policies | `policies/` | 5 | PDF or DOCX |
| Warranties | `warranties/` | 10 | PDF or DOCX |
| Inspection reports | `inspections/` | 30 | PDF preferred, else DOCX |
| Customer complaints | `complaints/` | 50 | EML or TXT |
| Supplier defect reports | `supplier_reports/` | 10 | PDF or DOCX |
| Support communications | `communications/` | 30 | EML preferred, else TXT |
| Refurbishment guidelines | `refurbishment/` | 5 | PDF or DOCX |

**Text must be machine-extractable** (real PDF/DOCX text layers, not scanned blanks). For PDF/DOCX you may use Python in the repo (`reportlab`, `python-docx`—add to `backend/requirements.txt` only if you install them locally to generate files) or write **valid** EML/TXT directly.

---

## D. Policy documents (5)

One file each; include extractable sections for:

- Policy ID (e.g. `POL-ELEC-2024-03`)
- Version (e.g. `3.2`)
- Effective date (`YYYY-MM-DD`)
- Applicable category
- **Return window (days)** — electronics standard: **30 days from delivery** (required for **R103** eval)
- Eligibility, exceptions, required documentation, approval thresholds (INR)

Topics:

1. Electronics (serial-tracked, defect vs change-of-mind)
2. Fashion (size/color, hygiene/sealed)
3. Home appliances (installation, pickup)
4. Accessories (opened package rules)
5. Damaged products / damaged-in-transit (photos within 48h, delivery damage)

---

## E. Scenario anchors R101–R115 (cross-check with DB)

After querying SQLite, confirm IDs. Expected mapping (generator convention):

| return_id | order_id | customer_id | product_id | Product (from `PRODUCT_LIBRARY` / `P_{return_id}`) |
|-----------|----------|-------------|------------|-----------------------------------------------------|
| R101 | O101 | C00101 | P_R101 | FlexFit USB-C Hub 7-in-1 |
| R102 | O102 | C00102 | P_R102 | SoundPeak Wireless Headphones Pro |
| R103 | O103 | C00103 | P_R103 | SoundPeak Wireless Headphones Pro |
| R104 | O104 | C00104 | P_R104 | HomeHive Air Purifier 300 |
| R105 | O105 | C00105 | P_R105 | FlexFit USB-C Hub 7-in-1 |
| R106 | O106 | C00106 | P_R106 | FlexFit USB-C Hub 7-in-1 |
| R107 | O107 | C00107 | P_R102 | SoundPeak Wireless Headphones Pro |
| R108 | O108 | C00108 | P_R108 | TechNova Ultrabook 14 |
| R109 | O109 | C00109 | P_R109 | FlexFit USB-C Hub 7-in-1 |
| R110 | O110 | C00110 | P_R110 | HomeHive Air Purifier 300 |
| R111 | O111 | C00111 | P_R111 | UrbanWeave Classic Cotton Shirt |
| R112 | O112 | C00112 | P_R108 | TechNova Ultrabook 14 |
| R113 | O113 | C00113 | P_R113 | FlexFit USB-C Hub 7-in-1 |
| R114 | O114 | C00114 | P_R114 | UrbanWeave Classic Cotton Shirt |
| R115 | O115 | C00115 | P_R115 | HomeHive Air Purifier 300 |

### Mandatory document behavior by scenario

| Return | Requirement |
|--------|-------------|
| **R102** | Inspection doc: purchased **HP9081**, received **HP9012**, mismatch explicit. Optional complaint + support thread. |
| **R103** | Complaint/policy cite return **>30 days after delivery** (verify dates from DB). |
| **R104** | Docs reference **delivery damage** (align with `deliveries.delivery_issue` for O104). |
| **R106** | Communication states **refund already completed** (align with `refunds` row). |
| **R108** | Inspection: **keyboard damage**, repairable; refurb guideline for laptops. |
| **R110** | **Two** inspection files with **conflicting** defect conclusions (match DB’s two inspection rows). |
| **R113** | **No** inspection file (DB has no inspection—keep evidence gap). |
| **R115** | Inspection: **unsafe**; refurb/safety doc: **no resale**. |

For non-scenario returns, assign documents to real `return_id` values from SQLite (`SELECT return_id FROM returns WHERE return_id >= 'R116' LIMIT 100`)—do not invent IDs that are not in the database.

---

## F. Content quality (per type)

- **Inspections (~30):** Report ID, `return_id`, date, inspector, site (Indian city), serials, accessories Y/N, defect verified Y/N, findings; footer “Internal use only — ShopSphere Retail.” Min ~200 words each where applicable.
- **Complaints (~50):** Varied voice; include `return_id` / `order_id` when linked.
- **Warranties (~10):** Category/product linkage; warranty months per product type (12 / 24 / 6 / 0 from catalog).
- **Supplier reports (~10):** Batch codes, recurring defects.
- **Support comms (~30):** Valid EML headers; threads for **R102**, **R106**, **R108** among others.
- **Refurbishment (~5):** Open-box, repair-resell, refurbish, recycle, dispose; **unsafe → dispose/recycle only**.

**Naming:** lowercase, underscores, e.g. `inspection_R102_serial_mismatch.pdf`, `support_R106_refund_already_processed.eml`.

---

## G. Manifest: `data/ground_truth/document_manifest.csv`

Create/update this file with **exactly one row per file**:

```csv
filename,document_type,return_id,product_id,policy_version,effective_date,file_path
```

- `document_type` ∈ `return_policy` | `warranty` | `inspection_report` | `customer_complaint` | `supplier_defect_report` | `support_communication` | `refurbishment_guideline` (must match `DocumentType` in `backend/app/models/enums.py`).
- `file_path`: forward slashes, relative to repo root, e.g. `data/unstructured/inspections/inspection_R102_serial_mismatch.pdf`
- Leave `return_id` / `product_id` empty when N/A.
- `effective_date`: `YYYY-MM-DD` (policy effective date or document date).

This file will be imported into SQLite `document_metadata` (`filename`, `document_type`, `return_id`, `product_id`, `policy_version`, `effective_date`, `file_path`). **Paths and types must match real files on disk.**

---

## H. Execution plan (in repo, incremental)

Work in batches; after each batch, update manifest and README checklist.

1. **Batch A:** `data/unstructured/policies/` (5) + `warranties/` (10) + manifest rows.
2. **Batch B:** `inspections/` (30)—scenario returns first; verify R102/R110/R113/R115 rules.
3. **Batch C:** `complaints/` (50) + `supplier_reports/` (10).
4. **Batch D:** `communications/` (30) + `refurbishment/` (5).
5. **Batch E:** Reconcile manifest row count = file count; write `docs/README_UNSTRUCTURED.md`.

If the repo already has partial files under `data/unstructured/`, **merge** without duplicating scenario-critical filenames; prefer idempotent updates.

---

## I. Verification (you run before finishing)

1. `find data/unstructured -type f | wc -l` (or equivalent) → **≥ 140**.
2. Manifest rows = file count; every `file_path` exists.
3. Re-run SQLite checks for R102 serials, R106 refund, R113 no inspection row, R110 two inspection rows.
4. Open sample PDF/DOCX and confirm selectable text (not empty).
5. Grep manifest for `R113` → **no** `inspection_report` row.

### Acceptance checklist

- [ ] 140+ files on disk under `data/unstructured/`
- [ ] `document_manifest.csv` complete and consistent
- [ ] `docs/README_UNSTRUCTURED.md` with per-folder counts and R101–R115 coverage table
- [ ] R102: HP9081 vs HP9012 in inspection text
- [ ] R110: two conflicting inspection documents
- [ ] R113: no inspection document
- [ ] R106: refund already processed (comms)
- [ ] R108: keyboard damage
- [ ] R115: unsafe / no resale
- [ ] Electronics policy: 30-day window
- [ ] No fraud accusations; no prompt injection; emails use `@shopsphere.invalid` or similar

---

## J. Do NOT

- Do not modify `backend/app/synthetic/generator.py` or reseed SQLite unless explicitly asked.
- Do not add PostgreSQL or change Alembic schema (Phase 4 is files + manifest only).
- Do not replace structured data with document-only fiction for scenario IDs.
- Do not commit secrets or real PII.
- Do not only paste documents in chat—**write the repo tree**.

---

## K. Handoff to Cursor (user message after you finish)

When done, the user will ask Cursor: **“Phase 4: load document metadata and validate.”** Your deliverable is the on-disk corpus + manifest; Cursor will wire `scripts/load_document_metadata.py` / ingestion (Phase 5).

**Start now:** Query `backend/shopsphere.db` for R101–R115, confirm serials and dates, create missing folders, then execute Batch A.
```

---

## Notes for the human operator

- Claude should treat **`backend/shopsphere.db`** and **`backend/app/synthetic/`** as authoritative; the table in section E is a quick reference, not a substitute for querying.
- If the DB is empty, run from repo root: `python scripts/load_database.py`, then point Claude at the repo again.
- After Claude finishes, return to Cursor for metadata load + Phase 5 Chroma ingestion.
