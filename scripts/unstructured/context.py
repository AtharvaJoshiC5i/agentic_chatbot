"""Read-only access to backend/shopsphere.db for the document generator.

SQLite is the source of truth: every ID, serial, date, status and amount that
appears in a generated document is taken from here.
"""

from __future__ import annotations

import sqlite3
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SCENARIO_IDS = tuple(f"R{i}" for i in range(101, 116))

# Return windows (days from delivery) defined by the policy documents.
RETURN_WINDOW_DAYS = {
    "electronics": 30,
    "fashion": 15,
    "home_appliances": 30,
    "accessories": 30,
}

INSPECTION_SITES = (
    "Bhiwandi Returns Centre, Mumbai (MH)",
    "Hoskote Fulfilment Hub, Bengaluru (KA)",
    "Farrukhnagar Returns Centre, Gurugram (HR)",
    "Chakan Inspection Bay, Pune (MH)",
    "Sriperumbudur Returns Centre, Chennai (TN)",
    "Uluberia Fulfilment Hub, Kolkata (WB)",
    "Medchal Returns Centre, Hyderabad (TS)",
)

INSPECTORS = (
    ("WH-INS-014", "Kavya Iyer"),
    ("WH-INS-022", "Rohan Deshpande"),
    ("WH-INS-031", "Meenakshi Pillai"),
    ("WH-INS-037", "Arjun Malhotra"),
    ("WH-INS-041", "Sneha Kulkarni"),
    ("WH-INS-048", "Imran Qureshi"),
    ("WH-INS-053", "Tanvi Bhattacharya"),
    ("WH-INS-060", "Harpreet Sandhu"),
)


def stable_index(key: str, modulo: int) -> int:
    """Deterministic index (Python's str hash is salted per process)."""
    return zlib.crc32(key.encode("utf-8")) % modulo


def parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def d(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value else "not recorded"


def inr(paise: int) -> str:
    """Format paise as INR with Indian digit grouping, e.g. INR 1,29,999.00."""
    rupees, frac = divmod(int(paise), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"INR {digits}.{frac:02d}"


def yes_no(flag: Any) -> str:
    return "Yes" if bool(flag) else "No"


@dataclass
class ReturnContext:
    row: dict[str, Any]
    inspections: list[dict[str, Any]] = field(default_factory=list)
    refunds: list[dict[str, Any]] = field(default_factory=list)
    cases: list[dict[str, Any]] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        return self.row[key]

    @property
    def return_id(self) -> str:
        return self.row["return_id"]

    @property
    def category(self) -> str:
        return self.row["category"]

    @property
    def delivery(self) -> datetime | None:
        return parse_dt(self.row["delivery_date"])

    @property
    def requested(self) -> datetime:
        return parse_dt(self.row["request_date"])

    @property
    def received(self) -> datetime | None:
        return parse_dt(self.row["received_date"])

    @property
    def ordered(self) -> datetime:
        return parse_dt(self.row["order_date"])

    @property
    def days_after_delivery(self) -> int | None:
        if self.delivery is None:
            return None
        return (self.requested - self.delivery).days

    @property
    def window_days(self) -> int:
        return RETURN_WINDOW_DAYS[self.category]

    @property
    def within_window(self) -> bool:
        days = self.days_after_delivery
        return days is not None and days <= self.window_days

    @property
    def price(self) -> str:
        return inr(self.row["unit_price"])

    @property
    def product_label(self) -> str:
        """Readable product reference; scenario products carry real catalogue names."""
        return f"{self.row['product_name']} (product {self.row['product_id']})"

    @property
    def completed_refund(self) -> dict[str, Any] | None:
        for refund in self.refunds:
            if refund["refund_status"] == "completed":
                return refund
        return None

    def inspector_for(self, inspection: dict[str, Any]) -> tuple[str, str]:
        return INSPECTORS[stable_index(f"insp-{inspection['inspection_id']}", len(INSPECTORS))]

    @property
    def site(self) -> str:
        return INSPECTION_SITES[stable_index(f"site-{self.return_id}", len(INSPECTION_SITES))]


class ShopSphereData:
    def __init__(self, db_path: Path) -> None:
        if not db_path.exists():
            raise FileNotFoundError(
                f"{db_path} not found. Run `python scripts/load_database.py` first."
            )
        self.conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        self.returns = self._load_returns()
        self.products = {r["product_id"]: dict(r) for r in self.conn.execute("SELECT * FROM products")}
        self.suppliers = {r["supplier_id"]: dict(r) for r in self.conn.execute("SELECT * FROM suppliers")}

    def _load_returns(self) -> dict[str, ReturnContext]:
        query = """
            SELECT r.return_id, r.order_item_id, r.request_date, r.return_reason, r.customer_description,
                   r.requested_resolution, r.return_status, r.received_date,
                   oi.order_id, oi.product_id, oi.purchased_serial_number, oi.unit_price, oi.quantity,
                   o.customer_id, o.order_date,
                   c.customer_name, c.email AS customer_email,
                   p.product_name, p.category, p.brand, p.warranty_months, p.serial_tracked, p.supplier_id,
                   d.delivery_id, d.dispatch_date, d.delivery_date, d.delivery_status, d.delivery_issue
            FROM returns r
            JOIN order_items oi ON oi.order_item_id = r.order_item_id
            JOIN orders o ON o.order_id = oi.order_id
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN products p ON p.product_id = oi.product_id
            LEFT JOIN deliveries d ON d.order_id = oi.order_id
            ORDER BY CAST(SUBSTR(r.return_id, 2) AS INTEGER)
        """
        contexts = {row["return_id"]: ReturnContext(dict(row)) for row in self.conn.execute(query)}
        grouped: dict[str, defaultdict] = {
            "inspections": defaultdict(list),
            "refunds": defaultdict(list),
            "investigation_cases": defaultdict(list),
        }
        order_by = {"inspections": "inspection_id", "refunds": "refund_id", "investigation_cases": "case_id"}
        for table, bucket in grouped.items():
            for row in self.conn.execute(f"SELECT * FROM {table} ORDER BY {order_by[table]}"):
                bucket[row["return_id"]].append(dict(row))
        for return_id, ctx in contexts.items():
            ctx.inspections = grouped["inspections"][return_id]
            ctx.refunds = grouped["refunds"][return_id]
            ctx.cases = grouped["investigation_cases"][return_id]
        return contexts

    def get(self, return_id: str) -> ReturnContext:
        return self.returns[return_id]

    def bulk(self) -> list[ReturnContext]:
        return [ctx for rid, ctx in self.returns.items() if rid not in SCENARIO_IDS]

    def returns_for_products(self, product_ids: set[str]) -> list[ReturnContext]:
        return [ctx for ctx in self.returns.values() if ctx["product_id"] in product_ids]
