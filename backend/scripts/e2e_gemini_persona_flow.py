"""End-to-end three-persona workflow via live API + Gemini agent.

Usage (backend running on :8000):
  python scripts/e2e_gemini_persona_flow.py R119
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8000"
LLM = "gemini"
DEFAULT_RETURN = "R119"

ACCOUNTS = {
    "analyst": ("returns_analyst", "ShopSphere@Analyst1"),
    "warehouse": ("warehouse_mgr", "ShopSphere@Warehouse1"),
    "supervisor": ("returns_supervisor", "ShopSphere@Super1"),
}


def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 300):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return e.code, payload


def login(role: str) -> str:
    username, password = ACCOUNTS[role]
    code, data = req("POST", "/api/auth/login", body={"username": username, "password": password})
    if code != 200:
        raise RuntimeError(f"login failed {role}: {code} {data}")
    return data["access_token"]


def chat(token: str, message: str, return_id: str, conv: str) -> tuple[int, dict | None]:
    return req(
        "POST",
        "/api/chat",
        token,
        {
            "message": message,
            "return_id": return_id,
            "conversation_id": conv,
            "history": [],
            "llm_provider": LLM,
        },
        timeout=300,
    )


def tool_names(payload: dict | None) -> list[str]:
    if not payload:
        return []
    events = payload.get("tool_events") or []
    out: list[str] = []
    for t in events:
        name = t.get("tool") or t.get("tool_name") or t.get("name")
        if name:
            out.append(str(name))
    return out


def workflow_via_db(return_id: str) -> dict:
    from app.database.session import get_session_maker
    from app.services.return_workflow import build_return_workflow_snapshot

    session = get_session_maker()()
    try:
        return build_return_workflow_snapshot(session, return_id)
    finally:
        session.close()


class Reporter:
    def __init__(self, return_id: str) -> None:
        self.return_id = return_id
        self.lines: list[str] = []
        self.checks: list[tuple[str, bool, str]] = []

    def log(self, msg: str) -> None:
        self.lines.append(msg)
        print(msg, flush=True)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        self.log(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    def section(self, title: str) -> None:
        self.log("")
        self.log(f"{'=' * 60}")
        self.log(title)
        self.log(f"{'=' * 60}")

    def write_report(self) -> Path:
        out_dir = Path(__file__).resolve().parents[2] / "docs"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"E2E_GEMINI_{self.return_id}_{ts}.md"
        passed = sum(1 for _, ok, _ in self.checks if ok)
        total = len(self.checks)
        summary = f"**Result:** {passed}/{total} checks passed\n\n"
        body = "\n".join(self.lines)
        checks_md = "\n".join(
            f"- [{'x' if ok else ' '}] **{name}**{': ' + detail if detail else ''}"
            for name, ok, detail in self.checks
        )
        path.write_text(
            f"# E2E Gemini persona flow — {self.return_id}\n\n"
            f"Generated: {ts} UTC\n\n{summary}\n## Checks\n\n{checks_md}\n\n## Log\n\n```\n{body}\n```\n",
            encoding="utf-8",
        )
        return path


def main() -> int:
    return_id = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RETURN).upper()
    rep = Reporter(return_id)

    rep.section(f"E2E persona workflow — {return_id} (LLM={LLM})")

    code, health = req("GET", "/api/health")
    rep.check("API health", code == 200, str(health) if code != 200 else "ok")

    tok_a = login("analyst")
    tok_w = login("warehouse")
    tok_s = login("supervisor")
    rep.log("Logins: analyst, warehouse, supervisor — OK")

    snap0 = workflow_via_db(return_id)
    if snap0.get("error"):
        rep.log(f"ABORT: {snap0}")
        rep.check("Return exists", False, snap0.get("message", ""))
        rep.write_report()
        return 1
    rep.log(f"Initial workflow: stage={snap0.get('analyst_workflow_stage')} status_summary={snap0.get('status_summary')}")

    # --- Step 1: Returns analyst ---
    rep.section("STEP 1 — Returns analyst (investigate + open case)")
    p1 = (
        f"Investigate return {return_id} using shop data and complaint documents. "
        "Summarize findings briefly. If manual review is needed, open an investigation case "
        "(use a valid issue_type). Do not submit or approve any refund."
    )
    rep.log(f"PROMPT: {p1}")
    c1, r1 = chat(tok_a, p1, return_id, f"e2e-gemini-{return_id}-s1")
    if c1 != 200:
        rep.check("Analyst chat HTTP 200", False, str(r1))
    else:
        rep.check("Analyst chat HTTP 200", True)
        rep.log(f"TOOLS: {tool_names(r1)}")
        rep.log(f"RESPONSE (first 800 chars):\n{(r1.get('final_response') or '')[:800]}")
        rep.check(
            "Analyst used investigation or workflow tools",
            bool(tool_names(r1)),
            ",".join(tool_names(r1)[:8]),
        )

    snap1 = workflow_via_db(return_id)
    rep.log(
        f"After step 1: case_open={snap1.get('analyst_case_open')} "
        f"stage={snap1.get('analyst_workflow_stage')}"
    )
    rep.check("Analyst case opened", snap1.get("analyst_case_open") is True, str(snap1.get("active_case")))

    # --- Step 2: Warehouse ---
    rep.section("STEP 2 — Warehouse manager (receive + inspect)")
    code, ret_row = req("GET", f"/api/returns/{return_id}", tok_w)
    if code == 200 and not ret_row.get("received_date"):
        rep.log("API: POST receive (unit arrived)")
        c_recv, recv = req("POST", f"/api/returns/{return_id}/receive", tok_w)
        rep.check("Warehouse receive API", c_recv == 200, str(recv)[:200] if c_recv != 200 else "received")

    p2 = (
        f"For return {return_id}, what is the handoff status and what should warehouse do next? "
        "Keep under 100 words."
    )
    rep.log(f"PROMPT: {p2}")
    c2a, r2a = chat(tok_w, p2, return_id, f"e2e-gemini-{return_id}-s2a")
    if c2a == 200:
        rep.log(f"TOOLS: {tool_names(r2a)}")
        rep.log(f"RESPONSE (first 500 chars):\n{(r2a.get('final_response') or '')[:500]}")
        rep.check("Warehouse chat OK", True)
    else:
        rep.check("Warehouse chat OK", False, str(r2a))

    snap2b = workflow_via_db(return_id)
    if (snap2b.get("inspection_count") or 0) < 1:
        insp_body = {
            "product_condition": "defective",
            "returned_serial_number": None,
            "accessories_complete": True,
            "defect_verified": True,
            "inspection_result": "fail",
            "inspector_notes": f"E2E Gemini — defect verified for {return_id}",
        }
        rep.log(f"API: POST inspection {insp_body}")
        c2b, r2b = req("POST", f"/api/returns/{return_id}/inspections", tok_w, insp_body)
        rep.check("Warehouse inspection API", c2b == 201, str(r2b)[:200] if c2b != 201 else "created")

    snap2 = workflow_via_db(return_id)
    rep.log(f"After step 2: insp={snap2.get('inspection_count')} warehouse_done={snap2.get('warehouse_work_complete')}")
    rep.check("Inspection on file", (snap2.get("inspection_count") or 0) >= 1)
    rep.check(
        "Analyst ready to submit (refund/replacement)",
        snap2.get("analyst_workflow_stage") in ("submit_refund", "submit_replacement"),
        str(snap2.get("analyst_workflow_stage")),
    )

    # --- Step 3: Analyst submit ---
    rep.section("STEP 3 — Returns analyst (submit to supervisor)")
    p3 = (
        f"For {return_id}, check refundable amount and submit a refund request to the supervisor. "
        "Do not approve or execute payout yourself."
    )
    rep.log(f"PROMPT: {p3}")
    c3, r3 = chat(tok_a, p3, return_id, f"e2e-gemini-{return_id}-s3")
    if c3 == 200:
        rep.log(f"TOOLS: {tool_names(r3)}")
        rep.log(f"RESPONSE (first 800 chars):\n{(r3.get('final_response') or '')[:800]}")
        rep.check("Analyst submit chat OK", True)
    else:
        rep.check("Analyst submit chat OK", False, str(r3))

    snap3 = workflow_via_db(return_id)
    pending = snap3.get("supervisor_pending") or {}
    rep.log(f"After step 3: stage={snap3.get('analyst_workflow_stage')} supervisor_pending={pending}")
    rep.check(
        "Awaiting supervisor",
        snap3.get("analyst_workflow_stage") == "await_supervisor" or pending.get("pending"),
        snap3.get("status_summary", ""),
    )

    code, dash_s = req("GET", "/api/dashboard/workspace", tok_s)
    if code == 200:
        queue = next((s for s in dash_s.get("sections", []) if s.get("key") == "approval_queue"), None)
        items = [i for i in (queue or {}).get("items", []) if i.get("return_id") == return_id]
        rep.log(f"Supervisor dashboard queue for {return_id}: {len(items)} item(s)")
        rep.check("Supervisor dashboard lists return", len(items) >= 1, f"queue_total={dash_s.get('kpis', {}).get('queue_total')}")

    # --- Step 4: Supervisor ---
    rep.section("STEP 4 — Returns supervisor (status + approve)")
    p4 = f"What is the status of the pending request for {return_id}? Should I approve?"
    rep.log(f"PROMPT: {p4}")
    c4a, r4a = chat(tok_s, p4, return_id, f"e2e-gemini-{return_id}-s4a")
    if c4a == 200:
        rep.log(f"TOOLS: {tool_names(r4a)}")
        rep.log(f"RESPONSE (first 800 chars):\n{(r4a.get('final_response') or '')[:800]}")
        rep.check("Supervisor status chat OK", True)
        rep.check(
            "Supervisor agent did not error",
            "agent execution failed" not in (r4a.get("final_response") or "").lower(),
        )
    else:
        rep.check("Supervisor status chat OK", False, str(r4a))

    refund_id = pending.get("refund_id")
    action_id = pending.get("action_id")
    if refund_id:
        rep.log(f"API: approve refund_id={refund_id}")
        c4b, r4b = req("POST", f"/api/refunds/{refund_id}/approve", tok_s, {"approve": True})
        rep.check("Supervisor approve refund API", c4b == 200, str(r4b)[:200] if c4b != 200 else "approved")
    elif action_id:
        rep.log(f"API: approve action_id={action_id}")
        c4b, r4b = req("POST", f"/api/actions/{action_id}/approve", tok_s, {"approve": True})
        rep.check("Supervisor approve action API", c4b == 200, str(r4b)[:200] if c4b != 200 else "approved")
    else:
        rep.check("Supervisor had pending item to approve", False, "no refund_id or action_id")

    snap4 = workflow_via_db(return_id)
    rep.log(f"After step 4: stage={snap4.get('analyst_workflow_stage')} summary={snap4.get('status_summary')}")

    # --- Step 5: Analyst customer follow-up ---
    rep.section("STEP 5 — Returns analyst (customer email)")
    p5 = f"Draft a short professional email to the customer about the supervisor decision on {return_id}."
    rep.log(f"PROMPT: {p5}")
    c5, r5 = chat(tok_a, p5, return_id, f"e2e-gemini-{return_id}-s5")
    if c5 == 200:
        rep.log(f"TOOLS: {tool_names(r5)}")
        rep.log(f"RESPONSE (first 600 chars):\n{(r5.get('final_response') or '')[:600]}")
        rep.check("Analyst follow-up chat OK", True)
    else:
        rep.check("Analyst follow-up chat OK", False, str(r5))

    snap5 = workflow_via_db(return_id)
    rep.check(
        "Final workflow after supervisor decision",
        snap5.get("analyst_workflow_stage") in ("customer_follow_up", "await_supervisor")
        or snap5.get("return_status") in ("resolved", "closed")
        or "customer" in (snap5.get("status_summary") or "").lower(),
        f"stage={snap5.get('analyst_workflow_stage')} status={snap5.get('return_status')}",
    )

    # Dashboard sync
    rep.section("Dashboard KPI spot-check (all personas)")
    for role, tok, persona in (
        ("analyst", tok_a, "returns_analyst"),
        ("warehouse", tok_w, "warehouse_manager"),
        ("supervisor", tok_s, "returns_supervisor"),
    ):
        code, dash = req("GET", "/api/dashboard/workspace", tok)
        ok = code == 200 and dash.get("persona") == persona
        rep.check(f"Dashboard {role}", ok, f"HTTP {code} persona={dash.get('persona') if code == 200 else 'n/a'}")

    all_ok = all(ok for _, ok, _ in rep.checks)
    rep.section("SUMMARY")
    rep.log(f"Overall: {'PASS' if all_ok else 'FAIL'} ({sum(1 for _, ok, _ in rep.checks if ok)}/{len(rep.checks)} checks)")
    report_path = rep.write_report()
    rep.log(f"Report written: {report_path}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
