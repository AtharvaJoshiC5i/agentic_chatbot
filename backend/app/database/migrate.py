"""Apply pending Alembic migrations (SQLite dev convenience)."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.database.connection import dispose_engine

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _sqlite_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False, "timeout": 30.0}
    return {}


def _alembic_config() -> Config | None:
    ini_path = _BACKEND_ROOT / "alembic.ini"
    if not ini_path.is_file():
        logger.warning("alembic.ini not found at %s; skipping auto-migrate", ini_path)
        return None
    return Config(str(ini_path))


def _head_revision(cfg: Config) -> str | None:
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head()


def _current_revision(database_url: str) -> str | None:
    engine = create_engine(
        database_url,
        connect_args=_sqlite_connect_args(database_url),
        pool_pre_ping=True,
    )
    try:
        with engine.connect() as connection:
            if not database_url.startswith("sqlite"):
                context = MigrationContext.configure(connection)
                return context.get_current_revision()

            # Fresh SQLite file may not have alembic_version yet.
            has_table = connection.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='alembic_version'"
                )
            ).fetchone()
            if not has_table:
                return None
            row = connection.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            return row[0] if row else None
    finally:
        engine.dispose()


def upgrade_database_to_head() -> None:
    """Run `alembic upgrade head` against the configured DATABASE_URL."""
    cfg = _alembic_config()
    if cfg is None:
        return

    settings = get_settings()
    head = _head_revision(cfg)
    if head:
        dispose_engine()
        current = _current_revision(settings.database_url)
        if current == head:
            logger.info("Database schema already at Alembic head (%s)", head)
            return

    dispose_engine()
    try:
        command.upgrade(cfg, "head")
    finally:
        dispose_engine()

    logger.info("Database schema is at Alembic head")
