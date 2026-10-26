"""Health check endpoint."""

from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings, get_settings
from app.schemas.health import HealthResponse
from app.services.health import aggregate_status, collect_dependency_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """
    Return application status and dependency readiness.

    Phase 1: validates configuration and basic filesystem/SQLite reachability.
    Later phases extend dependency checks (migrations, Chroma collections, etc.).
    """
    dependencies = collect_dependency_health(settings)
    return HealthResponse(
        status=aggregate_status(dependencies),
        app_name=settings.app_name,
        app_env=settings.app_env,
        version=__version__,
        dependencies=dependencies,
    )
