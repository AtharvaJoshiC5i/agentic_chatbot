"""Investigation case operations."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.models.enums import ActorType, CaseStatus, IssueType, SourceType
from app.models.tables import CaseNote, InvestigationCase, Return
from app.security.deps import CurrentUser
from app.services.audit import record_audit
from app.services.case_transitions import ACTIVE_CASE_STATUSES, can_transition
from app.services.return_events import record_return_event
from app.services.return_status import ReturnStatusError, on_case_created, on_case_resolved


class CaseServiceError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def get_active_case(session: Session, return_id: str) -> InvestigationCase | None:
    active_values = {status.value for status in ACTIVE_CASE_STATUSES}
    return session.execute(
        select(InvestigationCase)
        .where(
            InvestigationCase.return_id == return_id,
            InvestigationCase.case_status.in_(active_values),
        )
        .order_by(InvestigationCase.created_at.desc())
    ).scalars().first()


def create_case(
    session: Session,
    *,
    return_id: str,
    issue_type: IssueType,
    priority: str,
    actor: CurrentUser,
    due_in_days: int = 7,
    reuse_active: bool = True,
) -> InvestigationCase:
    if session.get(Return, return_id) is None:
        raise CaseServiceError("Return not found", "not_found")

    existing = get_active_case(session, return_id)
    if existing is not None:
        if reuse_active:
            return existing
        raise CaseServiceError("An active investigation case already exists for this return.", "duplicate_case")

    case = InvestigationCase(
        return_id=return_id,
        issue_type=issue_type.value,
        priority=priority,
        assigned_to=None,
        case_status=CaseStatus.OPEN.value,
        created_at=utc_now(),
        due_date=utc_now() + timedelta(days=due_in_days),
        resolution_notes=None,
    )
    session.add(case)
    session.flush()
    record_return_event(
        session,
        return_id=return_id,
        event_type="investigation_opened",
        description=f"Investigation case {case.case_id} opened ({issue_type.value}).",
        source_type=SourceType.CASE.value,
        source_id=f"{case.case_id}:opened",
        event_timestamp=case.created_at,
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="create_case",
        target_entity="investigation_case",
        target_id=str(case.case_id),
        execution_result="succeeded",
        evidence_references={"return_id": return_id},
    )
    try:
        on_case_created(session, return_id, case.case_id, actor)
    except ReturnStatusError as exc:
        session.rollback()
        raise CaseServiceError(str(exc), exc.code) from exc
    session.commit()
    session.refresh(case)
    return case


def assign_case(
    session: Session,
    case_id: int,
    assigned_to: str,
    actor: CurrentUser,
) -> InvestigationCase:
    case = session.get(InvestigationCase, case_id)
    if case is None:
        raise CaseServiceError("Case not found", "not_found")

    case.assigned_to = assigned_to
    case.case_status = CaseStatus.ASSIGNED.value
    record_return_event(
        session,
        return_id=case.return_id,
        event_type="case_updated",
        description=f"Case {case.case_id} assigned to {assigned_to}.",
        source_type=SourceType.CASE.value,
        source_id=f"{case.case_id}:assigned",
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="assign_case",
        target_entity="investigation_case",
        target_id=str(case.case_id),
        execution_result="succeeded",
        evidence_references={"assigned_to": assigned_to},
    )
    session.commit()
    session.refresh(case)
    return case


def transition_case_status(
    session: Session,
    *,
    case_id: int,
    new_status: CaseStatus,
    actor: CurrentUser,
    resolution_notes: str | None = None,
) -> InvestigationCase:
    case = session.get(InvestigationCase, case_id)
    if case is None:
        raise CaseServiceError("Case not found", "not_found")

    current = CaseStatus(case.case_status)
    if not can_transition(current, new_status):
        raise CaseServiceError(
            f"Cannot transition case from {current.value} to {new_status.value}",
            "invalid_transition",
        )

    case.case_status = new_status.value
    if resolution_notes:
        case.resolution_notes = resolution_notes

    record_return_event(
        session,
        return_id=case.return_id,
        event_type="case_updated",
        description=f"Case {case.case_id} status → {new_status.value}.",
        source_type=SourceType.CASE.value,
        source_id=f"{case.case_id}:status",
    )
    record_audit(
        session,
        actor=actor,
        actor_type=ActorType.USER,
        action_type="update_case_status",
        target_entity="investigation_case",
        target_id=str(case.case_id),
        execution_result="succeeded",
        evidence_references={"new_status": new_status.value},
    )
    if new_status in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
        on_case_resolved(session, case.return_id, case.case_id, actor)
    session.commit()
    session.refresh(case)
    return case


def add_case_note(
    session: Session,
    *,
    case_id: int,
    body: str,
    actor: CurrentUser,
) -> CaseNote:
    case = session.get(InvestigationCase, case_id)
    if case is None:
        raise CaseServiceError("Case not found", "not_found")
    note = CaseNote(
        case_id=case_id,
        author_username=actor.username,
        body=body.strip(),
        created_at=utc_now(),
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return note
