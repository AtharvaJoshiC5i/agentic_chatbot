# Cursor prompt: fix the persona workflow end to end (backend, agent, frontend)

**Implementation status:** Phases 1–3 backend, Phase 4 login/permissions (three demo personas), Phase 5 workflow/agent tools, Phase 6 approvals/tasks pages, `useLiveResource`, context panel workflow actions. Verify with `docs/WORKFLOW_VERIFICATION.md` and full test suite.

Paste everything below the line into Cursor (agent mode, repo root open). Work in the phases listed. After each phase run the tests named there and stop for review.

---

## Goal
Whatever a persona does must actually change the system and be visible to the next persona. An audit on a clean return (R105) found the defects below. Fix all of them. Do not touch the synthetic data, the unstructured documents, or the fixed chat visuals except where stated.

## Confirmed defects (reproduce each with a test first)
- **B1** `execute_refund` can never succeed: `services/refundable.py::calculate_refundable_amount_paise` counts the refund's own `approved` status, so remaining balance is 0 at execution.
- **B2** `returns.return_status` never changes after cases, refunds or tasks.
- **B3** Recovery tasks cannot be listed or updated, cases cannot be resolved or closed, inspections cannot be recorded.
- **B4** One refund takes four steps: approve action, execute action (only creates a refund row), approve refund, execute refund.
- **B5** Repeated refund requests create several open refund rows that block each other.
- **B6** No cross-return queues (`GET /api/refunds` is 404; `GET /api/actions` needs a return id). The dashboard "refunds awaiting approval" counts refund rows, so a pending action is invisible.
- **F1** The UI can only approve and execute actions. No UI for assigning cases, creating or updating tasks, recording inspections, or an approvals queue.
- **F2** Cards in chat messages are snapshots and never refresh when another user changes state.
- **Engine** `investigation/signals.py::derive_primary_signal` reports `duplicate_refund_attempt` for any return with a completed refund, so legitimately refunded returns look suspicious.

## Phase 1: backend correctness (tests first)
1. B1: exclude the refund being executed from the refundable calculation (`exclude_refund_id`). Test: request, approve, execute a single refund on a clean return and assert `completed`.
2. B5: reject a new refund request when an open (`requested` or `approved`) refund already exists for the return; return 409 with a clear message. The early completed-refund check in `services/actions.py` stays.
3. Engine: change the signal so a completed refund only produces `duplicate_refund_attempt` when a **new** refund request is being evaluated (an open request exists alongside the completed one). A resolved return with a completed refund and no open request must show `no_inconsistency_detected`. Keep R106 behaviour: the seed has a completed refund and the scenario expects `duplicate_refund_attempt`, so keep the signal when the user is asking about further refund and update the ground-truth eval accordingly. Document the rule.
4. Run: `pytest backend/tests -q` and `python scripts/run_ground_truth_eval.py` (from `backend/`).

## Phase 2: status transitions and workflow
Define one state machine in `backend/app/services/return_status.py` and call it from every service that changes work state. Never set `return_status` anywhere else.

| Trigger | New return status | Allowed from |
|---|---|---|
| Case created | `investigating` | received, inspecting |
| Case resolved or closed | back to previous work state, or `resolved` if a refund is completed | investigating |
| Inspection recorded | `inspecting` (first one) | received |
| Refund completed | `resolved` | received, inspecting, investigating |
| Refund request rejected by a supervisor | `rejected` | any open state |
| Return closed (supervisor action) | `closed` | resolved, rejected |

Each transition records a `return_events` row and an audit log. Add `POST /api/returns/{id}/close`.
Collapse the refund chain (B4): one supervisor **approval** of the refund request is the only approval. Executing an approved refund request happens **automatically** after approval (same transaction) unless the amount is above ₹50,000, in which case it needs a second sign-off by a different supervisor. Keep `/api/refunds/*` endpoints and the action endpoints working, but make the action `request_refund` create the refund row immediately (status `requested`, `pending`), so it is visible to supervisors at once. Test every step.

## Phase 3: missing endpoints (B3, B6)
Add, with role checks and tests:
- `GET /api/approvals` (supervisor): pending refund requests and pending actions across all returns, newest first, with amount, return id, requester, age.
- `GET /api/refunds?status=` and `GET /api/actions?status=` (return id optional).
- `GET /api/recovery/tasks?status=&assigned_to=`, `PATCH /api/recovery/tasks/{id}` (assign, `in_progress`, `completed`, with `completed_at`), only operations and supervisor.
- `POST /api/returns/{id}/inspections` (operations, supervisor): condition, serial, accessories, defect verified, result, notes; validates serial rules and moves the return status per the table.
- `POST /api/cases/{id}/resolve` and `/close` (supervisor).
- Make the dashboard counts derive from the same queries as the new queues so they always agree.

## Phase 4: three personas
Replace the five demo personas with three. Keep the enum values in the database (no schema change), but remove `customer_support_agent` and `administrator` from seeds, login hints, permission tables and docs.

| Persona (username) | Role | Can do |
|---|---|---|
| Analyst (`returns_analyst`) | returns_analyst | Read everything, investigate, create cases, request refunds. Cannot approve or do recovery work. |
| Operations (`warehouse_mgr`) | warehouse_manager | Read everything, record inspections, create, list and update recovery and inspection tasks, supplier returns. Cannot touch cases or refunds. |
| Supervisor (`returns_supervisor`) | returns_supervisor | Everything above, plus approve or reject refunds and actions, assign, resolve and close cases, monitoring, timeline sync, close returns. |

Update `security/permissions.py`, `services/action_policy.py`, `scripts/seed_users.py`, the agent tools (role checks live inside tools, as today), `questions.md`, `docs/`, and the tests in `backend/tests/test_actions.py` and `test_agent_role_tools.py`. Run the role matrix: every restricted endpoint for every role returns 403 or success exactly as the table says.

## Phase 5: agent tools
Add tools with the same role checks as the API: `approve_refund_request`, `resolve_investigation_case`, `record_inspection` (operations and supervisor), `update_recovery_task`. Keep one `list_pending_approvals` tool backed by `/api/approvals` logic. Update the system prompt playbook and `agents/capabilities.py`. Tool results must stay consistent with the API (use the same service functions).

## Phase 6: frontend
Use the existing design system (Tailwind utilities only, Inter, `stone` and `accent` tokens, no custom CSS classes).
- **Approvals page** `/workspace/approvals` (supervisor only): table of pending refunds and actions, approve and reject buttons, row updates immediately, amount in rupees, approval tier shown. Show a count badge in the sidebar.
- **Tasks page** `/workspace/tasks` (operations, supervisor): list with filters, assign, start, complete.
- **Return detail panel** (existing context panel): role-aware buttons for assigning, resolving and closing a case, recording an inspection, and closing a return.
- **Refresh (F2):** cards must read live state, not a snapshot. Fetch action, refund or case state by id when a card mounts, and refetch every 20 seconds while visible and on window focus. Also refetch the context panel and sidebar counts after any write. Use one small `useLiveResource` hook; do not add a data library.
- Hide controls the role cannot use. Show server error messages in a toast, never fail silently.
- Update `lib/roles` copy for the three personas.

## Acceptance (run all, report results)
1. A single refund on a clean return goes request, supervisor approve, completed with no other clicks (below ₹50,000), and the return becomes `resolved`.
2. A second refund request on the same return is rejected with 409.
3. Creating a case moves the return to `investigating`; resolving it moves it on; every change appears in the timeline and, after refresh, in every persona's UI within 20 seconds.
4. Operations can record an inspection, create, start and complete a task; the task list shows it for the supervisor.
5. The role matrix test passes for all three personas; removed roles cannot log in.
6. `pytest backend/tests -q`, `npm run lint`, and `npm run build` all pass; the ground-truth eval has no regressions.
7. A manual run-through of R105 with the three logins, written up in `docs/WORKFLOW_VERIFICATION.md` with what each persona saw at each step.
