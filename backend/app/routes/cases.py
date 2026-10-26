"""Investigation case APIs."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import CaseStatus
from app.models.tables import InvestigationCase
from app.schemas.api import AssignCaseRequest, CaseListResponse, CaseOut, CaseResolveRequest, CreateCaseRequest
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.security.permissions import ASSIGN_CASE_ROLES, CASE_RESOLVE_ROLES, WRITE_CASE_ROLES
from app.services.cases import CaseServiceError, assign_case, create_case, transition_case_status

router = APIRouter(prefix="/cases", dependencies=[Depends(get_current_user)])


@router.get("", response_model=CaseListResponse)
def list_cases(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CaseListResponse:
    query = select(InvestigationCase)
    if status_filter:
        query = query.where(InvestigationCase.case_status == status_filter)
    total = db.execute(select(func.count()).select_from(InvestigationCase)).scalar_one()
    rows = db.execute(query.order_by(InvestigationCase.created_at.desc()).limit(limit).offset(offset)).scalars().all()
    return CaseListResponse(items=[CaseOut.model_validate(row) for row in rows], total=int(total))


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db)) -> CaseOut:
    case = db.get(InvestigationCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return CaseOut.model_validate(case)


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def post_case(
    payload: CreateCaseRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*WRITE_CASE_ROLES)),
) -> CaseOut:
    try:
        case = create_case(
            db,
            return_id=payload.return_id,
            issue_type=payload.issue_type,
            priority=payload.priority,
            actor=user,
        )
    except CaseServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.post("/{case_id}/assign", response_model=CaseOut)
def post_assign_case(
    case_id: int,
    payload: AssignCaseRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*ASSIGN_CASE_ROLES)),
) -> CaseOut:
    try:
        case = assign_case(db, case_id, payload.assigned_to, user)
    except CaseServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.post("/{case_id}/resolve", response_model=CaseOut)
def post_resolve_case(
    case_id: int,
    payload: CaseResolveRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*CASE_RESOLVE_ROLES)),
) -> CaseOut:
    try:
        case = transition_case_status(
            db,
            case_id=case_id,
            new_status=CaseStatus.RESOLVED,
            actor=user,
            resolution_notes=payload.resolution_notes,
        )
    except CaseServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.post("/{case_id}/close", response_model=CaseOut)
def post_close_case(
    case_id: int,
    payload: CaseResolveRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_roles(*CASE_RESOLVE_ROLES)),
) -> CaseOut:
    try:
        case = transition_case_status(
            db,
            case_id=case_id,
            new_status=CaseStatus.CLOSED,
            actor=user,
            resolution_notes=payload.resolution_notes,
        )
    except CaseServiceError as exc:
        code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return CaseOut.model_validate(case)
