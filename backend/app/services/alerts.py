"""system_alerts persistence with open-alert deduplication."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import AlertSeverity, AlertStatus, AlertType
from app.models.tables import SystemAlert


@dataclass(frozen=True)
class AlertFinding:
    alert_type: AlertType
    related_entity: str
    related_id: str
    severity: AlertSeverity


def upsert_open_alert(session: Session, finding: AlertFinding) -> SystemAlert:
    existing = session.execute(
        select(SystemAlert).where(
            SystemAlert.alert_type == finding.alert_type.value,
            SystemAlert.related_entity == finding.related_entity,
            SystemAlert.related_id == finding.related_id,
            SystemAlert.status == AlertStatus.OPEN.value,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    row = SystemAlert(
        related_entity=finding.related_entity,
        related_id=finding.related_id,
        alert_type=finding.alert_type.value,
        severity=finding.severity.value,
        status=AlertStatus.OPEN.value,
        created_at=utc_now(),
    )
    session.add(row)
    session.flush()
    return row


def resolve_inactive_open_alerts(session: Session, active_findings: list[AlertFinding]) -> int:
    active_keys = {
        (finding.alert_type.value, finding.related_entity, finding.related_id)
        for finding in active_findings
    }
    resolved = 0
    open_rows = session.execute(
        select(SystemAlert).where(SystemAlert.status == AlertStatus.OPEN.value)
    ).scalars().all()
    for row in open_rows:
        key = (row.alert_type, row.related_entity, row.related_id)
        if key not in active_keys:
            row.status = AlertStatus.RESOLVED.value
            resolved += 1
    return resolved


def list_alerts(
    session: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SystemAlert]:
    query = select(SystemAlert).order_by(SystemAlert.created_at.desc())
    if status:
        query = query.where(SystemAlert.status == status)
    return list(session.execute(query.limit(limit).offset(offset)).scalars().all())


def acknowledge_alert(session: Session, alert_id: int) -> SystemAlert | None:
    row = session.get(SystemAlert, alert_id)
    if row is None:
        return None
    if row.status == AlertStatus.OPEN.value:
        row.status = AlertStatus.ACKNOWLEDGED.value
        session.commit()
        session.refresh(row)
    return row
