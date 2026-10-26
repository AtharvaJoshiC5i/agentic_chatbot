# R105 three-persona workflow verification

Manual checklist after Phase 3–6 implementation. Use clean return **R105** (hub not charging).

## Logins

| Persona | Username | Password (demo) |
|---------|----------|-----------------|
| Analyst | `returns_analyst` | `ShopSphere@Analyst1` |
| Operations | `warehouse_mgr` | `ShopSphere@Warehouse1` |
| Supervisor | `returns_supervisor` | `ShopSphere@Super1` |

Removed demo roles (`support_agent`, `admin`) receive **401** at login.

## Steps

1. **Analyst** — Open R105 in agent; run investigation; create case if prompted. Confirm return status becomes `investigating` in Data explorer or context panel timeline after refresh.
2. **Operations** — Record inspection on R105 (`/workspace` context panel **Record inspection** or API). Confirm status `inspecting` and timeline event.
3. **Analyst** — Submit refund request via agent or action API. Confirm pending row in supervisor **Approvals** (refund and/or action).
4. **Supervisor** — Approve from **Approvals** or chat action card. Confirm refund `completed` and return `resolved` without extra execute clicks (amount ≤ ₹50k).
5. **Supervisor** — Resolve case and **Close return** when policy allows.
6. **Second refund** on same return — expect **409** duplicate guard.

## Persona dashboards (`/workspace/dashboard`)

Default home after login remains **Agent** (`/workspace`). Open **Dashboard** from the top nav for a role-specific queue (bounded lists, no alert firehose).

| Persona | Dashboard should show | Should not show |
|---------|----------------------|-----------------|
| Analyst | KPIs (open investigations, my cases, my pending requests); **My cases** / **My pending requests**; starter cards → Agent | 200-row monitoring list; recovery tasks |
| Operations | My recovery tasks, unassigned tasks, **Awaiting inspection** returns; link to **Tasks** | Full approvals queue |
| Supervisor | Approval KPIs; refund/action previews with approve/reject; overdue cases; top priority alerts; **Run checks** / **View all alerts** | N/A |

**Monitoring** (`/workspace/monitoring`) is **supervisor-only** (analyst and warehouse redirect to Dashboard). `GET /api/monitoring/summary` is read-only; supervisors refresh signals via **Run checks** (`POST /api/monitoring/run`).

## Automated coverage

- `pytest backend/tests/test_workflow_api.py backend/tests/test_workspace_dashboard.py backend/tests/test_monitoring.py -q`
- Frontend: `npm run lint` and `npm run build`
