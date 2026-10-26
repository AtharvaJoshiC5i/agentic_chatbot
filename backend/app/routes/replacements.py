"""Replacement request APIs (analyst submits, supervisor decides)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.api import ReplacementDecisionRequest, ReplacementRequestCreate
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import REPLACEMENT_DECIDE_ROLES, REPLACEMENT_REQUEST_ROLES
from app.services.errors import http_status_for
from app.services.replacements import (
    ReplacementServiceError,
    create_replacement_request,
    decide_replacement,
    list_replacements,
    replacement_to_dict,
)

router = APIRouter(prefix="/replacements")


@router.get("")
def get_replacements(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    rows = list_replacements(db, status=status_filter, limit=limit)
    return {"items": [replacement_to_dict(r) for r in rows], "total": len(rows)}


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def post_replacement_request(
    payload: ReplacementRequestCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*REPLACEMENT_REQUEST_ROLES)),
) -> dict:
    try:
        row = create_replacement_request(db, return_id=payload.return_id.strip().upper(), actor=user)
    except ReplacementServiceError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return replacement_to_dict(row)


@router.post("/{replacement_id}/decision")
def post_replacement_decision(
    replacement_id: int,
    payload: ReplacementDecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*REPLACEMENT_DECIDE_ROLES)),
) -> dict:
    try:
        row = decide_replacement(db, replacement_id=replacement_id, actor=user, approve=payload.approve, reason=payload.reason)
    except ReplacementServiceError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return replacement_to_dict(row)
