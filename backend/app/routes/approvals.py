"""Supervisor approval queue."""

from fastapi import APIRouter, Depends, Query

from app.database.session import get_db
from app.security.deps import CurrentUser, require_roles
from app.security.permissions import ACTION_APPROVE_ROLES
from app.services.approvals import list_pending_approvals
from sqlalchemy.orm import Session

router = APIRouter(prefix="/approvals")


@router.get("")
def get_approvals(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_roles(*ACTION_APPROVE_ROLES)),
) -> dict:
    return list_pending_approvals(db, limit=limit)
