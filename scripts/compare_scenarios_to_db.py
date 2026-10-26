"""Compare reserved scenarios R101-R115 in a fresh bundle against the current SQLite file.

Used once before reseeding, to prove the generator rewrite did not move any
hand-designed scenario row (the unstructured documents cite those values).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.synthetic.generator import generate_synthetic_data  # noqa: E402

IDS = [f"R{i}" for i in range(101, 116)]


def norm(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, str) and len(value) >= 19 and value[4] == "-" and value[10] == " ":
        return value[:19]
    if isinstance(value, bool):
        return int(value)
    return value


def main() -> int:
    bundle = generate_synthetic_data()
    conn = sqlite3.connect(f"file:{(ROOT / 'backend' / 'shopsphere.db').as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    drift = 0

    def compare(label: str, old: list[dict], new: list[dict]) -> None:
        nonlocal drift
        old_n = [{k: norm(v) for k, v in row.items() if k in new[0]} for row in old] if new else []
        new_n = [{k: norm(v) for k, v in row.items() if k in (old[0] if old else new[0])} for row in new]
        if old_n != new_n:
            drift += 1
            print(f"  DRIFT {label}")
            for a, b in zip(old_n, new_n):
                if a != b:
                    print("    old:", a)
                    print("    new:", b)
                    break

    for rid in IDS:
        r_new = [r for r in bundle.returns if r["return_id"] == rid]
        r_old = [dict(r) for r in conn.execute("SELECT * FROM returns WHERE return_id=?", (rid,))]
        compare(f"{rid} return", r_old, r_new)
        item_id = r_new[0]["order_item_id"]
        i_new = [r for r in bundle.order_items if r["order_item_id"] == item_id]
        i_old = [dict(r) for r in conn.execute("SELECT * FROM order_items WHERE order_item_id=?", (item_id,))]
        compare(f"{rid} order item", i_old, i_new)
        order_id = i_new[0]["order_id"]
        compare(f"{rid} order", [dict(r) for r in conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))], [o for o in bundle.orders if o["order_id"] == order_id])
        compare(f"{rid} delivery", [dict(r) for r in conn.execute("SELECT * FROM deliveries WHERE order_id=?", (order_id,))], [d for d in bundle.deliveries if d["order_id"] == order_id])
        compare(f"{rid} product", [dict(r) for r in conn.execute("SELECT * FROM products WHERE product_id=?", (f"P_{rid}",))], [p for p in bundle.products if p["product_id"] == f"P_{rid}"])
        n_insp = [i for i in bundle.inspections if i["return_id"] == rid]
        o_insp = [dict(r) for r in conn.execute("SELECT * FROM inspections WHERE return_id=? ORDER BY inspection_id", (rid,))]
        if n_insp or o_insp:
            compare(f"{rid} inspections", o_insp, n_insp) if n_insp and o_insp else print(f"  DRIFT {rid} inspection presence") or None
        n_case = [c for c in bundle.investigation_cases if c["return_id"] == rid]
        o_case = [dict(r) for r in conn.execute("SELECT * FROM investigation_cases WHERE return_id=?", (rid,))]
        if n_case or o_case:
            compare(f"{rid} case", o_case, n_case) if n_case and o_case else print(f"  DRIFT {rid} case presence") or None

    print("Scenario rows identical to the current database" if drift == 0 else f"{drift} scenario row group(s) drifted")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
