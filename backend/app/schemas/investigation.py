"""Investigation API schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InvestigationCheckOut(BaseModel):
    check_id: str
    title: str
    status: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class PolicyEvaluationOut(BaseModel):
    product_category: str
    return_window_days: int
    days_after_delivery: int | None
    within_return_window: bool | None
    warranty_months: int
    order_age_days: int | None
    within_warranty_period: bool | None
    delivery_date: datetime | None = None
    return_request_date: datetime | None = None


class InvestigationReportOut(BaseModel):
    return_id: str
    scenario_slug: str | None
    checks: list[InvestigationCheckOut]
    f2_signal: str
    f3_policy: PolicyEvaluationOut
    f4_outcome: str
    recommended_actions: list[str]
    generated_at: datetime
