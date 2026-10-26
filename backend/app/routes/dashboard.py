"""Dashboard summary API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.api import DashboardSummary, WorkspaceDashboardOut
from app.security.deps import CurrentUser, get_current_user
from app.services.dashboard import get_dashboard_summary
from app.services.workspace_dashboard import get_workspace_dashboard

router = APIRouter(prefix="/dashboard", dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return DashboardSummary.model_validate(get_dashboard_summary(db))


@router.get("/workspace", response_model=WorkspaceDashboardOut)
def workspace_dashboard(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> WorkspaceDashboardOut:
    return WorkspaceDashboardOut.model_validate(get_workspace_dashboard(db, user))
