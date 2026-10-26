"""Live E2E: R113 three-persona workflow on running API."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
RETURN_ID = "R113"

ACCOUNTS = {
    "analyst": ("returns_analyst", "ShopSphere@Analyst1"),
    "warehouse": ("warehouse_mgr", "ShopSphere@Warehouse1"),
    "supervisor": ("returns_supervisor", "ShopSphere@Super1"),
}


def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 180):
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
    u, p = ACCOUNTS[role]
    code, data = req("POST", "/api/auth/login", body={"username": u, "password": p})
    assert code == 200, data
    return data["access_token"]


def chat(token: str, message: str, conv: str) -> tuple[int, dict | None]:
    return req(
        "POST",
        "/api/chat",
        token,
        {
            "message": message,
            "return_id": RETURN_ID,
            "conversation_id": conv,
            "history": [],
            "llm_provider": "groq",
        },
        timeout=240,
    )


def main() -> int:
    lines: list[str] = []
    rid = RETURN_ID

    def log(msg: str) -> None:
        lines.append(msg)
        print(msg, flush=True)

    log(f"=== E2E workflow for {rid} ===")

    tok_a = login("analyst")
    tok_w = login("warehouse")
    tok_s = login("supervisor")

    code, before = req("GET", f"/api/returns/{rid}", tok_a)
    log(f"STEP 0 status before: {before.get('return_status') if code == 200 else code}")

    # Step 1 — Analyst investigation
    p1 = (
        f"Investigate return {rid} with evidence from shop data and documents. "
        "If manual review is required, create an investigation case. "
        "Do not execute or approve a refund."
    )
    log(f"STEP 1 ANALYST PROMPT: {p1}")
    c1, r1 = chat(tok_a, p1, "e2e-r113-step1")
    if c1 == 200:
        tools = r1.get("tool_events") or []
        tool_names = [t.get("name") or t.get("tool_name") for t in tools]
        log(f"STEP 1 HTTP {c1} tools={tool_names}")
        log(f"STEP 1 RESPONSE (first 600 chars): {(r1.get('final_response') or '')[:600]}")
    else:
        log(f"STEP 1 FAILED HTTP {c1}: {r1}")

    code, after1 = req("GET", f"/api/returns/{rid}", tok_a)
    log(f"STEP 1 return status after: {after1.get('return_status')}")

    code, cases = req("GET", f"/api/cases?limit=20", tok_a)
    case_for = [c for c in (cases or {}).get("items", []) if c.get("return_id") == rid]
    log(f"STEP 1 cases for {rid}: {len(case_for)} {case_for[:1]}")

    # Step 2 — Warehouse inspection
    p2 = f"Summarize what inspection should verify for {rid} based on data (one short paragraph)."
    log(f"STEP 2a WAREHOUSE CHAT PROMPT: {p2}")
    c2a, r2a = chat(tok_w, p2, "e2e-r113-step2a")
    if c2a == 200:
        log(f"STEP 2a RESPONSE (first 400 chars): {(r2a.get('final_response') or '')[:400]}")
    else:
        log(f"STEP 2a chat HTTP {c2a}: {r2a}")

    insp = {
        "product_condition": "defective",
        "returned_serial_number": "USB113TEST",
        "accessories_complete": True,
        "defect_verified": True,
        "inspection_result": "fail",
        "inspector_notes": "E2E R113 — USB ports dead, defect verified",
    }
    log(f"STEP 2b WAREHOUSE API POST inspection: {insp}")
    c2b, r2b = req("POST", f"/api/returns/{rid}/inspections", tok_w, insp)
    log(f"STEP 2b inspection HTTP {c2b}: {r2b if c2b != 201 else 'created'}")

    code, after2 = req("GET", f"/api/returns/{rid}", tok_w)
    log(f"STEP 2 return status after inspection: {after2.get('return_status')}")

    # Step 3 — Analyst refund request
    p3 = (
        f"For {rid}, check refund eligibility and submit a refund request for the full remaining refundable amount. "
        "Do not approve or execute payout."
    )
    log(f"STEP 3 ANALYST PROMPT: {p3}")
    c3, r3 = chat(tok_a, p3, "e2e-r113-step3")
    if c3 == 200:
        tools = r3.get("tool_events") or []
        tool_names = [t.get("name") or t.get("tool_name") for t in tools]
        log(f"STEP 3 HTTP {c3} tools={tool_names}")
        log(f"STEP 3 RESPONSE (first 600 chars): {(r3.get('final_response') or '')[:600]}")
    else:
        log(f"STEP 3 FAILED HTTP {c3}: {r3}")

    code, refunds = req("GET", f"/api/refunds?return_id={rid}", tok_s)
    log(f"STEP 3 refunds for {rid}: HTTP {code} {refunds}")

    code, approvals = req("GET", "/api/approvals", tok_s)
    pending_r = [x for x in (approvals or {}).get("refunds", []) if x.get("return_id") == rid]
    log(f"STEP 3 supervisor approvals queue for {rid}: {pending_r[:2]}")

    # Step 4 — Supervisor approve first pending refund for R113 if any
    if pending_r:
        refund_id = pending_r[0]["refund_id"]
        log(f"STEP 4 SUPERVISOR approve refund_id={refund_id}")
        c4, r4 = req("POST", f"/api/refunds/{refund_id}/approve", tok_s, {"approve": True})
        log(f"STEP 4 approve HTTP {c4}: {r4}")
        code, after4 = req("GET", f"/api/returns/{rid}", tok_s)
        log(f"STEP 4 return status after approve: {after4.get('return_status')}")
        code, ref = req("GET", f"/api/refunds?return_id={rid}", tok_s)
        log(f"STEP 4 refund rows: {ref}")
    else:
        log("STEP 4 skipped — no pending refund for R113 in approvals queue")

    # Dashboard spot-check
    for role, tok in [("analyst", tok_a), ("warehouse", tok_w), ("supervisor", tok_s)]:
        code, dash = req("GET", "/api/dashboard/workspace", tok)
        log(f"DASHBOARD {role}: persona={dash.get('persona')} kpis={dash.get('kpis')}")

    log("=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
