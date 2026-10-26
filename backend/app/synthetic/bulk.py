"""Coherent bulk returns (R116+): one status-driven timeline per return.

Design rules (each fixes a defect of the earlier random generator):

* A return's status decides which records may exist. Nothing is dated after
  ``now``; "requested" returns have no receipt, inspection or refund.
* Inspections follow the stated return reason (a "damaged" claim is inspected
  for damage; a "changed_mind" claim has no defect to verify).
* Investigation cases are planted *together with* the evidence that justifies
  them (a serial_mismatch case has a real serial mismatch, and so on).
* Refunds follow status: completed refunds only on resolved/closed returns;
  open refund requests only on returns still being worked.
* Recovery options respect condition and safety (unsafe -> recycle/dispose).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.synthetic import catalog as cat
from app.synthetic.constants import VOLUMES

SCENARIO_IDS = {f"R{i}" for i in range(101, 116)}

# Days still needed after the request for the timeline to fit before "now".
TAIL_DAYS = {
    "inspecting": 11, "investigating": 11,
    "resolved": 18, "closed": 18, "rejected": 18,
}
EARLY_STATUSES = ("requested", "approved", "pickup_scheduled", "in_transit", "received")
INSPECTED_STATUSES = ("inspecting", "investigating", "resolved", "rejected", "closed")


def _paise(rupees: float) -> int:
    return int(round(rupees * 100))


@dataclass
class Plan:
    status: str
    issue: str | None = None
    reason_choices: tuple[str, ...] | None = None
    categories: tuple[str, ...] | None = None
    tracked: bool = False
    needs_warranty: bool = False
    min_age: int = 0
    max_age: int = 10_000
    oow: bool = False
    unsafe: bool = False
    conflict: bool = False
    serial_mismatch: bool = False
    delivery_issue: bool = False
    history: bool = False
    dup_refund: bool = False
    missing_insp: bool = False
    reject_basis: str | None = None  # "oow" | "not_reproduced"
    # --- resolved while building ---
    entry: dict[str, Any] | None = None
    reason: str = ""
    resolution: str = "refund"
    request_date: datetime | None = None
    received_date: datetime | None = None
    inspection_date: datetime | None = None
    resolution_date: datetime | None = None
    return_id: str = ""
    inspections: list[dict[str, Any]] = field(default_factory=list)


class _Builder:
    def __init__(self, bundle: Any, rng: np.random.Generator, now: datetime, nouns: dict[str, str]) -> None:
        self.b = bundle
        self.rng = rng
        self.now = now
        self.products = {p["product_id"]: p for p in bundle.products}
        self.orders = {o["order_id"]: o for o in bundle.orders}
        self.deliveries = {d["order_id"]: d for d in bundle.deliveries}
        self.items_by_order: dict[str, int] = {}
        for item in bundle.order_items:
            self.items_by_order[item["order_id"]] = self.items_by_order.get(item["order_id"], 0) + 1
        self.noun = nouns

        scenario_items = {r["order_item_id"] for r in bundle.returns}
        self.pool: list[dict[str, Any]] = []
        for item in bundle.order_items:
            if item["order_item_id"] in scenario_items or not item["order_id"].startswith("O0"):
                continue
            order = self.orders[item["order_id"]]
            delivery = self.deliveries[item["order_id"]]
            product = self.products[item["product_id"]]
            age = (now - delivery["delivery_date"]).days
            self.pool.append({"item": item, "order": order, "delivery": delivery, "product": product, "age": age})
        self.order_idx = list(self.rng.permutation(len(self.pool)))
        self.pool = [self.pool[i] for i in self.order_idx]
        self.next_inspection = len(bundle.inspections) + 1
        self.next_refund = len(bundle.refunds) + 1
        self.next_case = len(bundle.investigation_cases) + 1

    # ---------------------------------------------------------------- utils
    def pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def chance(self, p: float) -> bool:
        return bool(self.rng.random() < p)

    def between(self, lo: float, hi: float) -> float:
        return float(self.rng.uniform(lo, hi))

    def at_hour(self, dt: datetime) -> datetime:
        return dt.replace(hour=int(self.rng.integers(9, 18)), minute=int(self.rng.integers(0, 60)), second=0, microsecond=0)

    def reason_for(self, category: str) -> str:
        weights = cat.REASON_WEIGHTS[category]
        names = list(weights)
        probs = np.array([weights[n] for n in names])
        return names[int(self.rng.choice(len(names), p=probs / probs.sum()))]

    # ----------------------------------------------------------- planning
    def make_plans(self) -> list[Plan]:
        total = VOLUMES.returns - len(self.b.returns)
        conflicts = 8
        inspected_target = VOLUMES.inspections - len(self.b.inspections) - conflicts
        fixed = {"requested": 30, "approved": 15, "pickup_scheduled": 15, "in_transit": 14,
                 "investigating": 85, "resolved": 140, "rejected": 40, "closed": 51}
        counts = dict(fixed)
        counts["inspecting"] = inspected_target - sum(counts[s] for s in ("investigating", "resolved", "rejected", "closed"))
        counts["received"] = total - sum(counts.values())
        assert counts["inspecting"] > 0 and counts["received"] > 0, counts

        plans: list[Plan] = []

        def add(n: int, status: str, **kw: Any) -> None:
            for _ in range(n):
                plans.append(Plan(status=status, **kw))

        # R107's account history: two earlier, closed returns on the same customer.
        add(1, "closed", history=True, issue=None, tracked=True, categories=("electronics",), reason_choices=("wrong_product",), serial_mismatch=True, min_age=110)
        add(1, "closed", history=True, issue=None, tracked=True, categories=("electronics",), reason_choices=("not_functioning",), min_age=110)

        specs = [
            ("conflicting_evidence", {"investigating": conflicts}, dict(categories=("electronics", "home_appliances"), reason_choices=("not_functioning", "defective"), conflict=True, min_age=40)),
            ("serial_mismatch", {"investigating": 12}, dict(tracked=True, reason_choices=("not_functioning", "defective", "changed_mind"), serial_mismatch=True, min_age=40)),
            ("product_mismatch", {"investigating": 7}, dict(reason_choices=("wrong_product",), min_age=40)),
            ("safety_concern", {"investigating": 8}, dict(categories=("electronics", "home_appliances"), reason_choices=("defective",), unsafe=True, min_age=40)),
            ("delivery_dispute", {"inspecting": 6, "investigating": 6}, dict(reason_choices=("damaged",), delivery_issue=True, min_age=40)),
            ("policy_exception", {"investigating": 5, "inspecting": 5}, dict(oow=True, reason_choices=("changed_mind", "not_as_described", "other"), min_age=75)),
            ("warranty_review", {"investigating": 6}, dict(needs_warranty=True, oow=True, categories=("electronics", "home_appliances"), reason_choices=("defective", "not_functioning"), min_age=140)),
            ("duplicate_refund", {"resolved": 6}, dict(dup_refund=True, categories=("electronics", "home_appliances", "accessories"), reason_choices=("defective", "damaged", "not_functioning"), min_age=40)),
            ("missing_inspection", {"received": 9}, dict(missing_insp=True, min_age=30, max_age=60)),
            ("data_correction", {"investigating": 3}, dict(categories=("electronics", "home_appliances"), reason_choices=("size_color_incorrect",), min_age=40)),
            ("general", {"investigating": 8, "resolved": 4}, dict(min_age=40)),
        ]
        for issue, by_status, kw in specs:
            for status, n in by_status.items():
                add(n, status, issue=issue, **kw)

        for basis, n in (("oow", 28), ("not_reproduced", 12)):
            kw: dict[str, Any] = dict(reject_basis=basis)
            if basis == "oow":
                kw.update(oow=True, reason_choices=("changed_mind",), min_age=75)
            else:
                kw.update(categories=("electronics", "home_appliances", "accessories"), reason_choices=("defective", "not_functioning"), min_age=40)
            add(n, "rejected", **kw)

        used: dict[str, int] = {}
        for plan in plans:
            used[plan.status] = used.get(plan.status, 0) + 1
        for status, target in counts.items():
            rest = target - used.get(status, 0)
            assert rest >= 0, (status, target, used)
            if status in EARLY_STATUSES:
                add(rest, status, min_age=16, max_age=32)
            else:
                add(rest, status, min_age=25)
        # a few early returns arrive late in the window (older deliveries)
        for plan in plans:
            if plan.status in EARLY_STATUSES and not plan.missing_insp and self.chance(0.12):
                plan.min_age, plan.max_age = 33, 60
        assert len(plans) == total, (len(plans), total)
        return plans

    def take_entry(self, plan: Plan) -> dict[str, Any]:
        for index, entry in enumerate(self.pool):
            product = entry["product"]
            if not (plan.min_age <= entry["age"] <= plan.max_age):
                continue
            if plan.categories and product["category"] not in plan.categories:
                continue
            if plan.tracked and not (product["serial_tracked"] and entry["item"]["purchased_serial_number"] and entry["item"]["quantity"] == 1):
                continue
            if plan.needs_warranty and product["warranty_months"] < 12:
                continue
            if plan.history and entry["order"]["customer_id"] == "C00107":
                continue
            return self.pool.pop(index)
        raise RuntimeError(f"No catalogue item satisfies plan constraints: {plan}")

    # -------------------------------------------------------------- dates
    def set_dates(self, plan: Plan) -> None:
        entry = plan.entry
        assert entry is not None
        age = entry["age"]
        delivery = entry["delivery"]["delivery_date"]
        category = entry["product"]["category"]
        window = cat.RETURN_WINDOW[category]
        status = plan.status

        if status in EARLY_STATUSES:
            if status == "requested":
                k = self.between(0.3, 4)
            elif status == "approved":
                k = self.between(2, 6)
            elif status == "pickup_scheduled":
                k = self.between(3, 8)
            elif status == "in_transit":
                k = self.between(4, 10)
            elif plan.missing_insp:
                k = self.between(10, 24)
            else:
                k = self.between(7, 14)
            request = self.now - timedelta(days=k)
            plan.request_date = request
            if status == "received":
                plan.received_date = request + timedelta(days=self.between(2, 4))
            return

        tail = TAIL_DAYS[status]
        cap = max(1, age - tail - 1)
        if plan.oow:
            low = window + 3
            high = min(cap, window + 45)
            if plan.needs_warranty:
                high = min(cap, plan.entry["product"]["warranty_months"] * 30 - 20)
                low = window + 10
            offset = int(self.rng.integers(low, max(low + 1, high + 1)))
        elif plan.history:
            offset = int(self.rng.integers(2, window))
        elif plan.issue is None and self.chance(0.07) and cap > window + 3:
            offset = int(self.rng.integers(window + 2, min(cap, window + 30) + 1))
        else:
            offset = int(self.rng.integers(1, min(window, cap) + 1))
        offset = min(offset, cap)
        request = delivery + timedelta(days=offset, hours=int(self.rng.integers(0, 6)))
        received = request + timedelta(days=int(self.rng.integers(2, 6)), hours=int(self.rng.integers(0, 4)))
        plan.request_date, plan.received_date = request, received
        plan.inspection_date = received + timedelta(days=int(self.rng.integers(1, 3)), hours=int(self.rng.integers(0, 5)))
        if status in ("resolved", "closed", "rejected"):
            plan.resolution_date = plan.inspection_date + timedelta(days=int(self.rng.integers(1, 5)), hours=int(self.rng.integers(0, 5)))

    # --------------------------------------------------------- inspections
    def build_inspections(self, plan: Plan) -> None:
        if plan.status not in INSPECTED_STATUSES:
            return
        entry = plan.entry
        assert entry is not None
        category = entry["product"]["category"]
        item = entry["item"]
        purchased = item["purchased_serial_number"]
        reason = plan.reason
        date = plan.inspection_date
        assert date is not None and date <= self.now, (plan.reason, plan.status, date)

        serial = purchased
        if plan.serial_mismatch and purchased:
            serial = f"SN{int(purchased[2:]) + 7_000_000:06d}"

        condition, verified, result = "open_box", False, "inconclusive"
        accessories = True
        note = ""
        detail = lambda bank: self.pick(bank[category])  # noqa: E731

        if plan.status == "inspecting":
            result = "pending"
            condition = "damaged" if reason == "damaged" else "defective" if reason in ("defective", "not_functioning") else "open_box"
            note = "Inspection in progress; bench testing scheduled."
        elif plan.unsafe:
            condition, verified, result = "unsafe", True, "pass"
            note = self.pick(cat.UNSAFE_DETAIL[category])
        elif plan.serial_mismatch:
            condition = "defective" if reason in ("defective", "not_functioning") else "open_box"
            note = f"Returned unit serial {serial} does not match purchase record {purchased}. Additional verification required."
        elif reason == "wrong_product":
            condition = "new"
            note = "Returned item SKU label does not match the ordered product. Additional verification required."
        elif plan.issue == "data_correction":
            condition = "new"
            note = f"Return reason '{reason}' does not fit the ordered item (category {category}); record needs correction."
        elif reason == "damaged":
            condition = "damaged"
            if self.chance(0.88):
                verified, result = True, "pass"
                note = f"Physical damage confirmed: {detail(cat.DAMAGE_DETAIL)}. Consistent with the customer report."
            else:
                note = "Cosmetic marks only; damage reported by the customer could not be confirmed."
        elif reason in ("defective", "not_functioning"):
            condition = "defective"
            if plan.reject_basis == "not_reproduced" or not self.chance(0.78):
                condition = "open_box"
                result = "fail" if self.chance(0.55) else "inconclusive"
                note = "Bench test for 60 minutes could not reproduce the reported fault."
            else:
                verified, result = True, "pass"
                note = f"Fault reproduced: {detail(cat.FAULT_DETAIL)}."
        elif reason == "missing_accessories":
            condition, accessories = "open_box", False
            note = f"Accessories incomplete: {cat.MISSING_ITEMS[category]} not in the box. Main unit works normally."
        elif reason == "not_as_described":
            condition = self.pick(["like_new", "open_box"])
            note = "Item matches the product specification; no defect found. Listing discrepancy referred to the analyst."
        elif reason == "size_color_incorrect":
            condition = "new"
            note = "Item unworn with tags attached; size and colour recorded from the label for the analyst."
        elif reason == "changed_mind":
            condition = self.pick(["new", "like_new", "like_new", "open_box"])
            note = "Item returned unused or lightly used. No defect claimed."
        else:
            condition = self.pick(["like_new", "open_box"])
            note = "Item received and graded. Reason recorded as other."

        if category == "electronics" and condition == "defective" and verified and self.chance(0.06):
            condition = "for_parts"
            note += " Not economically repairable; graded for parts."

        rows = [
            {
                "inspection_date": date,
                "returned_serial_number": serial,
                "product_condition": condition,
                "accessories_complete": accessories,
                "defect_verified": verified,
                "inspection_result": result,
                "inspector_notes": note,
            }
        ]
        if plan.conflict:
            rows[0].update(
                product_condition="defective", defect_verified=True, inspection_result="pass",
                inspector_notes=f"Initial inspection verified the reported fault: {detail(cat.FAULT_DETAIL)}.",
            )
            rows.append(
                {
                    **rows[0],
                    "inspection_date": date + timedelta(hours=6),
                    "defect_verified": False,
                    "inspection_result": "fail",
                    "inspector_notes": "Second technician could not reproduce the fault; findings conflict with the first inspection.",
                }
            )
        plan.inspections = rows

    # ------------------------------------------------------------ text
    def description(self, plan: Plan) -> str:
        entry = plan.entry
        assert entry is not None
        category = entry["product"]["category"]
        noun = self.noun.get(entry["product"]["product_id"], "item")
        reason = plan.reason
        if reason == "damaged":
            return self.pick([f"The {noun} arrived with {self.pick(cat.DAMAGE_DETAIL[category])}.", f"Received my {noun} damaged: {self.pick(cat.DAMAGE_DETAIL[category])}."])
        if reason == "not_functioning":
            return f"My {noun} stopped working after a few days: {self.pick(cat.FAULT_DETAIL[category])}."
        if reason == "defective":
            return f"The {noun} has a fault: {self.pick(cat.FAULT_DETAIL[category])}."
        if reason == "wrong_product":
            return f"I received a different item from the {noun} I ordered."
        if reason == "size_color_incorrect":
            return f"The size or colour of the {noun} is not what I selected at checkout."
        if reason == "missing_accessories":
            return f"The box for the {noun} was missing {cat.MISSING_ITEMS[category]}."
        if reason == "changed_mind":
            return f"I no longer need the {noun}. It is unused and in the original packaging."
        if reason == "not_as_described":
            return f"The {noun} does not match the listing: {cat.MISMATCH_DETAIL[category]}."
        return self.pick(cat.OTHER_TEXT)

    # ---------------------------------------------------------------- main
    def run(self) -> None:
        plans = self.make_plans()
        # Constrained plans pick items first so flexible ones do not exhaust them.
        constrained = sorted(plans, key=lambda p: (p.issue is None and not p.history and p.reject_basis is None, -p.min_age))
        for plan in constrained:
            plan.entry = self.take_entry(plan)
            category = plan.entry["product"]["category"]
            plan.reason = self.pick(plan.reason_choices) if plan.reason_choices else self.reason_for(category)
            if plan.status == "rejected" and plan.reject_basis is None:
                plan.reason = "changed_mind"
        # resolution preference (kept mostly refunds so refund coverage matches the ledger)
        for plan in plans:
            roll = self.rng.random()
            plan.resolution = "refund" if roll < 0.91 else "store_credit" if roll < 0.95 else "replacement" if roll < 0.98 else "repair"
            if plan.issue == "duplicate_refund" or plan.history:
                plan.resolution = "refund"
        for plan in plans:
            self.set_dates(plan)
            self.build_inspections(plan)

        order = list(self.rng.permutation(len(plans)))
        plans = [plans[i] for i in order]
        for offset, plan in enumerate(plans):
            plan.return_id = f"R{116 + offset}"

        self.write_returns(plans)
        self.write_inspections(plans)
        self.write_deliveries(plans)
        self.write_refunds(plans)
        self.write_cases(plans)
        self.write_recovery(plans)
        self.write_status_effects(plans)

    # ------------------------------------------------------------- writers
    def write_returns(self, plans: list[Plan]) -> None:
        for plan in plans:
            entry = plan.entry
            assert entry is not None
            assert plan.request_date is not None and plan.request_date <= self.now
            assert plan.request_date > entry["delivery"]["delivery_date"], plan
            if plan.history:
                entry["order"]["customer_id"] = "C00107"
            self.b.returns.append(
                {
                    "return_id": plan.return_id,
                    "order_item_id": entry["item"]["order_item_id"],
                    "request_date": plan.request_date,
                    "return_reason": plan.reason,
                    "customer_description": self.description(plan),
                    "requested_resolution": plan.resolution,
                    "return_status": plan.status,
                    "received_date": plan.received_date,
                }
            )

    def write_inspections(self, plans: list[Plan]) -> None:
        for plan in sorted(plans, key=lambda p: int(p.return_id[1:])):
            for row in plan.inspections:
                self.b.inspections.append({"inspection_id": self.next_inspection, "return_id": plan.return_id, **row})
                self.next_inspection += 1

    def write_deliveries(self, plans: list[Plan]) -> None:
        for plan in plans:
            delivery = plan.entry["delivery"]
            if delivery["delivery_issue"]:
                continue
            if plan.delivery_issue or (plan.reason == "damaged" and self.chance(0.35)):
                delivery["delivery_issue"] = self.pick(cat.DELIVERY_ISSUES_DAMAGE)
        returned_orders = {p.entry["order"]["order_id"] for p in plans}
        quiet = [d for d in self.b.deliveries if d["order_id"] not in returned_orders and d["order_id"].startswith("O0") and not d["delivery_issue"]]
        for index in self.rng.permutation(len(quiet))[:20]:
            quiet[int(index)]["delivery_issue"] = self.pick(cat.DELIVERY_ISSUES_OTHER)

    def write_refunds(self, plans: list[Plan]) -> None:
        target = VOLUMES.refunds - len(self.b.refunds)
        completed = [p for p in plans if p.status in ("resolved", "closed") and p.resolution in ("refund", "store_credit")]
        dup = [p for p in completed if p.dup_refund]
        working = [p for p in plans if p.status in ("investigating", "inspecting") and p.resolution in ("refund", "store_credit") and not p.history]
        rejected = [p for p in plans if p.status == "rejected" and p.resolution == "refund"]
        pending_needed = target - len(completed) - len(dup)
        assert pending_needed >= 0, (target, len(completed), len(dup))
        order = list(self.rng.permutation(len(working)))
        pending = [working[i] for i in order[:pending_needed]]
        shortfall = pending_needed - len(pending)
        cancelled = rejected[:shortfall] if shortfall > 0 else []
        assert shortfall <= len(cancelled), f"Cannot reach {target} refunds"

        def add(plan: Plan, status: str, approval: str, processed: datetime | None, key: str) -> None:
            item = plan.entry["item"]
            self.b.refunds.append(
                {
                    "refund_id": self.next_refund,
                    "return_id": plan.return_id,
                    "refund_amount": item["unit_price"] * item["quantity"],
                    "refund_status": status,
                    "approval_status": approval,
                    "processed_date": processed,
                    "idempotency_key": f"refund-{plan.return_id}-{key}{self.next_refund}",
                }
            )
            self.next_refund += 1

        for plan in sorted(completed, key=lambda p: int(p.return_id[1:])):
            processed = plan.resolution_date + timedelta(days=int(self.rng.integers(0, 3)))
            assert processed <= self.now, plan.return_id
            add(plan, "completed", "approved", processed, "")
            if plan.dup_refund:
                add(plan, "requested", "pending", None, "dup-")
        for plan in sorted(pending, key=lambda p: int(p.return_id[1:])):
            add(plan, "requested", "pending", None, "")
        for plan in sorted(cancelled, key=lambda p: int(p.return_id[1:])):
            add(plan, "cancelled", "rejected", None, "")

    def write_cases(self, plans: list[Plan]) -> None:
        priorities = {"safety_concern": "critical", "serial_mismatch": "high", "conflicting_evidence": "high",
                      "duplicate_refund": "high", "delivery_dispute": "medium", "general": "low", "data_correction": "low"}
        notes = {
            "duplicate_refund": "Second refund request blocked; completed refund confirmed on the ledger.",
            "general": "Reviewed with the customer; no further action required.",
        }
        refunds_by_return = {r["return_id"]: r for r in self.b.refunds if r["refund_status"] == "completed"}
        for plan in sorted((p for p in plans if p.issue), key=lambda p: int(p.return_id[1:])):
            if plan.status in ("resolved", "closed"):
                created = plan.inspection_date + timedelta(hours=int(self.rng.integers(2, 20)))
                status = "resolved" if self.chance(0.6) else "closed"
                resolution = notes.get(plan.issue, "Resolved by returns analyst.")
                if plan.issue == "duplicate_refund":
                    resolution = f"Second refund request blocked; completed refund {refunds_by_return[plan.return_id]['refund_id']} confirmed on the ledger."
                assignee = f"analyst_{int(self.rng.integers(1, 8)):02d}"
            else:
                base = plan.received_date + timedelta(days=3) if plan.missing_insp else plan.inspection_date
                created = base + timedelta(hours=int(self.rng.integers(1, 30)))
                status = self.pick(["open", "open", "assigned", "in_progress", "in_progress", "pending_approval"])
                if plan.issue in ("conflicting_evidence", "safety_concern", "serial_mismatch") and status == "pending_approval":
                    status = "in_progress"
                resolution = None
                assignee = None if status == "open" else f"analyst_{int(self.rng.integers(1, 8)):02d}"
            assert created <= self.now, (plan.return_id, plan.issue, created)
            self.b.investigation_cases.append(
                {
                    "case_id": self.next_case,
                    "return_id": plan.return_id,
                    "issue_type": plan.issue,
                    "priority": priorities.get(plan.issue, "medium"),
                    "assigned_to": assignee,
                    "case_status": status,
                    "created_at": created,
                    "due_date": created + timedelta(days=7 if plan.issue == "general" else 5),
                    "resolution_notes": resolution,
                }
            )
            self.next_case += 1
        assert len(self.b.investigation_cases) == VOLUMES.investigation_cases, len(self.b.investigation_cases)

    # ------------------------------------------------------------ recovery
    def option_rows(self, price: int, category: str, condition: str, verified: bool, accessories: bool) -> list[dict[str, Any]]:
        order = {
            "new": ["resell_new", "open_box_resale", "refurbish_and_resell", "recycle"],
            "like_new": ["resell_new", "open_box_resale", "refurbish_and_resell", "recycle"],
            "open_box": ["open_box_resale", "refurbish_and_resell", "resell_new", "recycle"],
            "damaged": ["repair_and_resell", "refurbish_and_resell", "supplier_return", "recycle"],
            "defective": ["supplier_return", "repair_and_resell", "refurbish_and_resell", "recycle"],
            "unsafe": ["dispose", "recycle", "repair_and_resell", "resell_new"],
            "for_parts": ["recycle", "dispose", "supplier_return", "refurbish_and_resell"],
        }[condition]
        high_value = price >= _paise(50_000)
        rows = []
        for method in order:
            repair = refurb = 0
            if method == "resell_new":
                revenue = int(price * 0.95)
            elif method == "open_box_resale":
                revenue = int(price * self.between(0.68, 0.78))
            elif method == "repair_and_resell":
                revenue = int(price * self.between(0.74, 0.84))
                repair = max(_paise(150), int(price * self.between(0.08, 0.30)))
            elif method == "refurbish_and_resell":
                revenue = int(price * self.between(0.55, 0.68))
                repair = max(_paise(120), int(price * self.between(0.10, 0.22)))
            elif method == "supplier_return":
                revenue = int(price * self.between(0.80, 0.92))
            elif method == "recycle":
                revenue = int(price * self.between(0.01, 0.04))
            else:
                revenue = 0
            handling = _paise(self.between(100, 800)) if method not in ("dispose", "recycle") else _paise(self.between(150, 600))
            other = _paise(self.between(0, 500)) if method not in ("dispose",) else _paise(self.between(100, 300))
            net = revenue - repair - handling - other

            feasible = "feasible"
            if condition == "unsafe":
                feasible = "feasible" if method in ("dispose", "recycle") else "not_feasible"
            elif method == "resell_new" and condition not in ("new", "like_new"):
                feasible = "not_feasible"
            elif method == "open_box_resale" and (condition in ("damaged", "defective", "for_parts") or not accessories):
                feasible = "not_feasible"
            elif method == "supplier_return" and not verified:
                feasible = "not_feasible"
            elif method == "repair_and_resell" and category == "fashion":
                feasible = "not_feasible"
            elif method not in ("dispose", "recycle") and net <= 0:
                feasible = "not_feasible"
            elif high_value and method in ("repair_and_resell", "refurbish_and_resell", "supplier_return"):
                feasible = "requires_approval"
            rows.append({"recovery_method": method, "expected_revenue": revenue, "repair_cost": repair + 0, "handling_cost": handling,
                         "other_cost": other, "expected_net_recovery": net, "feasibility_status": feasible})
        rank = {"feasible": 0, "requires_approval": 1, "not_feasible": 2}
        return sorted(rows, key=lambda r: (rank[r["feasibility_status"]], -r["expected_net_recovery"]))

    def write_recovery(self, plans: list[Plan]) -> None:
        def add(return_id: str, row: dict[str, Any]) -> None:
            self.b.recovery_options.append({"option_id": len(self.b.recovery_options) + 1, "return_id": return_id, **row})

        # Hand-built scenarios (kept from the original design).
        laptop = next(p for p in self.b.products if p["product_id"] == "P_R108")["original_price"]
        for method, revenue, repair, handling, other, feas in (
            ("repair_and_resell", int(laptop * 0.82), _paise(4500), _paise(800), _paise(300), "feasible"),
            ("open_box_resale", int(laptop * 0.65), 0, _paise(500), _paise(200), "feasible"),
            ("supplier_return", int(laptop * 0.5), 0, _paise(1200), _paise(100), "requires_approval"),
            ("recycle", _paise(150), 0, _paise(400), 0, "feasible"),
        ):
            add("R108", {"recovery_method": method, "expected_revenue": revenue, "repair_cost": repair, "handling_cost": handling,
                         "other_cost": other, "expected_net_recovery": revenue - repair - handling - other, "feasibility_status": feas})
        appliance = next(p for p in self.b.products if p["product_id"] == "P_R115")["original_price"]
        for method, revenue, handling, other, feas in (
            ("dispose", 0, _paise(600), _paise(200), "feasible"),
            ("recycle", _paise(250), _paise(450), _paise(100), "feasible"),
            ("resell_new", appliance, _paise(100), 0, "not_feasible"),
            ("repair_and_resell", int(appliance * 0.8), _paise(300), _paise(100), "not_feasible"),
        ):
            add("R115", {"recovery_method": method, "expected_revenue": revenue, "repair_cost": 0, "handling_cost": handling,
                         "other_cost": other, "expected_net_recovery": revenue - handling - other, "feasibility_status": feas})

        # Other inspected returns (scenario and bulk) get condition-driven options.
        inspected: list[tuple[str, int, str, str, bool, bool]] = []
        item_by_order_item = {i["order_item_id"]: i for i in self.b.order_items}
        return_by_id = {r["return_id"]: r for r in self.b.returns}
        last_inspection: dict[str, dict[str, Any]] = {}
        for insp in self.b.inspections:
            last_inspection[insp["return_id"]] = insp
        for return_id, insp in last_inspection.items():
            if return_id in ("R108", "R115") or insp["inspection_result"] == "pending":
                continue
            item = item_by_order_item[return_by_id[return_id]["order_item_id"]]
            product = self.products[item["product_id"]]
            inspected.append((return_id, item["unit_price"], product["category"], insp["product_condition"], bool(insp["defect_verified"]), bool(insp["accessories_complete"])))
        inspected.sort(key=lambda r: int(r[0][1:]))

        budget = VOLUMES.recovery_options - len(self.b.recovery_options)
        generated = {r[0]: self.option_rows(r[1], r[2], r[3], r[4], r[5]) for r in inspected}
        counts = {rid: 1 for rid in generated}
        extra = budget - len(generated)
        assert extra >= 0, (budget, len(generated))
        ids = list(generated)
        order = list(self.rng.permutation(len(ids)))
        cursor, guard = 0, 0
        while extra > 0:
            rid = ids[order[cursor % len(ids)]]
            if counts[rid] < len(generated[rid]):
                counts[rid] += 1
                extra -= 1
            cursor += 1
            guard += 1
            assert guard < len(ids) * 6, "Cannot reach recovery option volume"
        for rid in ids:
            for row in generated[rid][: counts[rid]]:
                add(rid, row)
        assert len(self.b.recovery_options) == VOLUMES.recovery_options, len(self.b.recovery_options)

        # Recovery tasks: follow resolved/closed returns, using the best feasible option.
        best: dict[str, str] = {}
        for opt in self.b.recovery_options:
            if opt["feasibility_status"] == "feasible" and opt["return_id"] not in best:
                best[opt["return_id"]] = opt["recovery_method"]
        self.b.recovery_tasks.append(
            {"recovery_task_id": 1, "return_id": "R108", "recovery_method": "repair_and_resell", "assigned_to": "warehouse_mgr_01",
             "task_status": "pending", "created_at": self.now - timedelta(days=2), "completed_at": None}
        )
        done = [p for p in plans if p.status in ("resolved", "closed") and p.return_id in best and p.resolution_date]
        done.sort(key=lambda p: p.resolution_date, reverse=True)
        recent, older = done[:70], done[70:]
        recent_pick = [recent[int(i)] for i in self.rng.permutation(len(recent))]
        older_pick = [older[int(i)] for i in self.rng.permutation(len(older))]
        remaining = VOLUMES.recovery_tasks - len(self.b.recovery_tasks)
        n_completed = 34
        open_statuses = (["pending"] * 25) + (["assigned"] * 20) + (["in_progress"] * 20)
        assert n_completed + len(open_statuses) == remaining, remaining
        plan_status = [(p, "completed") for p in older_pick[:n_completed]]
        plan_status += list(zip(recent_pick[: len(open_statuses)], open_statuses))
        for plan, task_status in plan_status:
            created = min(self.now - timedelta(hours=6), plan.resolution_date + timedelta(days=int(self.rng.integers(1, 4))))
            completed = None
            if task_status == "completed":
                completed = min(self.now - timedelta(hours=2), created + timedelta(days=int(self.rng.integers(2, 9))))
            self.b.recovery_tasks.append(
                {
                    "recovery_task_id": len(self.b.recovery_tasks) + 1,
                    "return_id": plan.return_id,
                    "recovery_method": best[plan.return_id],
                    "assigned_to": None if task_status == "pending" else f"tech_{int(self.rng.integers(1, 6)):02d}",
                    "task_status": task_status,
                    "created_at": created,
                    "completed_at": completed,
                }
            )

    # ------------------------------------------------------ status effects
    def write_status_effects(self, plans: list[Plan]) -> None:
        completed_returns = {r["return_id"] for r in self.b.refunds if r["refund_status"] == "completed"}
        units = {}
        for unit in self.b.product_units:
            units.setdefault(unit["order_item_id"], []).append(unit)
        for plan in plans:
            if plan.return_id not in completed_returns:
                continue
            order = plan.entry["order"]
            single = self.items_by_order[order["order_id"]] == 1
            order["order_status"] = "returned" if single else "partially_returned"
            for unit in units.get(plan.entry["item"]["order_item_id"], []):
                unit["unit_status"] = "returned"


def build_bulk_returns(bundle: Any, rng: np.random.Generator, now: datetime, nouns: dict[str, str]) -> None:
    """Append R116+ returns and all dependent records to ``bundle``."""
    _Builder(bundle, rng, now, nouns).run()
