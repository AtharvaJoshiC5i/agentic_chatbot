"""Audit log writer."""

import json

from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType
from app.models.tables import AuditLog
from app.security.deps import CurrentUser


def record_audit(
    session: Session,
    *,
    actor: CurrentUser | None,
    actor_type: ActorType,
    action_type: str,
    target_entity: str,
    target_id: str,
    execution_result: str,
    evidence_references: dict | list | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.username if actor else "system",
        actor_type=actor_type.value,
        action_type=action_type,
        target_entity=target_entity,
        target_id=target_id,
        timestamp=utc_now(),
        execution_result=execution_result,
        evidence_references=json.dumps(evidence_references) if evidence_references else None,
    )
    session.add(entry)
    return entry
