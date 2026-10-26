# Unstructured document generation (Phase 4)

**Policy:** Unstructured files are generated into `data/unstructured/` using the repo-native Claude prompt:

→ **[CLAUDE_SYNTHETIC_DOCUMENTS_PROMPT.md](CLAUDE_SYNTHETIC_DOCUMENTS_PROMPT.md)**

Claude is expected to have **full repository access** (read `shopsphere.db`, synthetic code, ground truth; write files and `data/ground_truth/document_manifest.csv` in place).

**Metadata + RAG (automated):**

```powershell
python scripts/load_document_metadata.py
python scripts/ingest_documents.py
```

See README Phase 5 section for details.

**Generated corpus:** see [README_UNSTRUCTURED.md](README_UNSTRUCTURED.md) for per-folder counts, R101–R115 coverage, verification results, and the regeneration command (`scripts/generate_unstructured_documents.py`).
