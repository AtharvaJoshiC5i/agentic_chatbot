"""Live E2E checks against running API (localhost:8000). Run from backend with venv."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

ACCOUNTS = (
    ("returns_analyst", "ShopSphere@Analyst1", "analyst"),
    ("warehouse_mgr", "ShopSphere@Warehouse1", "warehouse"),
    ("returns_supervisor", "ShopSphere@Super1", "supervisor"),
)


def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 120):
    url = f"{BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
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


def login(username: str, password: str) -> tuple[str, str]:
    code, data = req("POST", "/api/auth/login", body={"username": username, "password": password})
    assert code == 200, (username, code, data)
    return data["access_token"], data["role"]


def main() -> int:
    results: list[str] = []
    tokens: dict[str, str] = {}

    for username, password, label in ACCOUNTS:
        tok, role = login(username, password)
        tokens[label] = tok
        results.append(f"LOGIN {label}: OK role={role}")

    # Dashboard per persona
    for label, expected_persona in (
        ("analyst", "returns_analyst"),
        ("warehouse", "warehouse_manager"),
        ("supervisor", "returns_supervisor"),
    ):
        code, dash = req("GET", "/api/dashboard/workspace", tokens[label])
        assert code == 200, dash
        assert dash["persona"] == expected_persona
        kpi_keys = set(dash["kpis"].keys())
        section_keys = {s["key"] for s in dash["sections"]}
        results.append(
            f"DASHBOARD {label}: persona={dash['persona']} kpis={sorted(kpi_keys)} sections={sorted(section_keys)}"
        )

    # Role gates
    code, _ = req("GET", "/api/approvals", tokens["warehouse"])
    results.append(f"APPROVALS warehouse: HTTP {code} (expect 403)")
    code, _ = req("GET", "/api/approvals", tokens["supervisor"])
    results.append(f"APPROVALS supervisor: HTTP {code} (expect 200)")

    code, tasks = req("GET", "/api/recovery/tasks?limit=5", tokens["warehouse"])
    results.append(f"TASKS warehouse: HTTP {code} count={len(tasks) if code == 200 else 'n/a'}")

    code, denied = req("GET", "/api/recovery/tasks?limit=5", tokens["analyst"])
    results.append(f"TASKS analyst: HTTP {code} (expect 403)")

    # R105 state before workflow
    code, r105 = req("GET", "/api/returns/R105", tokens["analyst"])
    results.append(f"R105 status before chat: {r105.get('return_status') if code == 200 else code}")

    # Agent chat — analyst (pinned R105)
    analyst_prompt = (
        "Investigate return R105 with evidence. Summarize findings in 3 bullets. "
        "If manual review is required, create an investigation case. Do not execute a refund."
    )
    code, chat = req(
        "POST",
        "/api/chat",
        tokens["analyst"],
        {
            "message": analyst_prompt,
            "return_id": "R105",
            "conversation_id": "e2e-analyst-r105",
            "history": [],
            "llm_provider": "groq",
        },
        timeout=180,
    )
    if code == 200:
        tools = [t.get("tool_name") for t in chat.get("tool_events", [])]
        preview = (chat.get("final_response") or "")[:400]
        results.append(f"CHAT analyst: OK tools={tools}")
        results.append(f"CHAT analyst response preview: {preview!r}")
    else:
        results.append(f"CHAT analyst: HTTP {code} {chat}")

    code, r105_after = req("GET", "/api/returns/R105", tokens["analyst"])
    results.append(f"R105 status after analyst: {r105_after.get('return_status') if code == 200 else code}")

    # Warehouse chat — inspection guidance for R105 if still received
    wh_prompt = (
        "For return R105, summarize what inspection should verify based on shop data and documents. "
        "Keep the answer under 120 words."
    )
    code, chat_wh = req(
        "POST",
        "/api/chat",
        tokens["warehouse"],
        {
            "message": wh_prompt,
            "return_id": "R105",
            "conversation_id": "e2e-wh-r105",
            "history": [],
            "llm_provider": "groq",
        },
        timeout=180,
    )
    if code == 200:
        preview = (chat_wh.get("final_response") or "")[:350]
        results.append(f"CHAT warehouse: OK preview={preview!r}")
    else:
        results.append(f"CHAT warehouse: HTTP {code} {chat_wh}")

    # Supervisor dashboard KPIs vs summary
    code, summary = req("GET", "/api/dashboard/summary", tokens["supervisor"])
    code2, dash_sup = req("GET", "/api/dashboard/workspace", tokens["supervisor"])
    if code == 200 and code2 == 200:
        r1 = summary.get("refunds_awaiting_approval")
        r2 = dash_sup["kpis"].get("refunds_awaiting_approval")
        a1 = summary.get("actions_awaiting_approval")
        a2 = dash_sup["kpis"].get("actions_awaiting_approval")
        match = r1 == r2 and a1 == a2
        results.append(f"SUPERVISOR KPI match summary vs workspace: {match} refunds={r1}/{r2} actions={a1}/{a2}")

    for line in results:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
