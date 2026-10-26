"""Action request APIs (F7 lifecycle)."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import ActionType
from app.models.tables import ActionRequest
from app.schemas.api import ActionApprovalRequest, ActionListResponse, ActionOut, SubmitActionRequest
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import ACTION_APPROVE_ROLES
from app.services.actions import (
    ActionServiceError,
    approve_action,
    execute_action,
    get_action,
    list_actions,
    submit_action,
)

router = APIRouter(prefix="/actions")


def _action_out(action: ActionRequest) -> ActionOut:
    try:
        payload = json.loads(action.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    data = ActionOut.model_validate(action).model_dump()
    data["payload"] = payload
    return ActionOut(**data)


@router.get("", response_model=ActionListResponse)
def get_actions(
    return_id: str | None = Query(None, min_length=3),
    approval_status: str | None = Query(None, alias="status"),
    execution_status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ActionListResponse:
    items = list_actions(
        db,
        return_id=return_id,
        approval_status=approval_status,
        execution_status=execution_status,
        limit=limit,
    )
    return ActionListResponse(items=[_action_out(row) for row in items], total=len(items))


@router.post("", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
def post_action(
    payload: SubmitActionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ActionOut:
    try:
        action_type = ActionType(payload.action_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action_type") from exc
    try:
        action = submit_action(
            db,
            action_type=action_type,
            return_id=payload.return_id,
            payload=payload.payload,
            idempotency_key=payload.idempotency_key,
            actor=user,
            auto_execute=payload.auto_execute,
        )
    except ActionServiceError as exc:
        code = status.HTTP_403_FORBIDDEN if exc.code == "forbidden" else status.HTTP_400_BAD_REQUEST
        if exc.code == "not_found":
            code = status.HTTP_404_NOT_FOUND
        if exc.code in {
            "duplicate_refund",
            "duplicate_refund_pending",
            "duplicate_refund_action_pending",
        }:
            code = status.HTTP_409_CONFLICT
        raise HTTPException(
            status_code=code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return _action_out(action)


@router.get("/{action_id}", response_model=ActionOut)
def get_action_by_id(
    action_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ActionOut:
    action = get_action(db, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return _action_out(action)


@router.post("/{action_id}/approve", response_model=ActionOut)
def post_approve_action(
    action_id: int,
    payload: ActionApprovalRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*ACTION_APPROVE_ROLES)),
) -> ActionOut:
    try:
        action = approve_action(db, action_id, user, approve=payload.approve)
    except ActionServiceError as exc:
        code = status.HTTP_403_FORBIDDEN if exc.code == "forbidden" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _action_out(action)


@router.post("/{action_id}/execute", response_model=ActionOut)
def post_execute_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ActionOut:
    try:
        action = execute_action(db, action_id, user)
    except ActionServiceError as exc:
        code = status.HTTP_403_FORBIDDEN if exc.code == "forbidden" else status.HTTP_400_BAD_REQUEST
        if exc.code == "duplicate_refund":
            code = status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _action_out(action)
