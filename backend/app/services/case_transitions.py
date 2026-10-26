"""Permitted investigation case status transitions."""

from app.models.enums import CaseStatus

ACTIVE_CASE_STATUSES = frozenset(
    {
        CaseStatus.OPEN,
        CaseStatus.ASSIGNED,
        CaseStatus.IN_PROGRESS,
        CaseStatus.AWAITING_EVIDENCE,
        CaseStatus.READY_FOR_REVIEW,
        CaseStatus.PENDING_APPROVAL,
    }
)

TERMINAL_CASE_STATUSES = frozenset({CaseStatus.RESOLVED, CaseStatus.CLOSED})

ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.OPEN: frozenset(
        {CaseStatus.ASSIGNED, CaseStatus.IN_PROGRESS, CaseStatus.AWAITING_EVIDENCE, CaseStatus.CLOSED}
    ),
    CaseStatus.ASSIGNED: frozenset(
        {
            CaseStatus.IN_PROGRESS,
            CaseStatus.AWAITING_EVIDENCE,
            CaseStatus.READY_FOR_REVIEW,
            CaseStatus.CLOSED,
        }
    ),
    CaseStatus.IN_PROGRESS: frozenset(
        {
            CaseStatus.AWAITING_EVIDENCE,
            CaseStatus.READY_FOR_REVIEW,
            CaseStatus.PENDING_APPROVAL,
            CaseStatus.RESOLVED,
            CaseStatus.CLOSED,
        }
    ),
    CaseStatus.AWAITING_EVIDENCE: frozenset(
        {CaseStatus.IN_PROGRESS, CaseStatus.READY_FOR_REVIEW, CaseStatus.CLOSED}
    ),
    CaseStatus.READY_FOR_REVIEW: frozenset(
        {CaseStatus.IN_PROGRESS, CaseStatus.PENDING_APPROVAL, CaseStatus.RESOLVED, CaseStatus.CLOSED}
    ),
    CaseStatus.PENDING_APPROVAL: frozenset({CaseStatus.RESOLVED, CaseStatus.CLOSED, CaseStatus.IN_PROGRESS}),
    CaseStatus.RESOLVED: frozenset({CaseStatus.CLOSED, CaseStatus.IN_PROGRESS}),
    CaseStatus.CLOSED: frozenset({CaseStatus.IN_PROGRESS}),
}


def can_transition(current: CaseStatus, new: CaseStatus) -> bool:
    if current == new:
        return True
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    return new in allowed
