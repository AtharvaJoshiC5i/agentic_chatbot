"""REST API request and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import IssueType, RecoveryMethod


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class ReturnSummary(BaseModel):
    return_id: str
    order_item_id: int
    return_reason: str
    return_status: str
    request_date: datetime
    received_date: datetime | None
    requested_resolution: str

    model_config = {"from_attributes": True}


class ReturnListResponse(BaseModel):
    items: list[ReturnSummary]
    total: int
    limit: int
    offset: int


class ProductSummary(BaseModel):
    product_id: str
    product_name: str
    category: str
    brand: str
    original_price_paise: int = Field(validation_alias="original_price")

    model_config = {"from_attributes": True, "populate_by_name": True}


class OrderItemSummary(BaseModel):
    order_item_id: int
    product_id: str
    quantity: int
    unit_price_paise: int = Field(validation_alias="unit_price")
    purchased_serial_number: str | None

    model_config = {"from_attributes": True, "populate_by_name": True}


class OrderDetail(BaseModel):
    order_id: str
    customer_id: str
    order_date: datetime
    total_amount_paise: int = Field(validation_alias="total_amount")
    order_status: str
    items: list[OrderItemSummary] = Field(default_factory=list)

    model_config = {"from_attributes": True, "populate_by_name": True}


class DeliverySummary(BaseModel):
    delivery_id: str
    dispatch_date: datetime | None
    delivery_date: datetime | None
    delivery_status: str
    delivery_issue: str | None

    model_config = {"from_attributes": True}


class ReturnDetail(ReturnSummary):
    customer_description: str | None
    order: OrderDetail | None = None
    product: ProductSummary | None = None
    delivery: DeliverySummary | None = None


class InspectionOut(BaseModel):
    inspection_id: int
    return_id: str
    inspection_date: datetime
    returned_serial_number: str | None
    product_condition: str
    accessories_complete: bool
    defect_verified: bool
    inspection_result: str
    inspector_notes: str | None

    model_config = {"from_attributes": True}


class RefundOut(BaseModel):
    refund_id: int
    return_id: str
    refund_amount_paise: int = Field(validation_alias="refund_amount")
    refund_status: str
    approval_status: str
    processed_date: datetime | None
    idempotency_key: str

    model_config = {"from_attributes": True, "populate_by_name": True}


class TimelineEventOut(BaseModel):
    event_id: int
    return_id: str
    event_type: str
    event_timestamp: datetime
    description: str
    source_type: str
    source_id: str


class TimelineSyncResponse(BaseModel):
    return_id: str
    events_inserted: int
    total_events: int


class CaseOut(BaseModel):
    case_id: int
    return_id: str
    issue_type: str
    priority: str
    assigned_to: str | None
    case_status: str
    created_at: datetime
    due_date: datetime | None
    resolution_notes: str | None

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseOut]
    total: int


class DashboardSummary(BaseModel):
    total_returns: int
    pending_investigations: int
    refunds_awaiting_approval: int
    actions_awaiting_approval: int = 0
    open_recovery_tasks: int
    estimated_recovery_value_paise: int
    completed_recovery_tasks: int
    returns_investigating: int
    overdue_investigation_cases: int
    open_system_alerts: int = 0
    generated_at: datetime


class CreateCaseRequest(BaseModel):
    return_id: str
    issue_type: IssueType
    priority: str = "medium"


class AssignCaseRequest(BaseModel):
    assigned_to: str


class CaseResolveRequest(BaseModel):
    resolution_notes: str | None = None


class RecordInspectionRequest(BaseModel):
    product_condition: str
    returned_serial_number: str | None = None
    accessories_complete: bool = True
    defect_verified: bool = False
    inspection_result: str
    inspector_notes: str | None = None


class RecoveryTaskPatchRequest(BaseModel):
    assigned_to: str | None = None
    task_status: str | None = None


class RefundListResponse(BaseModel):
    items: list[RefundOut]
    total: int


class RefundRequestCreate(BaseModel):
    return_id: str
    refund_amount_paise: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=128)


class RefundApprovalRequest(BaseModel):
    approve: bool = True
    reason: str | None = None  # required when approve is false


class RecoveryTaskCreate(BaseModel):
    return_id: str
    recovery_method: RecoveryMethod
    assigned_to: str | None = None


class RecoveryTaskOut(BaseModel):
    recovery_task_id: int
    return_id: str
    recovery_method: str
    assigned_to: str | None
    task_status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ActionOut(BaseModel):
    action_id: int
    return_id: str | None
    action_type: str
    requested_by: str
    approval_required: bool
    approval_status: str
    execution_status: str
    created_at: datetime
    executed_at: datetime | None
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class SubmitActionRequest(BaseModel):
    action_type: str
    return_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=128)
    auto_execute: bool = True


class ActionListResponse(BaseModel):
    items: list[ActionOut]
    total: int


class ActionApprovalRequest(BaseModel):
    approve: bool = True


class MessageResponse(BaseModel):
    message: str
    detail: dict[str, Any] | None = None


class WorkspaceQueueItem(BaseModel):
    kind: str
    title: str
    subtitle: str | None = None
    return_id: str | None = None
    workflow_stage: str | None = None
    next_action: str | None = None
    requested_resolution: str | None = None
    inspection_count: int | None = None
    refund_status: str | None = None
    approval_status: str | None = None
    case_id: int | None = None
    recovery_task_id: int | None = None
    action_id: int | None = None
    refund_id: int | None = None
    alert_id: int | None = None
    severity: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    amount_paise: int | None = None
    assigned_to: str | None = None
    overdue: bool | None = None
    approval_kind: str | None = None
    requested_by: str | None = None
    action_type: str | None = None
    status_summary: str | None = None
    # Persona handoff fields (what the previous persona recorded, and whose move it is)
    your_move: bool | None = None
    replacement_id: int | None = None
    notification_id: int | None = None
    warehouse_verdict: dict | str | None = None
    warehouse_notes: str | None = None
    latest_inspection: dict | None = None
    case: dict | None = None
    workflow_timeline: list[dict[str, Any]] = Field(default_factory=list)
    last_activity_at: datetime | None = None
    last_update_summary: str | None = None
    last_update_actor: str | None = None
    last_update_actor_label: str | None = None
    handoff_from_other: bool | None = None
    is_highlighted: bool | None = None


class WorkspaceDashboardSection(BaseModel):
    key: str
    title: str
    items: list[WorkspaceQueueItem]


class WorkspaceDashboardOut(BaseModel):
    persona: str
    generated_at: datetime
    kpis: dict[str, int]
    sections: list[WorkspaceDashboardSection]


class VerdictRequest(BaseModel):
    feasible: bool
    recommendation: str  # "proceed" or "decline"
    notes: str | None = None


class DeclineRequest(BaseModel):
    reason: str


class ReplacementRequestCreate(BaseModel):
    return_id: str


class ReplacementDecisionRequest(BaseModel):
    approve: bool = True
    reason: str | None = None


class NotificationSendRequest(BaseModel):
    subject: str | None = None
    body: str | None = None
