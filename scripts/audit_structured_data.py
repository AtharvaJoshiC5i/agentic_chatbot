"""Audit the structured synthetic dataset for realism and internal consistency.

Run from the repo root:
    backend/.venv/Scripts/python scripts/audit_structured_data.py            # audit a fresh in-memory bundle
    backend/.venv/Scripts/python scripts/audit_structured_data.py --db       # audit backend/shopsphere.db

Exit code is non-zero if any check fails. The reserved scenarios R101-R115 are
audited separately from the bulk returns because they are hand-designed.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
SCENARIOS = {f"R{i}" for i in range(101, 116)}
WINDOW = {"electronics": 30, "fashion": 15, "home_appliances": 30, "accessories": 30}
KNOWN_BRANDS = {
    "SoundPeak", "TechNova", "PixelEdge", "Ampere", "UrbanWeave", "LoomLane", "StitchCraft", "NovaWear",
    "HomeHive", "CoolBreeze", "ChefMate", "PureFlow", "CarryAll", "FlexFit", "DailyGear", "SnapCase",
}
TABLES = (
    "customers", "suppliers", "products", "orders", "order_items", "product_units", "deliveries", "returns",
    "inspections", "refunds", "investigation_cases", "recovery_options", "recovery_tasks",
)
DATE_COLUMNS = (
    "order_date", "dispatch_date", "delivery_date", "request_date", "received_date", "inspection_date",
    "processed_date", "created_at", "completed_at", "due_date",
)


def parse(value):
    if value is None or isinstance(value, datetime):
        return value
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_bundle():
    from app.synthetic.generator import generate_synthetic_data

    return generate_synthetic_data()


def load_db():
    conn = sqlite3.connect(f"file:{(ROOT / 'backend' / 'shopsphere.db').as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    data = {}
    for table in TABLES:
        rows = []
        for row in conn.execute(f"SELECT * FROM {table}"):
            record = dict(row)
            for column in DATE_COLUMNS:
                if column in record:
                    record[column] = parse(record[column])
            rows.append(record)
        data[table] = rows
    return SimpleNamespace(**data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", action="store_true", help="audit the SQLite database instead of a fresh bundle")
    args = parser.parse_args()
    b = load_db() if args.db else load_bundle()

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{f' ({detail})' if detail else ''}")
        if not ok:
            failures.append(name)

    ret = {r["return_id"]: r for r in b.returns}
    item = {i["order_item_id"]: i for i in b.order_items}
    order = {o["order_id"]: o for o in b.orders}
    deliv = {d["order_id"]: d for d in b.deliveries}
    prod = {p["product_id"]: p for p in b.products}
    insp: dict[str, list] = {}
    for row in b.inspections:
        insp.setdefault(row["return_id"], []).append(row)
    refunds: dict[str, list] = {}
    for row in b.refunds:
        refunds.setdefault(row["return_id"], []).append(row)
    cases = {}
    for row in b.investigation_cases:
        cases.setdefault(row["return_id"], []).append(row)
    options: dict[str, list] = {}
    for row in b.recovery_options:
        options.setdefault(row["return_id"], []).append(row)
    completed = [r for r in b.refunds if r["refund_status"] == "completed"]
    bulk = [r for r in b.returns if r["return_id"] not in SCENARIOS]

    def line(return_row):
        return item[return_row["order_item_id"]]

    def category(return_row):
        return prod[line(return_row)["product_id"]]["category"]

    def days_after_delivery(return_row):
        return (return_row["request_date"] - deliv[line(return_row)["order_id"]]["delivery_date"]).days

    print("Time consistency")
    check("no bulk return dated after the data snapshot (2026-03-20)", not [r["return_id"] for r in bulk if (r["request_date"] > NOW) or (r["received_date"] and r["received_date"] > NOW)])
    check("no bulk inspection after snapshot", not [i["return_id"] for i in b.inspections if i["return_id"] not in SCENARIOS and i["inspection_date"] > NOW])
    check("no refund processed after snapshot", not [r["return_id"] for r in b.refunds if r["processed_date"] and r["processed_date"] > NOW])
    check("no bulk case or task dated after snapshot", not [c for c in b.investigation_cases if c["return_id"] not in SCENARIOS and c["created_at"] > NOW] and not [t for t in b.recovery_tasks if t["created_at"] > NOW or (t["completed_at"] and t["completed_at"] > NOW)])
    check("every request is after delivery", not [r["return_id"] for r in b.returns if r["request_date"] <= deliv[line(r)["order_id"]]["delivery_date"]])
    check("every inspection is after warehouse receipt", not [i["return_id"] for i in b.inspections if ret[i["return_id"]]["received_date"] and i["inspection_date"] < ret[i["return_id"]]["received_date"]])

    print("Status drives which records exist")
    before_receipt = ("requested", "approved", "pickup_scheduled", "in_transit")
    mix = Counter(r["return_status"] for r in b.returns)
    print(f"    status mix: {dict(mix)}")
    check("returns not yet received have no received_date", not [r["return_id"] for r in b.returns if r["return_status"] in before_receipt and r["received_date"]])
    check("returns past receipt have a received_date", not [r["return_id"] for r in b.returns if r["return_status"] not in before_receipt and not r["received_date"]])
    check("returns not yet received have no inspection, refund or case", not [r["return_id"] for r in b.returns if r["return_status"] in before_receipt and (r["return_id"] in insp or r["return_id"] in refunds or r["return_id"] in cases)])
    check("completed refunds exist only on resolved/closed returns (plus R106)", all(ret[x["return_id"]]["return_status"] in ("resolved", "closed") or x["return_id"] == "R106" for x in completed), str(dict(Counter(ret[x["return_id"]]["return_status"] for x in completed))))
    check("at most one completed refund per return", max(Counter(x["return_id"] for x in completed).values()) == 1)
    check("refund never exceeds the line total", all(x["refund_amount"] <= line(ret[x["return_id"]])["unit_price"] * line(ret[x["return_id"]])["quantity"] for x in b.refunds))
    check("only R106 has a completed refund among R101-R115", sorted(x["return_id"] for x in completed if x["return_id"] in SCENARIOS) == ["R106"])
    check("R101 has no refund yet (agent must request one)", "R101" not in refunds)
    check("resolved/closed returns are mostly refunded (>=85%)", sum(1 for r in b.returns if r["return_status"] in ("resolved", "closed") and r["return_id"] in {x["return_id"] for x in completed}) >= 0.85 * sum(1 for r in b.returns if r["return_status"] in ("resolved", "closed")))
    awaiting = [r["return_id"] for r in b.returns if r["return_status"] == "received" and r["return_id"] not in insp]
    print(f"    received and awaiting inspection: {len(awaiting)} (R113 among them: {'R113' in awaiting})")
    check("R113 has no inspection", "R113" not in insp)

    print("Inspections match the stated reason")
    check("result 'pass' only when the defect is verified (or unsafe)", not [i["return_id"] for i in b.inspections if i["inspection_result"] == "pass" and not i["defect_verified"] and i["product_condition"] != "unsafe"])
    mismatches = sorted({i["return_id"] for i in b.inspections if i["returned_serial_number"] and line(ret[i["return_id"]])["purchased_serial_number"] and i["returned_serial_number"] != line(ret[i["return_id"]])["purchased_serial_number"]})
    print(f"    serial mismatches: {mismatches}")
    check("R102 and R107 keep their serial mismatch", {"R102", "R107"} <= set(mismatches))
    damaged_claims = [i for i in b.inspections if ret[i["return_id"]]["return_reason"] == "damaged" and i["return_id"] not in SCENARIOS and i["inspection_result"] != "pending"]
    check("damaged claims are inspected as damaged", all(i["product_condition"] == "damaged" for i in damaged_claims))
    accessory_claims = [i for i in b.inspections if ret[i["return_id"]]["return_reason"] == "missing_accessories" and i["return_id"] not in SCENARIOS and i["inspection_result"] != "pending"]
    check("missing-accessory claims record incomplete accessories", all(not i["accessories_complete"] for i in accessory_claims))

    print("Cases are backed by evidence")
    kinds = Counter(c["issue_type"] for c in b.investigation_cases)
    print(f"    cases: {dict(kinds)}")
    status_mix = Counter(c["case_status"] for c in b.investigation_cases)
    print(f"    case status: {dict(status_mix)}")
    check("case statuses are varied (>=4 kinds)", len(status_mix) >= 4)
    check("resolved/closed cases have resolution notes", all(c["resolution_notes"] for c in b.investigation_cases if c["case_status"] in ("resolved", "closed")))
    check("serial_mismatch cases have a real mismatch", all(c["return_id"] in mismatches for c in b.investigation_cases if c["issue_type"] == "serial_mismatch"))
    check("safety_concern cases have an unsafe inspection", all(any(i["product_condition"] == "unsafe" for i in insp.get(c["return_id"], [])) for c in b.investigation_cases if c["issue_type"] == "safety_concern"))
    check("conflicting_evidence cases have two disagreeing inspections", all(len(insp.get(c["return_id"], [])) == 2 and len({bool(i["defect_verified"]) for i in insp[c["return_id"]]}) == 2 for c in b.investigation_cases if c["issue_type"] == "conflicting_evidence"))
    check("delivery_dispute cases have a delivery issue", all(deliv[line(ret[c["return_id"]])["order_id"]]["delivery_issue"] for c in b.investigation_cases if c["issue_type"] == "delivery_dispute"))
    check("missing_inspection cases are received with no inspection", all(ret[c["return_id"]]["return_status"] == "received" and c["return_id"] not in insp for c in b.investigation_cases if c["issue_type"] == "missing_inspection" and c["return_id"] != "R113"))
    check("policy_exception cases are outside the window", all(days_after_delivery(ret[c["return_id"]]) > WINDOW[category(ret[c["return_id"]])] for c in b.investigation_cases if c["issue_type"] == "policy_exception"))
    check("duplicate_refund cases have a completed refund and a second request", all(len(refunds.get(c["return_id"], [])) == 2 and any(r["refund_status"] == "completed" for r in refunds[c["return_id"]]) for c in b.investigation_cases if c["issue_type"] == "duplicate_refund"))

    print("Return window realism")
    outside = [r for r in b.returns if days_after_delivery(r) > WINDOW[category(r)]]
    print(f"    outside the window: {len(outside)} of {len(b.returns)}")
    check("outside-window share is realistic (5-25%)", 0.05 <= len(outside) / len(b.returns) <= 0.25)
    check("R103 is outside the 30-day window", days_after_delivery(ret["R103"]) > 30)

    print("Catalogue realism")
    generated = [p for p in b.products if not p["product_id"].startswith("P_")]
    fashion = [p for p in generated if p["category"] == "fashion"]
    check("fashion prices stay under INR 8,000", max(p["original_price"] for p in fashion) <= 800_000, f"max INR {max(p['original_price'] for p in fashion) // 100}")
    check("all brands are from the fictional list", all(p["brand"] in KNOWN_BRANDS for p in b.products))
    check("no placeholder product names (e.g. 'Adaptive neutral complexity')", all(any(p["product_name"].startswith(brand) for brand in KNOWN_BRANDS) for p in b.products))
    check("fashion has no serial tracking; electronics and appliances do", all((p["serial_tracked"]) == (p["category"] in ("electronics", "home_appliances")) for p in b.products))
    print(f"    sample: {[p['product_name'] for p in generated[:3]]}")

    print("Recovery options and tasks")
    unsafe = {i["return_id"] for i in b.inspections if i["product_condition"] == "unsafe"}
    check("unsafe returns: only recycle/dispose are feasible", all(o["feasibility_status"] == "not_feasible" or o["recovery_method"] in ("recycle", "dispose") for r in unsafe for o in options.get(r, [])))
    check("R115 offers dispose and recycle, never resale", {o["recovery_method"] for o in options.get("R115", []) if o["feasibility_status"] == "feasible"} == {"dispose", "recycle"})
    check("R108 repair_and_resell is feasible", any(o["recovery_method"] == "repair_and_resell" and o["feasibility_status"] == "feasible" for o in options.get("R108", [])))
    check("net recovery = revenue - repair - handling - other", all(o["expected_net_recovery"] == o["expected_revenue"] - o["repair_cost"] - o["handling_cost"] - o["other_cost"] for o in b.recovery_options))
    check("resale options need a sellable condition", all(o["feasibility_status"] != "feasible" or o["recovery_method"] != "resell_new" or any(i["product_condition"] in ("new", "like_new") for i in insp.get(o["return_id"], [])) for o in b.recovery_options))
    check("tasks: completed_at is set only when completed", all((t["task_status"] == "completed") == (t["completed_at"] is not None) for t in b.recovery_tasks))
    print(f"    task status: {dict(Counter(t['task_status'] for t in b.recovery_tasks))}")

    print("Scenario R107 account history")
    history = [r["return_id"] for r in b.returns if order[line(r)["order_id"]]["customer_id"] == "C00107"]
    check("C00107 has earlier returns besides R107", len(history) >= 3, str(history))

    print()
    if failures:
        print(f"{len(failures)} check(s) failed")
        return 1
    print("All checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
