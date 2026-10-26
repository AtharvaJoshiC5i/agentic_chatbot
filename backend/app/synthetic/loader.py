"""Load synthetic datasets into SQLite."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.tables import (
    ActionRequest,
    AuditLog,
    Customer,
    CustomerNotification,
    Delivery,
    DocumentMetadata,
    Inspection,
    InvestigationCase,
    Order,
    OrderItem,
    Product,
    ProductUnit,
    RecoveryOption,
    RecoveryTask,
    Refund,
    Return,
    ReturnEvent,
    Supplier,
    SystemAlert,
    User,
    WarehouseVerdict,
)
from app.synthetic.generator import SyntheticDataBundle


def clear_structured_data(session: Session) -> None:
    """Delete business data while preserving Alembic version metadata."""
    for model in (
        CustomerNotification,
        WarehouseVerdict,
        ReturnEvent,
        ActionRequest,
        RecoveryTask,
        RecoveryOption,
        InvestigationCase,
        Refund,
        Inspection,
        DocumentMetadata,
        Return,
        ProductUnit,
        OrderItem,
        Delivery,
        Order,
        Product,
        Customer,
        Supplier,
        AuditLog,
        SystemAlert,
        User,
    ):
        session.execute(delete(model))
    session.commit()


def load_bundle(session: Session, bundle: SyntheticDataBundle) -> None:
    """Insert a generated bundle in foreign-key-safe order."""
    clear_structured_data(session)

    session.bulk_insert_mappings(Customer, bundle.customers)
    session.bulk_insert_mappings(Supplier, bundle.suppliers)
    session.bulk_insert_mappings(Product, bundle.products)
    session.bulk_insert_mappings(Order, bundle.orders)
    session.bulk_insert_mappings(OrderItem, bundle.order_items)
    session.bulk_insert_mappings(ProductUnit, bundle.product_units)
    session.bulk_insert_mappings(Delivery, bundle.deliveries)
    session.bulk_insert_mappings(Return, bundle.returns)
    session.bulk_insert_mappings(Inspection, bundle.inspections)
    session.bulk_insert_mappings(Refund, bundle.refunds)
    session.bulk_insert_mappings(InvestigationCase, bundle.investigation_cases)
    session.bulk_insert_mappings(RecoveryOption, bundle.recovery_options)
    session.bulk_insert_mappings(RecoveryTask, bundle.recovery_tasks)
    session.commit()
