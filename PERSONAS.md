# The five ShopSphere personas — who they are and how they differ

Everyone uses the **same workspace**: chat, agent trace, supporting evidence, and (when you pin a return) the context panel. What changes is **what you are allowed to do** and **how the agent talks to you**.

Think of it like one hospital system: nurses, doctors, and billing all see the same patient chart, but only some roles can prescribe, approve surgery, or release payment.

---

## What all five personas have in common

| Shared experience | What it means for you |
|-------------------|------------------------|
| **Sign in** | Demo account per role (see table at the end). |
| **Investigate returns** | Ask about R101–R115; the agent reads SQLite + documents. |
| **Look up facts** | Orders, inspections, policy, complaints, recovery *analysis* (read-only). |
| **Visible tools** | Every tool call appears in **Agent trace** and **Supporting evidence**. |
| **Same data** | Handoffs happen via **return ID**, cases, and actions in the database—not shared chat threads. |

No persona can “make up” return facts. If the data is missing, the agent should say so.

---

## One story, five viewpoints (example)

**Situation:** Return **R102** — possible serial mismatch; refund must not be rushed.

| Persona | What they do in this story |
|---------|----------------------------|
| **Customer support** | Explains to the customer that verification is in progress; does **not** open a formal case. |
| **Returns analyst** | Runs investigation, opens **investigation case**, requests evidence; submits **refund request** only if policy allows (does not pay out). |
| **Warehouse manager** | Summarizes **inspection PDFs** and physical findings; may create a **repair/recovery** task later—not refunds. |
| **Returns supervisor** | Assigns the case, **approves** refund actions, **executes payout** when appropriate, clears the queue. |
| **Administrator** | Can run the full demo path (same powers as supervisor for operations). |

Same return, different jobs—like a relay race, not five separate apps.

---

## 1. Customer support agent

**Login:** `support_agent` · **Password:** `ShopSphere@Support1`

**Who they are:** Frontline staff on calls and email. They need **clear, customer-safe language** fast.

**Superpower:** Investigate + explain + **submit a refund request** when eligible.

**Cannot:** Open investigation cases, approve refunds, execute payout, or create warehouse recovery tasks.

**Example prompt (pin R101):**

```text
Explain return R101 in plain language for a customer callback. Submit a refund request only if eligible — do not execute the refund.
```

**Example prompt (pin R106 — guardrail):**

```text
Can we refund R106 again? Explain why we must not submit another refund.
```

**Mindset:** “I help the customer understand; I **ask** for money back, I don’t **send** it.”

---

## 2. Returns analyst

**Login:** `returns_analyst` · **Password:** `ShopSphere@Analyst1`

**Who they are:** Investigators for tricky or risky returns (mismatch, policy edge cases, conflicting docs).

**Superpower:** Everything support can do for reads **plus** **create investigation cases** and **submit refund requests** with evidence.

**Cannot:** Assign cases to people, approve/execute refunds, or create recovery tasks.

**Example prompt (pin R102):**

```text
Investigate R102 with evidence. Create an investigation case if manual review is required. Do not execute a refund.
```

**Example prompt (pin R110):**

```text
Investigate R110 and explain any conflicting inspection findings.
```

**Mindset:** “I build the file and route decisions; **supervisor** signs the check.”

---

## 3. Warehouse manager

**Login:** `warehouse_mgr` · **Password:** `ShopSphere@Warehouse1`

**Who they are:** People who touch the **physical product**—inspections, repair, refurb, quarantine, disposal.

**Superpower:** Read investigations and **recovery recommendations**; **create recovery/repair tasks** (often after supervisor approval on the action).

**Cannot:** Request or approve refunds, open investigation cases, or assign analysts.

**Example prompt (pin R108):**

```text
What recovery do you recommend for R108? Create a repair recovery task if repair-and-resell is recommended.
```

**Example prompt (pin R115 — safety):**

```text
Is R115 safe to refurbish or resell? Recommend disposal or recycle if needed.
```

**Mindset:** “I protect **inventory value and safety**; finance handles **customer refunds**.”

---

## 4. Returns supervisor

**Login:** `returns_supervisor` · **Password:** `ShopSphere@Super1`

**Who they are:** Queue owner and **approval authority** for money and gated actions.

**Superpower:** Analyst capabilities **plus** assign cases, **approve** action requests, **execute payout** on refunds, recovery task oversight, monitoring/timeline admin APIs.

**Cannot:** Nothing important is withheld in the demo—they are the operational “decision desk.”

**Example prompt (pin R104 after support submitted a request):**

```text
List pending actions for R104. Approve the refund request, execute payout, and confirm get_refund_status shows completed.
```

**Example prompt (portfolio):**

```text
Which refunds are awaiting approval? Summarize what I should approve today.
```

**Mindset:** “I turn **requests** into **completed** outcomes and keep the backlog honest.”

---

## 5. Administrator

**Login:** `admin` · **Password:** `ShopSphere@Admin1`

**Who they are:** Break-glass and **demo validation**—train the team, run end-to-end scenarios, check system health.

**Superpower:** Same operational powers as **supervisor** for refunds, cases, recovery, and actions; full API access for pipeline tests.

**Cannot:** (In the story of the product, admin is not a “customer”—still an internal user with maximum internal permissions.)

**Example prompt (pin R102 — golden scenario):**

```text
Investigate return R102 end-to-end: evidence, case if needed, assignment, and no refund until investigation is complete.
```

**Example prompt (health snapshot):**

```text
Summarize system health: open alerts, pending refunds, and cases without assignee.
```

**Mindset:** “I prove the **whole system** works; in production I’d use this role sparingly.”

---

## Side-by-side: what only one role can do

| Capability | Support | Analyst | Warehouse | Supervisor | Admin |
|------------|:-------:|:-------:|:---------:|:----------:|:-----:|
| Customer-style explanations | **Best fit** | ✓ | ✓ | ✓ | ✓ |
| Create investigation case | — | **✓** | — | ✓ | ✓ |
| Submit refund **request** | ✓ | ✓ | — | ✓ | ✓ |
| Approve + **execute payout** | — | — | — | **✓** | ✓ |
| Create recovery / repair task | — | — | **✓** | ✓ | ✓ |
| Assign cases | — | — | — | **✓** | ✓ |
| Monitoring / timeline admin | — | — | — | **✓** | ✓ |

---

## Similarities that confuse people (and the truth)

| Confusion | Reality |
|-----------|---------|
| “Support and analyst feel the same.” | Both can **request** refunds; only **analyst** opens **cases** for deep investigations. |
| “Supervisor and admin are identical.” | In this demo, **yes for day-to-day refunds**; admin is for **full-pipeline and health** demos. |
| “Warehouse can fix refunds by repairing the item.” | Recovery **does not** replace a refund; different ledger, different actions. |
| “If the agent says ‘executed,’ the customer was paid.” | Check **Refund ledger → completed**. See [REFUND_PERSONA_FLOW.md](REFUND_PERSONA_FLOW.md). |

---

## How to pick a persona when practicing

| Your goal | Sign in as |
|-----------|------------|
| Practice customer calls | `support_agent` |
| Practice investigations and cases | `returns_analyst` |
| Practice repair / recovery economics | `warehouse_mgr` |
| Practice approvals and payout | `returns_supervisor` |
| Run one-shot end-to-end demo | `admin` |

---

## Quick login reference

| Username | Role | Password |
|----------|------|----------|
| `support_agent` | Customer support | `ShopSphere@Support1` |
| `returns_analyst` | Returns analyst | `ShopSphere@Analyst1` |
| `warehouse_mgr` | Warehouse manager | `ShopSphere@Warehouse1` |
| `returns_supervisor` | Returns supervisor | `ShopSphere@Super1` |
| `admin` | Administrator | `ShopSphere@Admin1` |

More prompts per role: [questions.md](questions.md)  
Refund handoff across roles: [REFUND_PERSONA_FLOW.md](REFUND_PERSONA_FLOW.md)  
Platform overview: [README.md](README.md)
