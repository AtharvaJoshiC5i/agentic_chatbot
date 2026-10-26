"""Human evidence request tracking."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, EvidenceRequestStatus
from app.models.tables import EvidenceRequest, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit


class EvidenceRequestError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def create_evidence_request(
    session: Session,
    *,
    return_id: str,
    request_type: str,
    description: str,
    actor: CurrentUser,
    case_id: int | None = None,
    due_in_days: int = 5,
) -> EvidenceRequest:
    if session.get(Return, return_id) is None:
        raise EvidenceRequestError("Return not found", "not_found")

    row = EvidenceRequest(
        return_id=return_id,
        case_id=case_id,
        request_type=request_type,
        description=description.strip(),
        status=EvidenceRequestStatus.PENDING.value,
        due_date=utc_now() + timedelta(days=due_in_days),
        created_at=utc_now(),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="create_evidence_request",
        target_entity="evidence_request",
        target_id=str(row.request_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id, "request_type": request_type},
    )
    session.commit()
    session.refresh(row)
    return row
