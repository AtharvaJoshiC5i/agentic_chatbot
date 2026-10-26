"""Warranty claim tracking."""

from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, WarrantyClaimStatus
from app.models.tables import Return, WarrantyClaim
from app.security.deps import CurrentUser
from app.services.audit import record_audit


class WarrantyServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def create_warranty_claim(
    session: Session,
    *,
    return_id: str,
    notes: str | None,
    actor: CurrentUser,
) -> WarrantyClaim:
    if session.get(Return, return_id) is None:
        raise WarrantyServiceError("Return not found", "not_found")

    claim = WarrantyClaim(
        return_id=return_id,
        status=WarrantyClaimStatus.OPEN.value,
        notes=notes,
        created_at=utc_now(),
    )
    session.add(claim)
    session.flush()
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="create_warranty_claim",
        target_entity="warranty_claim",
        target_id=str(claim.claim_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id},
    )
    session.commit()
    session.refresh(claim)
    return claim
