"""Deterministic investigation API (Phase 8)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.investigation.investigation import run_investigation
from app.schemas.investigation import InvestigationReportOut
from app.security.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/returns", dependencies=[Depends(get_current_user)])


@router.get("/{return_id}/investigation", response_model=InvestigationReportOut)
def get_return_investigation(return_id: str, db: Session = Depends(get_db)) -> InvestigationReportOut:
    report = run_investigation(db, return_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found")
    return InvestigationReportOut.model_validate(report.to_dict())
