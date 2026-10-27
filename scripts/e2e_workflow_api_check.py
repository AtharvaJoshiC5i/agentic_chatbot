#!/usr/bin/env python3
"""Smoke-check governed returns workflow via live API (requires backend on :8000)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"

ACCOUNTS = [
    ("returns_analyst", "ShopSphere@Analyst1", "returns_analyst"),
    ("warehouse_mgr", "ShopSphere@Warehouse1", "warehouse_manager"),
    ("returns_supervisor", "ShopSphere@Super1", "returns_supervisor"),
]


def post(path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    results: list[str] = []
    try:
        urllib.request.urlopen(f"{BASE}/api/health", timeout=5)
    except Exception as e:
        print(f"FAIL: API not reachable at {BASE} ({e})")
        return 1

    tokens: dict[str, str] = {}
    for username, password, key in ACCOUNTS:
        tok = post("/api/auth/login", {"username": username, "password": password})["access_token"]
        tokens[key] = tok
        results.append(f"OK login {username}")

    for key, tok in tokens.items():
        dash = get("/api/dashboard/workspace", tok)
        persona = dash.get("persona")
        sections = dash.get("sections") or []
        item_count = sum(len(s.get("items") or []) for s in sections)
        results.append(f"OK dashboard persona={persona} sections={len(sections)} items={item_count}")

    analyst = tokens["returns_analyst"]
    dash = get("/api/dashboard/workspace", analyst)
    work = next((s for s in dash["sections"] if s.get("key") == "work_queue"), None)
    if not work or not work.get("items"):
        results.append("WARN analyst work_queue empty — pick a seeded return manually")
        sample_rid = "R101"
    else:
        sample_rid = work["items"][0]["return_id"]
        stage = work["items"][0].get("workflow_stage")
        results.append(f"OK analyst sample {sample_rid} stage={stage}")

    wf = get(f"/api/returns/{sample_rid}/workflow", analyst)
    if wf.get("error"):
        results.append(f"FAIL workflow snapshot {sample_rid}")
        return 1
    results.append(f"OK workflow snapshot status_summary={wf.get('status_summary', '')[:80]}…")

    timeline = get(f"/api/returns/{sample_rid}/timeline?sync=false", analyst)
    results.append(f"OK timeline events={len(timeline) if isinstance(timeline, list) else '?'}")

    print("\n".join(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
