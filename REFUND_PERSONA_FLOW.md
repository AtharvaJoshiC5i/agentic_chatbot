# How personas resolve a refund end-to-end

This guide walks you through **who does what**, **how information moves between roles**, and **exact prompts to try** in the ShopSphere demo workspace.

**Important:** Refunds use **two layers** (now aligned):

1. **Action requests** — analyst/operations submits; supervisor **approves once** (≤ ₹50,000 auto-completes payout).
2. **Refund ledger** — row is created when the request is submitted; only **`completed`** means the customer was paid.

Do not tell the customer the refund was sent until the **Refund ledger** shows **completed**.

---

## Demo logins

| Persona | Username | Password |
|---------|----------|----------|
| Customer support | `support_agent` | `ShopSphere@Support1` |
| Returns analyst | `returns_analyst` | `ShopSphere@Analyst1` |
| Returns supervisor | `returns_supervisor` | `ShopSphere@Super1` |
| Administrator | `admin` | `ShopSphere@Admin1` |

Use a **fresh return** for a clean walkthrough. **R101 is often already polluted** from earlier demos. Prefer **R104** (delivery damage) or **R109** (missing accessories).

---

## Recommended practice return: **R104**

Pin **`R104`** in the workspace composer for every step.

---

### Step 1 — Customer support (`support_agent`)

Sign in → Workspace → pin **R104**.

```text
Investigate R104 for a customer callback. Explain eligibility in plain language using order and policy facts. If eligible, submit a refund request with the correct amount. Do not execute the refund.
```

**Check:**

- Agent trace shows investigation + `submit_refund_request`.
- **Actions** card: new request with an **action #** (note the number).
- **Refund ledger**: still **no completed payout** (expected until supervisor executes).

---

### Step 2 — Returns supervisor (`returns_supervisor`)

Sign out → sign in as `returns_supervisor` → pin **R104**.

```text
List pending actions for return R104. Approve the refund request and confirm get_refund_status shows completed.
```

Or use the UI: **Approve** on the action card — payout completes automatically for amounts ≤ ₹50,000.

**Check:**

- **Actions**: request refund → **Succeeded**.
- **Refund ledger**: one row, status **completed** (green / “Payout completed”).
- Agent reply should **not** say “awaiting approval” if ledger is completed.

---

### Step 3 — Support again (`support_agent`)

Pin **R104**:

```text
Explain the current refund status for R104 in plain language for a customer email. Use get_refund_status — only say money was sent if status is completed.
```

**Check:** Email tone matches **completed** payout (or honestly says still in review if not).

---

## Rules you will see in the product

| Rule | Behavior |
|------|----------|
| Second refund while one is open | **Blocked** (pending action or open refund row). |
| R106 | **Duplicate completed refund** blocked (use for guardrail demo). |
| Support / analyst | May **submit** refund requests only. |
| Supervisor / admin | **Approve** actions + **Execute payout** (completes ledger). |

---

## Handoff without shared chat

Each login has its own chat history. Handoff is via **shared data**:

- **Return ID** (e.g. R104)
- **Action #** from the support message or Actions panel
- **Refund #** from Refund ledger after execute

---

## Single-session shortcut (admin only)

Sign in as `admin`, pin **R104**:

```text
Investigate R104 for refund eligibility. If eligible, submit a refund request, approve it, execute payout, and confirm get_refund_status shows completed.
```

Use for smoke tests only — production should keep support and supervisor separate.

---

## More scenarios

- [questions.md](questions.md) — prompts by role  
- [README.md](README.md) — platform overview  
