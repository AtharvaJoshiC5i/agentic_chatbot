"""Health check response models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DependencyStatus(str, Enum):
    OK = "ok"
    NOT_READY = "not_ready"
    DEGRADED = "degraded"
    SKIPPED = "skipped"


class DependencyHealth(BaseModel):
    name: str
    status: DependencyStatus
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: DependencyStatus
    app_name: str
    app_env: str
    version: str
    dependencies: list[DependencyHealth]
