# ShopSphere AI Returns & Product Recovery Agent

An **internal AI assistant** for ShopSphere Retail operations teams. It investigates returns using **real shop data and documents**, explains outcomes in plain language, routes **refunds and recovery** through governed workflows, and shows **every tool call** so humans stay in control.

This is a **demonstration environment** with seeded scenarios **R101–R115**, synthetic orders and inspections, and unstructured complaints, policies, and warehouse documents indexed for search.

---

## What is this agent?

The agent is a **tool-driven LangGraph assistant** connected to:

- **Structured data** — returns, orders, inspections, cases, refunds, recovery tasks, and audit history (SQLite).
- **Unstructured knowledge** — complaints, support email, inspection PDFs, and policy text (local files + Chroma RAG).
- **Deterministic engines** — investigation checks, policy snapshots, return timelines, recovery economics, and monitoring alerts.

It does **not** invent return facts. It **queries, searches, investigates, and submits actions** your role is allowed to perform. Sensitive steps (especially **refunds** and many **recovery** writes) go through **submit → supervisor approval → execute**, with guards against mistakes such as **duplicate refunds** (e.g. R106).

You interact through the **React workspace** (`/workspace`): chat, pinned return context, investigation and timeline panels, decision passports, data explorer, a **persona dashboard** (`/workspace/dashboard`), and full **monitoring** for supervisors only.

---

## What can it do?

| Area | What the agent helps with |
|------|---------------------------|
| **Investigate returns** | Eligibility, policy windows, warehouse findings, inconsistency signals (e.g. serial mismatch on R102), and a recommended next step: refund path, escalate, or verify further. |
| **Look up records** | Return status, order and delivery details, inspections, refund status, product info, and customer return history in one conversation. |
| **Search documents** | Complaints, communications, inspection reports, warranty text, and the **policy version that applies** to a given order date. |
| **Build timelines** | Chronological return journeys with sources—useful for handoffs and audits. |
| **Product recovery** | Compare repair, refurbish, resale, supplier return, and disposal by **expected net recovery**, including safety blocks (e.g. R115). |
| **Operational actions** | Open investigation cases, **request** refunds, create recovery/repair tasks, request evidence, assign cases, **approve and execute** when your role allows. |
| **Oversight** | Portfolio-style questions (pending investigations, refunds awaiting approval), monitoring alerts, escalations, and **decision passports** for explainable outcomes. |

Capabilities are exposed to the UI via `GET /api/agent/capabilities`. Role-specific **write** tools are filtered server-side (`backend/app/agents/tool_access.py`).

---

## Why is it needed? What problems does it solve?

Retail returns operations are fragmented: facts live in the OMS, WMS, finance, and inboxes, while policy lives in documents analysts rarely have at hand. That leads to slow investigations, inconsistent decisions, duplicate payouts, poor recovery economics, and weak audit trails.

This agent targets those gaps:

1. **Slow, manual investigation** — Analysts no longer stitch SQL, PDFs, and email by hand; the agent runs structured checks and RAG in one thread and cites what it used.
2. **Policy and evidence drift** — Answers are grounded in **applicable policy** and **document search**, not generic LLM guesses.
3. **Financial and compliance risk** — Refunds and high-impact actions require **approval**; duplicate refund attempts are **blocked** when data says a refund already exists.
4. **Lost product value** — Recovery optimizer compares options so teams favor repair/resell when safe and economical instead of defaulting to write-offs.
5. **Opaque AI** — Tool steps, timelines, investigation panels, and decision passports make automation **inspectable** for supervisors and auditors.
6. **Role confusion** — Five demo personas mirror real handoffs: support explains, analysts investigate and request, warehouse executes recovery, supervisors approve, admins run full pipeline demos.

---

## Who uses the platform? Five roles

Choose your role on the landing page or sign in with the matching demo account. The workspace copy, starter prompts, and **available agent tools** change with your role.

### 1. Returns analyst (`returns_analyst`)

**Role:** Front-line investigator for complex or high-risk returns.

**Typical work:** Deep-dive returns (serial mismatch, conflicting inspections, policy edge cases), reconcile structured data with documents, open **investigation cases**, and **submit refund requests** with the correct amount—never approve or pay out.

**Can do:** Investigate; SQL lookups; document search; recovery **read** (options and recommendations); create cases; request refunds; check action status.

**Cannot do:** Assign cases; approve or execute refunds; create recovery tasks; run monitoring admin APIs.

| Username | Password |
|----------|----------|
| `returns_analyst` | `ShopSphere@Analyst1` |

---

### 2. Customer support agent (`customer_support_agent`)

**Role:** Customer-facing operator who needs **accurate, plain-language** answers fast.

**Typical work:** Explain return status for callbacks, summarize complaints and delivery issues, clarify policy (e.g. return windows on R103), and **request refunds** when eligible—without approving money movement.

**Can do:** Same read/investigate/document paths as other roles; submit refund **requests**.

**Cannot do:** Create or assign investigation cases; approve or execute refunds; create recovery tasks.

| Username | Password |
|----------|----------|
| `support_agent` | `ShopSphere@Support1` |

---

### 3. Warehouse manager (`warehouse_manager`)

**Role:** Inspection and **physical recovery** owner.

**Typical work:** Interpret inspection results and warehouse documents, compare recovery economics (e.g. R108 repair-and-resell), handle **safety/quarantine** cases (R115), and **create repair or recovery tasks** when the recommendation supports them.

**Can do:** Investigate and read recovery analysis; submit recovery/repair-related actions allowed for warehouse roles.

**Cannot do:** Open investigation cases; request or execute refunds; assign cases or approve refund actions.

| Username | Password |
|----------|----------|
| `warehouse_mgr` | `ShopSphere@Warehouse1` |

---

### 4. Returns supervisor (`returns_supervisor`)

**Role:** Queue owner and **approval authority** for money and gated actions.

**Typical work:** Clear refunds awaiting approval, assign overdue investigations, execute approved actions, sync timelines, run monitoring checks, and drive end-to-end cases (e.g. R102 through evidence → case → controlled refund).

**Can do:** Everything analysts and support can do, plus **assign cases**, **approve and execute** refunds and approved actions, recovery task creation, monitoring run/acknowledge, timeline sync APIs.

**Cannot do:** Nothing material is withheld in the demo—supervisors are the operational “full stack” minus break-glass admin-only conveniences.

| Username | Password |
|----------|----------|
| `returns_supervisor` | `ShopSphere@Super1` |

---

### 5. Administrator (`administrator`)

**Role:** **Break-glass** and **demo validation**—same operational powers as supervisors, plus full API access for pipeline tests, health views, and scenario walkthroughs (investigate → case → refund → recovery → timeline).

**Typical work:** Validate golden scenarios, inspect system alerts and pending work, and prove RBAC and audit behavior end-to-end.

| Username | Password |
|----------|----------|
| `admin` | `ShopSphere@Admin1` |

---

### RBAC summary

| Capability | Analyst | Support | Warehouse | Supervisor | Admin |
|------------|:-------:|:-------:|:---------:|:----------:|:-----:|
| Investigate, lookups, documents | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create investigation case | ✓ | — | — | ✓ | ✓ |
| Assign investigation case | — | — | — | ✓ | ✓ |
| Request refund | ✓ | ✓ | — | ✓ | ✓ |
| Approve / execute refund | — | — | — | ✓ | ✓ |
| Recovery recommendation (read) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create recovery / repair task | — | — | ✓ | ✓ | ✓ |
| Approve gated actions | — | — | — | ✓ | ✓ |
| Monitoring / timeline admin APIs | — | — | — | ✓ | ✓ |

For **example prompts per role**, see [`questions.md`](questions.md).

For a **step-by-step refund walkthrough across personas** (use return **R104**), see [`REFUND_PERSONA_FLOW.md`](REFUND_PERSONA_FLOW.md).

For **how the five personas compare** (similarities, differences, and examples), see [`PERSONAS.md`](PERSONAS.md).

---

## Quick start

### Prerequisites

- Python **3.11+**
- Node.js for the frontend
- API keys in `.env` for **Groq** and/or **Gemini** (see [`.env.example`](.env.example))

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
cd ..
copy .env.example .env
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Seed demo users once per database: `python scripts/seed_users.py` (from repo root with venv active).

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) · API docs: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) → pick a **role** → sign in → **Workspace** chat. Pin a return ID (e.g. `R102`) when the question is return-specific.

### Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Pydantic, Alembic |
| Data | SQLite, synthetic + ground-truth scenarios |
| RAG | Local documents, ChromaDB |
| Agent | LangGraph, role-filtered tools |
| UI | React, Vite, Tailwind |

### Tests

```powershell
cd backend
python -m pytest tests/ -q
```

---

## Repository layout

```
backend/     FastAPI app, agent, investigation, services, tests
frontend/    React workspace and role-based landing/sign-in
data/        Synthetic structured data, unstructured docs, ground truth
scripts/     Data load, ingest, migrations, monitoring, eval
questions.md Sample questions and golden prompts by role
```

---

## License

Private demonstration project for **ShopSphere Retail** (fictional). Internal use only.
