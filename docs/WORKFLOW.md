# Persona workflow

Three personas share one database. Every step writes its result to the database, and the next persona reads it from
their own queue (`GET /api/dashboard/workspace`) or the agent's live workflow snapshot (`GET /api/returns/{id}/workflow`).

| # | Persona | Does | Written to the database | Next persona sees |
|---|---|---|---|---|
| 1a | Returns analyst | Checks the return against the recorded policy window; if definitively outside policy, rejects it without warehouse handoff | return `rejected`, policy-basis timeline event, customer message draft | Analyst queue: review message |
| 1b | Returns analyst | If policy eligibility is confirmed, opens an inspection case; system assigns the active warehouse manager immediately | `investigation_cases` (`assigned`), case note with policy screen, return handoff event | Warehouse queue: receive / inspect |
| 2 | Warehouse manager | Confirms physical arrival, records receipt, inspects the unit and records a feasibility verdict | receipt timestamp, `inspections`, case `in_progress` then `ready_for_review` | Analyst queue: submit or decline |
| 3 | Warehouse manager | Gives a verdict: can the refund or replacement be performed? (replacement: stock is checked) | `warehouse_verdicts`, case `ready_for_review` | Analyst queue: submit or decline |
| 4a | Returns analyst | Submits the refund or replacement (only if the verdict says proceed and matches the request type) | `refunds` / `replacement_requests` (requested), case `pending_approval` | Supervisor queue, with the verdict and inspection |
| 4b | Returns analyst | Declines after an unsuccessful warehouse verdict (reason required) | return `rejected`, case `resolved`, `customer_notifications` draft | Analyst queue: review message |
| 5 | Returns supervisor | Reviews the complete return timeline, inspection and warehouse verdict; approves or rejects (reason required) | local refund ledger decision / replacement stock reservation, return resolved or rejected, case resolved, message draft | Analyst queue: review message |
| 6 | Returns analyst | Reviews and confirms the drafted customer message | local message confirmation, case `closed`, return `closed` | (finished) |

## Rules enforced by the API (HTTP 409 when broken)
- No refund or replacement can be submitted without an open case and a warehouse verdict of *proceed*.
- A case cannot be opened when the recorded policy check definitively fails or required policy dates are missing.
- A warehouse handoff does not record physical arrival; receipt must be confirmed and recorded separately before inspection.
- A refund cannot be submitted for a replacement request, or the other way round.
- Only one open refund or replacement request per return; only one completed refund per return.
- A warehouse verdict of *proceed* needs stock for replacements; a *decline* needs a reason.
- Rejecting or declining needs a reason, and the reason is written into the customer email draft.
- Cases only move forward: open → in progress → ready for review → pending approval → resolved → closed.

## Persona permissions
| | Analyst | Warehouse | Supervisor |
|---|---|---|---|
| Open cases, submit refund / replacement, decline, send customer email | yes | | yes |
| Receive, inspect, give verdict | | yes | yes |
| Approve / reject refunds and replacements, assign / resolve cases | | | yes |

Customer messages are drafted and confirmation is logged; no mail server is configured (seeded customer addresses use the `.invalid` domain). Refund completion updates the demo ledger only; no payment provider is connected, so no money is transferred.

## Tests
`backend/tests/` is the complete backend suite (`python -m pytest tests/ -q` from `backend/`). The persona workflow tests drive approve, reject, decline and replacement paths through the API as each persona and assert hand-offs from the database and the next persona's queue.
