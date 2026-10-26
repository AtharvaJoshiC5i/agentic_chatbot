"""Return read APIs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tables import Delivery, Inspection, Order, OrderItem, Product, Return
from app.schemas.api import (
    TimelineSyncResponse,
    DeliverySummary,
    InspectionOut,
    OrderDetail,
    OrderItemSummary,
    ProductSummary,
    RecordInspectionRequest,
    RefundOut,
    ReturnDetail,
    ReturnListResponse,
    ReturnSummary,
    TimelineEventOut,
)
from app.models.enums import InspectionResult, ProductCondition
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import INSPECTION_WRITE_ROLES, RETURN_CLOSE_ROLES
from app.services.queries import get_return_detail, list_returns
from app.services.refundable import calculate_refundable_amount_paise
from app.services.refunds import get_refund_for_return
from app.services.inspections import InspectionServiceError, record_inspection
from app.services.return_events import sync_return_timeline
from app.services.return_status import ReturnStatusError, close_return, receive_return_at_warehouse
from app.services.errors import http_status_for
from app.services.handoff import WorkflowError, decline_return, get_latest_verdict, record_verdict, verdict_to_dict
from app.services.return_workflow import build_return_workflow_snapshot
from app.schemas.api import DeclineRequest, VerdictRequest
from app.security.permissions import DECLINE_ROLES, VERDICT_ROLES
from app.services.timeline import build_return_timeline
from app.models.enums import UserRole

router = APIRouter(prefix="/returns", dependencies=[Depends(get_current_user)])


@router.get("", response_model=ReturnListResponse)
def get_returns(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: CurrentUser = Depends(get_current_user),
) -> ReturnListResponse:
    rows, total = list_returns(db, status=status_filter, limit=limit, offset=offset)
    return ReturnListResponse(
        items=[ReturnSummary.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{return_id}", response_model=ReturnDetail)
def get_return(return_id: str, db: Session = Depends(get_db)) -> ReturnDetail:
    return_row = get_return_detail(db, return_id)
    if return_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")

    item = db.get(OrderItem, return_row.order_item_id)
    order_detail = None
    product_summary = None
    delivery_summary = None
    if item:
        order = db.get(Order, item.order_id)
        product = db.get(Product, item.product_id)
        if product:
            product_summary = ProductSummary.model_validate(product)
        if order:
            items = db.execute(
                select(OrderItem).where(OrderItem.order_id == order.order_id)
            ).scalars().all()
            order_detail = OrderDetail(
                order_id=order.order_id,
                customer_id=order.customer_id,
                order_date=order.order_date,
                total_amount_paise=order.total_amount,
                order_status=order.order_status,
                items=[OrderItemSummary.model_validate(row) for row in items],
            )
            delivery = db.execute(
                select(Delivery).where(Delivery.order_id == order.order_id)
            ).scalar_one_or_none()
            if delivery:
                delivery_summary = DeliverySummary.model_validate(delivery)

    return ReturnDetail(
        return_id=return_row.return_id,
        order_item_id=return_row.order_item_id,
        return_reason=return_row.return_reason,
        return_status=return_row.return_status,
        request_date=return_row.request_date,
        received_date=return_row.received_date,
        requested_resolution=return_row.requested_resolution,
        customer_description=return_row.customer_description,
        order=order_detail,
        product=product_summary,
        delivery=delivery_summary,
    )


@router.get("/{return_id}/timeline", response_model=list[TimelineEventOut])
def get_return_timeline(
    return_id: str,
    db: Session = Depends(get_db),
    sync: bool = Query(True, description="Sync structured records into return_events before read"),
) -> list[TimelineEventOut]:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    events = build_return_timeline(db, return_id, sync=sync)
    return [TimelineEventOut.model_validate(event) for event in events]


@router.post("/{return_id}/timeline/sync", response_model=TimelineSyncResponse)
def post_return_timeline_sync(
    return_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_roles(UserRole.RETURNS_SUPERVISOR)),
) -> TimelineSyncResponse:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    inserted = sync_return_timeline(db, return_id, commit=True)
    total = len(build_return_timeline(db, return_id, sync=False))
    return TimelineSyncResponse(return_id=return_id, events_inserted=inserted, total_events=total)


@router.post("/{return_id}/receive", response_model=ReturnSummary)
def post_receive_return(
    return_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*INSPECTION_WRITE_ROLES)),
) -> ReturnSummary:
    try:
        row = receive_return_at_warehouse(db, return_id, user)
    except ReturnStatusError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return ReturnSummary.model_validate(row)


@router.post("/{return_id}/inspections", response_model=InspectionOut, status_code=status.HTTP_201_CREATED)
def post_return_inspection(
    return_id: str,
    payload: RecordInspectionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*INSPECTION_WRITE_ROLES)),
) -> InspectionOut:
    try:
        product_condition = ProductCondition(payload.product_condition.strip().lower())
        inspection_result = InspectionResult(payload.inspection_result.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid inspection enums") from exc
    try:
        row = record_inspection(
            db,
            return_id=return_id,
            product_condition=product_condition,
            returned_serial_number=payload.returned_serial_number,
            accessories_complete=payload.accessories_complete,
            defect_verified=payload.defect_verified,
            inspection_result=inspection_result,
            inspector_notes=payload.inspector_notes,
            actor=user,
        )
    except InspectionServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        if exc.code == "serial_mismatch":
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail={"code": exc.code, "message": str(exc)}) from exc
    return InspectionOut.model_validate(row)


@router.post("/{return_id}/close", response_model=ReturnSummary)
def post_close_return(
    return_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*RETURN_CLOSE_ROLES)),
) -> ReturnSummary:
    try:
        row = close_return(db, return_id, user)
    except ReturnStatusError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return ReturnSummary.model_validate(row)


@router.get("/{return_id}/inspections", response_model=list[InspectionOut])
def get_return_inspections(return_id: str, db: Session = Depends(get_db)) -> list[InspectionOut]:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    rows = db.execute(select(Inspection).where(Inspection.return_id == return_id)).scalars().all()
    return [InspectionOut.model_validate(row) for row in rows]


@router.get("/{return_id}/refund", response_model=RefundOut | None)
def get_return_refund(return_id: str, db: Session = Depends(get_db)) -> RefundOut | None:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    refund = get_refund_for_return(db, return_id)
    return RefundOut.model_validate(refund) if refund else None


@router.get("/{return_id}/refundable")
def get_return_refundable(return_id: str, db: Session = Depends(get_db)) -> dict[str, int]:
    if db.get(Return, return_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    return calculate_refundable_amount_paise(db, return_id)


@router.get("/{return_id}/workflow")
def get_return_workflow(
    return_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Who has to act next on this return, and everything each persona has already recorded."""
    snap = build_return_workflow_snapshot(db, return_id)
    if snap.get("error") == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    return snap


@router.get("/{return_id}/verdict")
def get_return_verdict(
    return_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> dict | None:
    return verdict_to_dict(get_latest_verdict(db, return_id.strip().upper()))


@router.post("/{return_id}/verdict", status_code=status.HTTP_201_CREATED)
def post_return_verdict(
    return_id: str,
    payload: VerdictRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*VERDICT_ROLES)),
) -> dict:
    """Warehouse: can the customer's refund or replacement be performed? The result goes back to the analyst."""
    try:
        verdict = record_verdict(
            db,
            return_id=return_id.strip().upper(),
            actor=user,
            feasible=payload.feasible,
            recommendation=payload.recommendation,
            notes=payload.notes,
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return verdict_to_dict(verdict)


@router.post("/{return_id}/decline", response_model=ReturnSummary)
def post_decline_return(
    return_id: str,
    payload: DeclineRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*DECLINE_ROLES)),
) -> ReturnSummary:
    """Analyst declines the request (e.g. the warehouse says it cannot be performed); a customer email is drafted."""
    try:
        row = decline_return(db, return_id=return_id.strip().upper(), actor=user, reason=payload.reason)
    except (WorkflowError, ReturnStatusError) as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return ReturnSummary.model_validate(row)
