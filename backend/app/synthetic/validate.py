"""Validation rules for generated structured data."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import RefundStatus
from app.models.tables import (
    Delivery,
    Inspection,
    Order,
    OrderItem,
    Refund,
    Return,
)
from app.synthetic.constants import RESERVED_RETURN_IDS, VOLUMES
from app.synthetic.scenarios import scenario_profiles


@dataclass
class ValidationReport:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def validate_loaded_database(session: Session) -> ValidationReport:
    report = ValidationReport()
    _validate_counts(session, report)
    _validate_reserved_returns(session, report)
    _validate_scenario_rules(session, report)
    _validate_refund_duplicates(session, report)
    _validate_date_ordering(session, report)
    return report


def _validate_counts(session: Session, report: ValidationReport) -> None:
    expected = {
        "customers": VOLUMES.customers,
        "suppliers": VOLUMES.suppliers,
        "products": VOLUMES.products + len(scenario_profiles()),
        "orders": VOLUMES.orders,
        "order_items": VOLUMES.order_items,
        "deliveries": VOLUMES.deliveries,
        "returns": VOLUMES.returns,
        "inspections": VOLUMES.inspections,
        "refunds": VOLUMES.refunds,
        "investigation_cases": VOLUMES.investigation_cases,
        "recovery_options": VOLUMES.recovery_options,
        "recovery_tasks": VOLUMES.recovery_tasks,
    }
    for table, count in expected.items():
        actual = session.execute(select(func.count()).select_from(_table_model(table))).scalar_one()
        if actual != count:
            report.add_error(f"{table}: expected {count} rows, found {actual}")


def _table_model(name: str):
    from app.models.tables import (
        Customer,
        InvestigationCase,
        OrderItem,
        Product,
        RecoveryOption,
        RecoveryTask,
        Supplier,
    )

    mapping = {
        "customers": Customer,
        "suppliers": Supplier,
        "products": Product,
        "orders": Order,
        "order_items": OrderItem,
        "deliveries": Delivery,
        "returns": Return,
        "inspections": Inspection,
        "refunds": Refund,
        "investigation_cases": InvestigationCase,
        "recovery_options": RecoveryOption,
        "recovery_tasks": RecoveryTask,
    }
    return mapping[name]


def _validate_reserved_returns(session: Session, report: ValidationReport) -> None:
    rows = session.execute(select(Return.return_id)).scalars().all()
    present = set(rows)
    for return_id in RESERVED_RETURN_IDS:
        if return_id not in present:
            report.add_error(f"Reserved return {return_id} is missing.")


def _validate_scenario_rules(session: Session, report: ValidationReport) -> None:
    profiles = scenario_profiles()

    r102_item = _return_order_item(session, "R102")
    if r102_item and r102_item.purchased_serial_number != "HP9081":
        report.add_error("R102 purchased serial must be HP9081.")

    r102_inspection = session.execute(
        select(Inspection).where(Inspection.return_id == "R102")
    ).scalar_one_or_none()
    if r102_inspection is None:
        report.add_error("R102 must have an inspection.")
    elif r102_inspection.returned_serial_number != "HP9012":
        report.add_error("R102 returned serial in inspection must be HP9012.")

    r106_completed = session.execute(
        select(func.count())
        .select_from(Refund)
        .where(Refund.return_id == "R106", Refund.refund_status == RefundStatus.COMPLETED)
    ).scalar_one()
    if r106_completed != 1:
        report.add_error("R106 must have exactly one completed refund.")

    r110_count = session.execute(
        select(func.count()).select_from(Inspection).where(Inspection.return_id == "R110")
    ).scalar_one()
    if r110_count < 2:
        report.add_error("R110 must have at least two inspections.")

    r113_count = session.execute(
        select(func.count()).select_from(Inspection).where(Inspection.return_id == "R113")
    ).scalar_one()
    if r113_count != 0:
        report.add_error("R113 must not have inspection records.")

    from app.models.tables import RecoveryOption

    r108_options = session.execute(
        select(func.count()).select_from(RecoveryOption).where(RecoveryOption.return_id == "R108")
    ).scalar_one()
    if r108_options < 3:
        report.add_error("R108 must include multiple recovery options.")

    r115_inspection = session.execute(
        select(Inspection).where(Inspection.return_id == "R115")
    ).scalar_one_or_none()
    if r115_inspection is None or r115_inspection.product_condition != "unsafe":
        report.add_error("R115 inspection must mark product condition unsafe.")

    r103 = session.execute(select(Return).where(Return.return_id == "R103")).scalar_one()
    item = session.get(OrderItem, r103.order_item_id)
    order = session.get(Order, item.order_id) if item else None
    delivery = (
        session.execute(select(Delivery).where(Delivery.order_id == order.order_id)).scalar_one_or_none()
        if order
        else None
    )
    if delivery and delivery.delivery_date and r103.request_date:
        days_after_delivery = (r103.request_date - delivery.delivery_date).days
        if days_after_delivery <= 30:
            report.add_error(
                f"R103 must be outside the 30-day electronics return window "
                f"(got {days_after_delivery} days after delivery)."
            )


def _return_order_item(session: Session, return_id: str) -> OrderItem | None:
    return_row = session.execute(select(Return).where(Return.return_id == return_id)).scalar_one_or_none()
    if return_row is None:
        return None
    return session.get(OrderItem, return_row.order_item_id)


def _validate_refund_duplicates(session: Session, report: ValidationReport) -> None:
    completed = session.execute(
        select(Refund.return_id).where(Refund.refund_status == RefundStatus.COMPLETED)
    ).scalars().all()
    counts = Counter(completed)
    for return_id, count in counts.items():
        if count > 1:
            report.add_error(f"Return {return_id} has {count} completed refunds (expected at most 1).")


def _validate_date_ordering(session: Session, report: ValidationReport) -> None:
    deliveries = session.execute(select(Delivery)).scalars().all()
    for delivery in deliveries:
        order = session.get(Order, delivery.order_id)
        if order is None:
            report.add_error(f"Delivery {delivery.delivery_id} references missing order.")
            continue
        if delivery.dispatch_date and delivery.dispatch_date < order.order_date:
            report.add_error(f"Order {order.order_id} dispatch precedes order date.")
        if (
            delivery.dispatch_date
            and delivery.delivery_date
            and delivery.delivery_date < delivery.dispatch_date
        ):
            report.add_error(f"Delivery {delivery.delivery_id} delivery precedes dispatch.")

    returns = session.execute(select(Return)).scalars().all()
    for return_row in returns:
        item = session.get(OrderItem, return_row.order_item_id)
        if item is None:
            report.add_error(f"Return {return_row.return_id} references missing order item.")
            continue
        order = session.get(Order, item.order_id)
        delivery = session.execute(
            select(Delivery).where(Delivery.order_id == order.order_id)
        ).scalar_one_or_none()
        if delivery and delivery.delivery_date and return_row.request_date < delivery.delivery_date:
            report.add_error(
                f"Return {return_row.return_id} requested before delivery completion."
            )
        inspections = session.execute(
            select(Inspection).where(Inspection.return_id == return_row.return_id)
        ).scalars().all()
        for inspection in inspections:
            if return_row.received_date and inspection.inspection_date < return_row.received_date:
                report.add_error(
                    f"Inspection {inspection.inspection_id} for {return_row.return_id} precedes warehouse receipt."
                )
