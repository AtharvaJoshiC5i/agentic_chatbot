"""Monitoring and system alerts API (F8)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import UserRole
from app.schemas.monitoring import MonitoringRunOut, MonitoringSummaryOut, SystemAlertOut
from app.security.deps import CurrentUser, get_current_user, require_roles
from app.services.alerts import acknowledge_alert, list_alerts
from app.services.monitoring import get_monitoring_summary, run_monitoring_checks

router = APIRouter(prefix="/monitoring", dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=MonitoringSummaryOut)
def monitoring_summary(db: Session = Depends(get_db)) -> MonitoringSummaryOut:
    payload = get_monitoring_summary(db)
    return MonitoringSummaryOut(
        open_alerts=payload["open_alerts"],
        alerts=[SystemAlertOut.model_validate(row) for row in payload["alerts"]],
    )


@router.get("/alerts", response_model=list[SystemAlertOut])
def get_alerts(
    db: Session = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[SystemAlertOut]:
    rows = list_alerts(db, status=status_filter, limit=limit, offset=offset)
    return [SystemAlertOut.model_validate(row) for row in rows]


@router.post("/run", response_model=MonitoringRunOut)
def post_run_monitoring(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_roles(UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR)),
) -> MonitoringRunOut:
    result = run_monitoring_checks(db, commit=True)
    return MonitoringRunOut.model_validate(result.to_dict())


@router.post("/alerts/{alert_id}/acknowledge", response_model=SystemAlertOut)
def post_acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_roles(UserRole.RETURNS_SUPERVISOR, UserRole.ADMINISTRATOR)),
) -> SystemAlertOut:
    row = acknowledge_alert(db, alert_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return SystemAlertOut.model_validate(row)
