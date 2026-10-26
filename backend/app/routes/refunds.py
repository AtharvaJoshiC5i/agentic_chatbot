"""Refund action APIs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.api import RefundApprovalRequest, RefundListResponse, RefundOut, RefundRequestCreate
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import REFUND_APPROVE_ROLES, REFUND_EXECUTE_ROLES, REFUND_REQUEST_ROLES
from app.services.errors import http_status_for
from app.services.refunds import (
    RefundServiceError,
    approve_refund,
    execute_refund,
    list_refunds,
    request_refund,
)

router = APIRouter(prefix="/refunds")


@router.get("", response_model=RefundListResponse)
def get_refunds(
    status_filter: str | None = Query(None, alias="status"),
    approval_status: str | None = Query(None),
    return_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> RefundListResponse:
    items = list_refunds(
        db,
        status=status_filter,
        approval_status=approval_status,
        return_id=return_id,
        limit=limit,
    )
    return RefundListResponse(items=[RefundOut.model_validate(row) for row in items], total=len(items))


@router.post("/requests", response_model=RefundOut, status_code=status.HTTP_201_CREATED)
def post_refund_request(
    payload: RefundRequestCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*REFUND_REQUEST_ROLES)),
) -> RefundOut:
    try:
        refund = request_refund(
            db,
            return_id=payload.return_id,
            refund_amount_paise=payload.refund_amount_paise,
            idempotency_key=payload.idempotency_key,
            actor=user,
        )
    except RefundServiceError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return RefundOut.model_validate(refund)


@router.post("/{refund_id}/approve", response_model=RefundOut)
def post_approve_refund(
    refund_id: int,
    payload: RefundApprovalRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*REFUND_APPROVE_ROLES)),
) -> RefundOut:
    try:
        refund = approve_refund(db, refund_id, user, approve=payload.approve, reason=payload.reason)
    except RefundServiceError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return RefundOut.model_validate(refund)


@router.post("/{refund_id}/execute", response_model=RefundOut)
def post_execute_refund(
    refund_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*REFUND_EXECUTE_ROLES)),
) -> RefundOut:
    try:
        refund = execute_refund(db, refund_id, user)
    except RefundServiceError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return RefundOut.model_validate(refund)
