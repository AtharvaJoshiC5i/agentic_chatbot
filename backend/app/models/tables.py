"""SQLAlchemy ORM models matching the Alembic-managed database schema."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("email", name="uq_customers_email"),)

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    account_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_status: Mapped[str] = mapped_column(String(32), nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="supplier")


class SystemAlert(Base, CreatedAtMixin):
    __tablename__ = "system_alerts"
    __table_args__ = (
        UniqueConstraint(
            "alert_type",
            "related_entity",
            "related_id",
            "status",
            name="uq_system_alerts_dedup_open",
        ),
        Index("ix_system_alerts_created_at", "created_at"),
        Index("ix_system_alerts_status", "status"),
    )

    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    related_entity: Mapped[str] = mapped_column(String(64), nullable=False)
    related_id: Mapped[str] = mapped_column(String(64), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_order_date", "order_date"),
    )

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    order_status: Mapped[str] = mapped_column(String(32), nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    delivery: Mapped["Delivery | None"] = relationship(back_populates="order", uselist=False)


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)
    warranty_months: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.supplier_id"), nullable=False)
    stock_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    supplier: Mapped[Supplier] = relationship(back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    documents: Mapped[list["DocumentMetadata"]] = relationship(back_populates="product")
    replacement_requests: Mapped[list["ReplacementRequest"]] = relationship(back_populates="product")


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("order_id", name="uq_deliveries_order_id"),)

    delivery_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    dispatch_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_issue: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="delivery")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_product_id", "product_id"),
    )

    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    purchased_serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")
    product_units: Mapped[list["ProductUnit"]] = relationship(back_populates="order_item")
    returns: Mapped[list["Return"]] = relationship(back_populates="order_item")


class ProductUnit(Base):
    __tablename__ = "product_units"
    __table_args__ = (Index("ix_product_units_order_item_id", "order_item_id"),)

    product_unit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.order_item_id"), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False)
    unit_status: Mapped[str] = mapped_column(String(32), nullable=False)

    order_item: Mapped[OrderItem] = relationship(back_populates="product_units")
    inventory_dispositions: Mapped[list["InventoryDisposition"]] = relationship(
        back_populates="product_unit"
    )


class Return(Base):
    __tablename__ = "returns"
    __table_args__ = (
        Index("ix_returns_order_item_id", "order_item_id"),
        Index("ix_returns_request_date", "request_date"),
        Index("ix_returns_return_status", "return_status"),
    )

    return_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.order_item_id"), nullable=False)
    request_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    return_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    return_status: Mapped[str] = mapped_column(String(32), nullable=False)
    received_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order_item: Mapped[OrderItem] = relationship(back_populates="returns")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="return_record")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="return_record")
    investigation_cases: Mapped[list["InvestigationCase"]] = relationship(back_populates="return_record")
    recovery_options: Mapped[list["RecoveryOption"]] = relationship(back_populates="return_record")
    recovery_tasks: Mapped[list["RecoveryTask"]] = relationship(back_populates="return_record")
    events: Mapped[list["ReturnEvent"]] = relationship(back_populates="return_record")
    action_requests: Mapped[list["ActionRequest"]] = relationship(back_populates="return_record")
    documents: Mapped[list["DocumentMetadata"]] = relationship(back_populates="return_record")
    shipment: Mapped["ReturnShipment | None"] = relationship(back_populates="return_record", uselist=False)
    evidence_requests: Mapped[list["EvidenceRequest"]] = relationship(back_populates="return_record")
    decision_passports: Mapped[list["DecisionPassport"]] = relationship(back_populates="return_record")
    replacement_requests: Mapped[list["ReplacementRequest"]] = relationship(back_populates="return_record")
    warranty_claims: Mapped[list["WarrantyClaim"]] = relationship(back_populates="return_record")
    inventory_dispositions: Mapped[list["InventoryDisposition"]] = relationship(back_populates="return_record")
    warehouse_verdicts: Mapped[list["WarehouseVerdict"]] = relationship(back_populates="return_record")
    customer_notifications: Mapped[list["CustomerNotification"]] = relationship(back_populates="return_record")


class ActionRequest(Base, CreatedAtMixin):
    __tablename__ = "action_requests"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_action_requests_idempotency_key"),
        Index("ix_action_requests_execution_status", "execution_status"),
        Index("ix_action_requests_return_id", "return_id"),
    )

    action_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str | None] = mapped_column(ForeignKey("returns.return_id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    approval_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_record: Mapped[Return | None] = relationship(back_populates="action_requests")


class DocumentMetadata(Base, CreatedAtMixin):
    __tablename__ = "document_metadata"
    __table_args__ = (
        Index("ix_document_metadata_document_type", "document_type"),
        Index("ix_document_metadata_product_id", "product_id"),
        Index("ix_document_metadata_return_id", "return_id"),
    )

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    return_id: Mapped[str | None] = mapped_column(ForeignKey("returns.return_id"), nullable=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.product_id"), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")

    return_record: Mapped[Return | None] = relationship(back_populates="documents")
    product: Mapped[Product | None] = relationship(back_populates="documents")


class Inspection(Base):
    __tablename__ = "inspections"
    __table_args__ = (Index("ix_inspections_return_id", "return_id"),)

    inspection_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_condition: Mapped[str] = mapped_column(String(32), nullable=False)
    accessories_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    defect_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    inspection_result: Mapped[str] = mapped_column(String(32), nullable=False)
    inspector_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="inspections")


class InvestigationCase(Base, CreatedAtMixin):
    __tablename__ = "investigation_cases"
    __table_args__ = (
        Index("ix_investigation_cases_case_status", "case_status"),
        Index("ix_investigation_cases_due_date", "due_date"),
        Index("ix_investigation_cases_return_id", "return_id"),
    )

    case_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="investigation_cases")
    notes: Mapped[list["CaseNote"]] = relationship(back_populates="case")


class RecoveryOption(Base):
    __tablename__ = "recovery_options"
    __table_args__ = (Index("ix_recovery_options_return_id", "return_id"),)

    option_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    recovery_method: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_revenue: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    handling_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    other_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_net_recovery: Mapped[int] = mapped_column(Integer, nullable=False)
    feasibility_status: Mapped[str] = mapped_column(String(32), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="recovery_options")


class RecoveryTask(Base, CreatedAtMixin):
    __tablename__ = "recovery_tasks"
    __table_args__ = (
        Index("ix_recovery_tasks_return_id", "return_id"),
        Index("ix_recovery_tasks_task_status", "task_status"),
    )

    recovery_task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    recovery_method: Mapped[str] = mapped_column(String(64), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="recovery_tasks")
    inventory_dispositions: Mapped[list["InventoryDisposition"]] = relationship(
        back_populates="recovery_task"
    )


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_refunds_idempotency_key"),
        Index("ix_refunds_approval_status", "approval_status"),
        Index("ix_refunds_return_id", "return_id"),
    )

    refund_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    refund_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refund_status: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    processed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="refunds")


class ReturnEvent(Base):
    __tablename__ = "return_events"
    __table_args__ = (
        Index("ix_return_events_event_timestamp", "event_timestamp"),
        Index("ix_return_events_return_id", "return_id"),
    )

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="events")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_target_entity", "target_entity", "target_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution_result: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_references: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReturnShipment(Base):
    __tablename__ = "return_shipments"
    __table_args__ = (
        UniqueConstraint("return_id", name="uq_return_shipments_return_id"),
        Index("ix_return_shipments_return_id", "return_id"),
    )

    shipment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    pickup_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warehouse_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    receipt_discrepancy: Mapped[str | None] = mapped_column(Text, nullable=True)
    lost_in_transit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    return_record: Mapped[Return] = relationship(back_populates="shipment")


class CaseNote(Base):
    __tablename__ = "case_notes"
    __table_args__ = (Index("ix_case_notes_case_id", "case_id"),)

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("investigation_cases.case_id"), nullable=False)
    author_username: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[InvestigationCase] = relationship(back_populates="notes")


class EvidenceRequest(Base):
    __tablename__ = "evidence_requests"
    __table_args__ = (
        Index("ix_evidence_requests_return_id", "return_id"),
        Index("ix_evidence_requests_status", "status"),
    )

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_cases.case_id"), nullable=True)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="evidence_requests")
    case: Mapped[InvestigationCase | None] = relationship()


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        UniqueConstraint(
            "related_entity",
            "related_id",
            "escalation_reason",
            "status",
            name="uq_escalations_dedup_open",
        ),
        Index("ix_escalations_status", "status"),
    )

    escalation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    related_entity: Mapped[str] = mapped_column(String(64), nullable=False)
    related_id: Mapped[str] = mapped_column(String(64), nullable=False)
    escalation_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class DecisionPassport(Base):
    __tablename__ = "decision_passports"
    __table_args__ = (
        UniqueConstraint("return_id", "version", name="uq_decision_passports_return_version"),
        Index("ix_decision_passports_return_id", "return_id"),
    )

    passport_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_report: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="decision_passports")


class ReplacementRequest(Base):
    __tablename__ = "replacement_requests"
    __table_args__ = (Index("ix_replacement_requests_return_id", "return_id"),)

    replacement_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    replacement_order_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="replacement_requests")
    product: Mapped[Product] = relationship(back_populates="replacement_requests")


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    __table_args__ = (Index("ix_warranty_claims_return_id", "return_id"),)

    claim_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="warranty_claims")


class InventoryDisposition(Base):
    __tablename__ = "inventory_dispositions"
    __table_args__ = (Index("ix_inventory_dispositions_return_id", "return_id"),)

    disposition_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    product_unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_units.product_unit_id"), nullable=True
    )
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    recovery_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_tasks.recovery_task_id"), nullable=True
    )
    actual_proceeds_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_cost_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="inventory_dispositions")
    product_unit: Mapped[ProductUnit | None] = relationship(back_populates="inventory_dispositions")
    recovery_task: Mapped[RecoveryTask | None] = relationship(back_populates="inventory_dispositions")


class WarehouseVerdict(Base):
    __tablename__ = "warehouse_verdicts"
    __table_args__ = (Index("ix_warehouse_verdicts_return_id", "return_id"),)

    verdict_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_cases.case_id"), nullable=True)
    resolution_type: Mapped[str] = mapped_column(String(16), nullable=False)
    feasible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    stock_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(16), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    return_record: Mapped[Return] = relationship(back_populates="warehouse_verdicts")
    case: Mapped[InvestigationCase | None] = relationship()


class CustomerNotification(Base):
    __tablename__ = "customer_notifications"
    __table_args__ = (Index("ix_customer_notifications_return_id", "return_id"),)

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("returns.return_id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    return_record: Mapped[Return] = relationship(back_populates="customer_notifications")
