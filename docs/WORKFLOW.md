# Persona workflow

Three personas share one database. Every step writes its result to the database, and the next persona reads it from
their own queue (`GET /api/dashboard/workspace`) or the agent's live workflow snapshot (`GET /api/returns/{id}/workflow`).

| # | Persona | Does | Written to the database | Next persona sees |
|---|---|---|---|---|
| 1 | Returns analyst | Investigates against policy, opens an investigation case | `investigation_cases` (open), return `investigating` | Warehouse queue: receive / inspect |
| 2 | Warehouse manager | Receives and inspects the unit | `inspections`, case `in_progress` (assigned to the warehouse user) | Warehouse queue: verdict |
| 3 | Warehouse manager | Gives a verdict: can the refund or replacement be performed? (replacement: stock is checked) | `warehouse_verdicts`, case `ready_for_review` | Analyst queue: submit or decline |
| 4a | Returns analyst | Submits the refund or replacement (only if the verdict says proceed and matches the request type) | `refunds` / `replacement_requests` (requested), case `pending_approval` | Supervisor queue, with the verdict and inspection |
| 4b | Returns analyst | Declines instead (needs a reason), after a decline verdict | return `rejected`, case `resolved`, `customer_notifications` draft | Analyst queue: send email |
| 5 | Returns supervisor | Approves (refund is paid out, or replacement stock is reserved) or rejects (reason required) | refund `completed` / replacement `approved`, return `resolved` or `rejected`, case `resolved`, `customer_notifications` draft | Analyst queue: send email |
| 6 | Returns analyst | Reviews, edits and confirms the drafted customer email | notification `sent`, case `closed`, return `closed` | (finished) |

## Rules enforced by the API (HTTP 409 when broken)
- No refund or replacement can be submitted without an open case and a warehouse verdict of *proceed*.
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

"Customer email sent" means the analyst confirmed it: it is logged on the timeline and in the audit trail. No mail
server is called (customer addresses in the dataset use the `.invalid` domain).

## Tests
`backend/tests/test_persona_workflow.py` drives approve, reject, decline and replacement paths through the API as each
persona and asserts every hand-off from the database and from the next persona's queue.
