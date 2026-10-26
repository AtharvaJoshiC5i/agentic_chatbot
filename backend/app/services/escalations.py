"""Escalation records with open-row deduplication."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import EscalationStatus
from app.models.tables import Escalation


def create_escalation(
    session: Session,
    *,
    related_entity: str,
    related_id: str,
    escalation_reason: str,
    owner_username: str | None = None,
    commit: bool = True,
) -> Escalation:
    existing = session.execute(
        select(Escalation).where(
            Escalation.related_entity == related_entity,
            Escalation.related_id == related_id,
            Escalation.escalation_reason == escalation_reason,
            Escalation.status == EscalationStatus.OPEN.value,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    row = Escalation(
        related_entity=related_entity,
        related_id=related_id,
        escalation_reason=escalation_reason,
        owner_username=owner_username,
        status=EscalationStatus.OPEN.value,
        created_at=utc_now(),
        resolved_at=None,
    )
    session.add(row)
    if commit:
        session.commit()
        session.refresh(row)
    else:
        session.flush()
    return row


def resolve_escalation(session: Session, escalation_id: int) -> Escalation | None:
    row = session.get(Escalation, escalation_id)
    if row is None:
        return None
    row.status = EscalationStatus.RESOLVED.value
    row.resolved_at = utc_now()
    session.commit()
    session.refresh(row)
    return row
