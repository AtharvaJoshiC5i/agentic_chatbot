"""FastAPI application entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.database.connection import dispose_engine
from app.database.migrate import upgrade_database_to_head
from app.routes import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    settings.ensure_runtime_directories()
    dispose_engine()
    try:
        upgrade_database_to_head()
    except Exception:  # noqa: BLE001 — log and continue so misconfigured Alembic does not block health checks
        logger.exception("Automatic database migration failed; run: alembic upgrade head")
    try:
        from app.database.session import get_session_maker
        from app.services.demo_users import ensure_demo_users

        boot = get_session_maker()()
        try:
            n = ensure_demo_users(boot)
            if n:
                logger.info("Created %s demo user(s) for workspace login", n)
        finally:
            boot.close()
    except Exception:  # noqa: BLE001
        logger.exception("Demo user bootstrap failed; run: python scripts/seed_users.py")
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        __version__,
        settings.app_env,
    )

    monitor_task: asyncio.Task | None = None

    async def _monitoring_worker() -> None:
        from app.database.session import get_session_maker
        from app.services.monitoring import run_monitoring_checks

        interval = max(5, settings.monitoring_interval_minutes * 60)
        while True:
            await asyncio.sleep(interval)
            session = get_session_maker()()
            try:
                run_monitoring_checks(session, commit=True)
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled monitoring run failed")
            finally:
                session.close()

    if settings.monitoring_auto_run:
        monitor_task = asyncio.create_task(_monitoring_worker())

    yield

    if monitor_task is not None:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "AI Returns Fraud & Product Recovery Agent for ShopSphere Retail. "
            "Structured data in SQLite; unstructured retrieval via ChromaDB (later phases)."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api")

    return application


app = create_app()
