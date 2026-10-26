"""Monitoring and alerts API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class SystemAlertOut(BaseModel):
    alert_id: int
    related_entity: str
    related_id: str
    alert_type: str
    severity: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MonitoringRunOut(BaseModel):
    findings_count: int
    alerts_created: int
    alerts_resolved: int
    open_alerts: int
    by_type: dict[str, int] = Field(default_factory=dict)


class MonitoringSummaryOut(BaseModel):
    open_alerts: int
    alerts: list[SystemAlertOut]
