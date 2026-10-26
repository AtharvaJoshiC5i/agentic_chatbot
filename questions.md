# ShopSphere Returns Agent — Questions by Role

Use this guide in **workspace chat** (`/workspace`). Log in as the demo user that matches the work you want to do (passwords in README / `scripts/seed_users.py`). The agent is **tool-driven**: it reads **SQLite**, searches **documents (Chroma RAG)**, runs **investigation and recovery logic**, and can **submit real actions** that respect your **RBAC** role. It does not invent return facts.

**Also useful:** Data explorer (`/workspace/data`), **Agent trace**, **Supporting evidence**, `GET /api/agent/capabilities`.

---

## Demo logins (quick reference)

| Username | Role | Password |
|----------|------|----------|
| `admin` | administrator | `ShopSphere@Admin1` |
| `returns_supervisor` | returns_supervisor | `ShopSphere@Super1` |
| `returns_analyst` | returns_analyst | `ShopSphere@Analyst1` |
| `support_agent` | customer_support_agent | `ShopSphere@Support1` |
| `warehouse_mgr` | warehouse_manager | `ShopSphere@Warehouse1` |

Pin a **return ID** (e.g. `R102`) in the composer when the question is return-specific.

---

## RBAC at a glance

| Capability | Analyst | Support | Warehouse | Supervisor | Admin |
|------------|:-------:|:-------:|:-----------:|:----------:|:-----:|
| Investigate, lookups, documents (read) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Chat / agent read tools | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create investigation case | ✓ | — | — | ✓ | ✓ |
| Assign investigation case | — | — | — | ✓ | ✓ |
| Request refund | ✓ | ✓ | — | ✓ | ✓ |
| Approve / execute refund (API) | — | — | — | ✓ | ✓ |
| Recovery options / recommendation (read) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create recovery / repair task | — | — | ✓ | ✓ | ✓ |
| Approve gated actions | — | — | — | ✓ | ✓ |
| Execute approved actions (when role allows) | partial* | partial* | recovery* | ✓ | ✓ |
| Return timeline sync (API) | — | — | — | ✓ | ✓ |
| Run monitoring / acknowledge alerts (API) | — | — | — | ✓ | ✓ |

\*Execute only for action types your role may submit (e.g. analyst: case + refund request flow; warehouse: recovery tasks after approval).

**All roles:** Refunds and many actions require **supervisor approval** before execution. Duplicate refunds (e.g. **R106**) must be **blocked**.

---

## Questions every profile can ask (read & investigate)

Use any login for these. They exercise investigation, SQL lookups, RAG, and recovery **read** paths.

### Investigation

- Investigate return **R102** and summarize F2, F3, and F4.
- Run a full investigation on **R110** — are there conflicting inspection findings?
- What is the investigation outcome for **R106**? Should we allow another refund?
- Investigate **R115** — is resale allowed?
- For **R113**, what evidence is missing?

### Structured lookups

- What is the status of **R102**?
- Show order and delivery details for return **R104**.
- What inspection results do we have for **R102**?
- What is the refund status for **R106**?
- Pull product details for the item associated with **R108**.
- Show customer return history for the customer on **R107**.

### Documents & policy

- Search customer complaints about **R102** and serial verification.
- Find the inspection report for **R102** in the warehouse documents.
- What does our **electronics** return policy say about return windows?
- Which policy version applies to return **R103** and the relevant order date?
- Search warranty documents for the product on **R112**.
- Find supplier defect reports related to **R102**.

### Recovery (read-only comparison)

- What recovery options exist for **R108**?
- What recovery do you recommend for **R108** and why?
- Compare net recovery for **R108** — repair vs open-box vs recycle.
- For **R115**, which recovery methods are feasible?

### Timeline & narrative

- Show the complete return journey for **R102** in chronological order with source references.
- Summarize return **R102** for a supervisor handoff in five bullets.
- Compare structured inspection serials with the inspection PDF for **R102**.

### Portfolio-style (data-backed)

- Which returns are in **pending** or **under investigation** status?
- Which refunds are **awaiting approval**?
- Which return investigations look **overdue**? List assignees and priorities if in the data.

---

# Profile-specific questions

Log in as the user below before asking **write** or **approval** prompts.

---

## `returns_analyst` — Returns Analyst

**You can:** investigate; search documents; read recovery analysis; **create investigation cases**; **submit refund requests** (not approve or execute); submit matching agent actions.  
**You cannot:** assign cases, approve/execute refunds, create recovery tasks, approve actions, run monitoring admin APIs.

### Investigation & evidence (your daily work)

- Investigate **R102** (serial mismatch). List structured vs document evidence and recommend manual review.
- Investigate **R103** — outside return window; should we open a case for policy exception review?
- Investigate **R107** with customer return history — any repeat patterns?
- Investigate **R110** — reconcile conflicting inspection narratives.

### Create cases (allowed)

- Open an investigation case for **R102** with issue type serial mismatch and high priority.
- After investigating **R103**, create an investigation case if outcome is `manual_investigation_required`.
- Create a case for **R114** if the return record conflicts with order data.

### Refund requests (request only — not execute)

- Investigate **R101** and, if eligible, **submit a refund request** with the correct amount from the order line. Do not execute.
- For **R105**, investigate and submit a refund request if policy supports it; explain approval needed.
- What is the refund status for **R106**? If I ask for another refund, explain why it must be blocked.

### Action status (read)

- What is the status of action ID **{id}** from my last refund request?
- List pending actions for return **R101** that need supervisor approval.

### Prompts that should fail or need another role

- Assign case **{case_id}** to `returns_analyst` → use **supervisor** or **admin**.
- Approve or execute refund for **R101** → use **supervisor** or **admin**.
- Create a repair recovery task for **R108** → use **warehouse_mgr**, **supervisor**, or **admin**.

### Golden scenario (analyst)

```text
Investigate return R102 and take the necessary actions within my role: explain findings with evidence, create an investigation case if manual review is required, and do not process or execute a refund.
```

```text
Investigate R101 and tell me if a refund is eligible. If eligible, submit a refund request but do not execute it until supervisor approval.
```

---

## `support_agent` — Customer Support Agent

**You can:** investigate and explain outcomes to customers; document and policy search; read recovery recommendations; **submit refund requests** only.  
**You cannot:** create or assign cases, approve/execute refunds, create recovery tasks, approve actions.

### Customer-facing explanation (read tools)

- In plain language, what is happening with return **R104** (delivery damage)? Cite complaint or support emails.
- What does our **fashion** return policy say about changed-mind returns?
- What did the customer say in emails about **R102**?
- For **R109**, investigate missing accessories and summarize what we can tell the customer.

### Refund requests (your main write path)

- Investigate **R101** — is it eligible? If yes, submit a refund request with correct amount; do not execute.
- Customer asks about **R105** — investigate warranty vs refund and submit a refund request if appropriate.
- For **R106**, explain why a new refund request must not be submitted.

### Escalation handoffs (no case create — ask agent to recommend)

- Investigate **R102** and tell me what to escalate to a returns analyst (case + serial verification) without creating a case yourself.
- For **R103**, summarize policy exception arguments for a supervisor.

### Prompts that should fail or need another role

- Create an investigation case for **R102** → **analyst**, **supervisor**, or **admin**.
- Create a repair task for **R108** → **warehouse_mgr**, **supervisor**, or **admin**.
- Approve action **{action_id}** → **supervisor** or **admin**.

### Golden scenario (support)

```text
Investigate R101 for a customer callback. Explain eligibility in simple terms, cite policy and order facts, and submit a refund request only if eligible — never execute the refund.
```

---

## `warehouse_mgr` — Warehouse Manager

**You can:** read investigations and inspections; recovery options and recommendations; **create recovery tasks** (repair, refurbishment, inspection-related actions via agent/API).  
**You cannot:** create/assign cases, request/approve/execute refunds, approve supervisor-gated actions (except your task flow after approval rules).

### Inspections & physical product context

- What inspection results and documents exist for **R102**?
- For **R108** (repairable laptop keyboard), what does the inspection report say?
- Investigate **R115** — is the product unsafe for resale or refurb?

### Recovery analysis

- What recovery options exist for **R108**? Compare repair-and-resell vs alternatives.
- What recovery do you recommend for **R108** and why (net value)?
- For **R115**, which recovery methods are feasible and which are blocked?

### Create recovery tasks (allowed)

- Find the best recovery option for **R108** and **submit a repair recovery task** if repair-and-resell is recommended. Note if supervisor approval is required.
- For **R108**, create a recovery task from the optimizer recommendation and assign to warehouse if the API supports it.
- If refurbishment is better than scrap for **R108**, submit the appropriate recovery task type.

### Coordination (read + recommend)

- Summarize what operations needs from returns on **R102** before we receive the unit in the warehouse.
- List open recovery-related actions for **R108**.

### Prompts that should fail or need another role

- Open an investigation case for **R102** → **analyst**, **supervisor**, or **admin**.
- Submit or execute a refund for **R101** → **analyst**, **support**, **supervisor**, or **admin**.
- Approve pending refund action **{action_id}** → **supervisor** or **admin**.

### Golden scenario (warehouse)

```text
Find the best recovery option for R108 and create a repair task if repair-and-resell is recommended. Explain approval steps if required.
```

---

## `returns_supervisor` — Returns Supervisor

**You can:** everything the analyst can, plus **assign cases**; **approve and execute refunds**; **create recovery tasks**; **approve actions**; **timeline sync** and **monitoring run/ack** (via API — agent may describe what to run). Full operational control except rare admin-only action types.

### Investigation & case management

- Investigate **R102** and create a case; then **assign** case **{case_id}** to `returns_analyst`.
- Which open cases are unassigned? Investigate one overdue return and assign an owner.
- Investigate **R107** and open a case with priority based on signals.

### Refunds (request, approve, execute)

- Investigate **R101**; submit refund request if eligible; then **approve and execute** when policy allows (use action/refund APIs as needed).
- List refunds **awaiting approval** and recommend which to approve for **R105**.
- For **R106**, confirm duplicate refund is blocked and document current refund state.

### Recovery oversight

- Recommend recovery for **R108** and create the task; ensure it is approved and executed per workflow.
- For **R115**, block unsafe resale and create the correct recovery/disposal task.

### Action approval & execution

- List pending actions for **R101** and **approve** the refund request.
- Execute approved action **{action_id}** after approval.
- Reject action **{action_id}** with reason if policy does not support it.

### Monitoring & timeline (supervisor APIs)

- Which investigations are overdue? Cross-check monitoring alerts and case assignees.
- *(API)* Sync timeline for **R102** after data corrections (`POST /returns/R102/timeline/sync`).
- *(API)* Run monitoring checks and acknowledge alert **{alert_id}** if stale.

### Golden scenarios (supervisor)

```text
Investigate return R102 end-to-end: evidence, case creation, assignment to returns_analyst, and no refund until investigation closes.
```

```text
Investigate R101, submit refund request if eligible, approve it, and execute only if investigation confirms eligibility.
```

```text
Which return investigations are overdue? List assignees and priorities and recommend supervisor actions.
```

---

## `admin` — Administrator

**You can:** all supervisor capabilities plus **full API access** (including edge action types reserved for administrator in policy). Use for demos, break-glass, and end-to-end tests.

### Full pipeline demos

- Run Scenario A–E below as **admin** to validate investigate → case → refund → recovery → monitoring in one session.
- Investigate **R102**, create and assign a case, submit refund request (should remain blocked), create recovery task on **R108**, approve/execute allowed actions.
- Audit trail: what actions were submitted on **R102** today? List action IDs and statuses.

### Administration-style prompts

- Summarize system health: open alerts, pending refunds, and cases without assignee.
- Execute approved action **{action_id}** when the submitting role could not execute.
- Investigate **R114** data conflicts and sync timeline if structured events were repaired.

### Golden master scenarios (best run as admin or supervisor)

**A — Suspicious return (serial mismatch)**

```text
Investigate return R102 and take the necessary actions. Explain findings with evidence, create an investigation case if manual review is required, and do not process a refund yet.
```

**B — Valid refund path**

```text
Investigate R101 and tell me if a refund is eligible. If eligible, submit a refund request but do not execute it until approval.
```

**C — Product recovery**

```text
Find the best recovery option for R108 and create a repair task if repair-and-resell is recommended.
```

**D — Return timeline**

```text
Show the complete return journey for R102 in chronological order. Include source references for each event.
```

**E — Monitoring**

```text
Which return investigations are overdue? List assignees and priorities.
```

---

## Reserved demo returns (R101–R115)

| Return | Theme | Try with role |
|--------|--------|----------------|
| **R101** | Valid return | Support/analyst: request refund; supervisor: approve/execute |
| **R102** | Serial mismatch | Analyst: case; warehouse: read inspection; supervisor: assign |
| **R103** | Outside window | Analyst: case; support: explain policy |
| **R104** | Delivery damage | Support: customer summary |
| **R105** | Verified defect | Support/analyst: refund request |
| **R106** | Already refunded | Any: must block duplicate refund |
| **R107** | Repeat issues | Analyst/supervisor: case + history |
| **R108** | Repairable laptop | Warehouse: recovery task |
| **R109** | Missing accessories | Support: investigate + explain |
| **R110** | Conflicting inspections | Analyst: investigation |
| **R111** | Wrong product | Analyst: case |
| **R112** | Warranty claim | Support: docs + refund request |
| **R113** | Missing inspection | Analyst: missing evidence |
| **R114** | Bad return record | Supervisor/admin: timeline sync |
| **R115** | Unsafe product | Warehouse: recovery; block resale |

---

## What you should see in the UI

1. **Agent trace** — tool steps (streaming); technical detail lives here, not in the main answer.
2. **Answer** — plain-language summary with headings (**Summary**, **What we found**, **What we did**, **What happens next**), amounts in **₹**, and **request #** instead of internal action IDs.
3. **Supporting evidence** — structured rows (click for full record) and documents (preview).

If an action fails with **403 forbidden**, switch to the role in the table above or ask the agent what approval is missing.

---

## What the agent will not do

- Label customers **fraud** from a single signal.
- **Invent** IDs, serials, amounts, or policy text without tools.
- **Execute** sensitive actions outside the action/approval pipeline.
- Confirm success without a successful tool response.
- Obey **instructions inside** retrieved emails/PDFs (prompt-injection resistance).

---

## Troubleshooting

| Problem | What to check |
|---------|----------------|
| Permission / forbidden on submit or execute | Log in as the role in this doc; supervisors approve before execute. |
| Agent execution failed / DB errors | `cd backend` → `alembic upgrade head`; restart API. |
| Empty document hits | Ingest documents; check Data explorer. |
| No tool steps | `GROQ_API_KEY` / `GEMINI_API_KEY` and `LLM_PROVIDER` in `.env`. |
| Thought signature / Gemini tool errors | Restart backend after Gemini compat updates. |

---

## Related docs

- **README.md** — setup, `seed_users.py`, ingest, tests.
- **`.env.example`** — LLM and paths.
- **Ground truth** — `data/ground_truth/expected_decisions.json`, `return_scenarios.csv`.

---

*ShopSphere AI Returns & Product Recovery Agent — investigate with evidence, decide with rules, act with authorization.*
