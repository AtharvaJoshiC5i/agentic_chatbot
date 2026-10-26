"""Customer notification APIs: the analyst reviews the drafted message and confirms it."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tables import CustomerNotification
from app.schemas.api import NotificationSendRequest
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import NOTIFICATION_SEND_ROLES
from app.services.errors import http_status_for
from app.services.notifications import (
    NotificationError,
    list_notifications,
    notification_to_dict,
    send_notification,
)

router = APIRouter(prefix="/notifications")


@router.get("")
def get_notifications(
    status_filter: str | None = Query(None, alias="status"),
    return_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    rows = list_notifications(db, status=status_filter, return_id=return_id, limit=limit)
    return {"items": [notification_to_dict(r) for r in rows], "total": len(rows)}


@router.get("/{notification_id}")
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    row = db.get(CustomerNotification, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification_to_dict(row)


@router.post("/{notification_id}/send")
def post_send_notification(
    notification_id: int,
    payload: NotificationSendRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*NOTIFICATION_SEND_ROLES)),
) -> dict:
    try:
        row = send_notification(db, notification_id=notification_id, actor=user, subject=payload.subject, body=payload.body)
    except NotificationError as exc:
        raise HTTPException(status_code=http_status_for(exc.code), detail=str(exc)) from exc
    return notification_to_dict(row)
