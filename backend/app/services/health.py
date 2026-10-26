"""Health and readiness checks for external dependencies."""

import sqlite3
from pathlib import Path

from app.config import Settings
from app.schemas.health import DependencyHealth, DependencyStatus


def _check_sqlite(settings: Settings) -> DependencyHealth:
    db_path = settings.sqlite_database_path
    if db_path is None:
        if settings.database_url.endswith(":memory:"):
            return DependencyHealth(
                name="sqlite",
                status=DependencyStatus.OK,
                detail="In-memory SQLite configured (development/test).",
                metadata={"database_url": settings.database_url},
            )
        return DependencyHealth(
            name="sqlite",
            status=DependencyStatus.DEGRADED,
            detail="Database URL is not a supported file-backed SQLite path.",
            metadata={"database_url": settings.database_url},
        )

    metadata = {"path": str(db_path)}

    if not db_path.exists():
        parent_writable = _is_directory_writable(db_path.parent)
        if parent_writable:
            return DependencyHealth(
                name="sqlite",
                status=DependencyStatus.NOT_READY,
                detail="Database file not created yet (expected before Phase 2 migrations).",
                metadata=metadata,
            )
        return DependencyHealth(
            name="sqlite",
            status=DependencyStatus.DEGRADED,
            detail="Database directory is not writable.",
            metadata=metadata,
        )

    try:
        with sqlite3.connect(db_path, timeout=5.0) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            version_row = connection.execute("SELECT sqlite_version()").fetchone()
            sqlite_version = version_row[0] if version_row else "unknown"
            metadata["sqlite_version"] = sqlite_version

            migration_row = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            if migration_row is None:
                return DependencyHealth(
                    name="sqlite",
                    status=DependencyStatus.NOT_READY,
                    detail="Database file exists but migrations have not been applied.",
                    metadata=metadata,
                )
            metadata["alembic_revision"] = migration_row[0]

            returns_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='returns'"
            ).fetchone()
            if returns_exists is None:
                return DependencyHealth(
                    name="sqlite",
                    status=DependencyStatus.DEGRADED,
                    detail="Migrations applied but core schema tables are missing.",
                    metadata=metadata,
                )

        return DependencyHealth(
            name="sqlite",
            status=DependencyStatus.OK,
            detail="SQLite schema is migrated and reachable.",
            metadata=metadata,
        )
    except sqlite3.Error as exc:
        return DependencyHealth(
            name="sqlite",
            status=DependencyStatus.DEGRADED,
            detail=f"SQLite connection failed: {exc}",
            metadata=metadata,
        )


def _check_chroma(settings: Settings) -> DependencyHealth:
    chroma_dir = settings.chroma_directory
    metadata = {"path": str(chroma_dir)}

    if not chroma_dir.exists():
        if _is_directory_writable(chroma_dir.parent):
            return DependencyHealth(
                name="chroma",
                status=DependencyStatus.NOT_READY,
                detail="Chroma data directory not initialized (expected in Phase 5).",
                metadata=metadata,
            )
        return DependencyHealth(
            name="chroma",
            status=DependencyStatus.DEGRADED,
            detail="Chroma parent directory is not writable.",
            metadata=metadata,
        )

    if not chroma_dir.is_dir():
        return DependencyHealth(
            name="chroma",
            status=DependencyStatus.DEGRADED,
            detail="Chroma path exists but is not a directory.",
            metadata=metadata,
        )

    try:
        from app.rag.store import collection_document_count

        chunk_count = collection_document_count()
        metadata["indexed_chunks"] = chunk_count
        if chunk_count > 0:
            return DependencyHealth(
                name="chroma",
                status=DependencyStatus.OK,
                detail="Chroma vector index is populated.",
                metadata=metadata,
            )
        return DependencyHealth(
            name="chroma",
            status=DependencyStatus.NOT_READY,
            detail="Chroma directory exists but no chunks indexed yet (run scripts/ingest_documents.py).",
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001 — surface dependency health without crashing API
        return DependencyHealth(
            name="chroma",
            status=DependencyStatus.DEGRADED,
            detail=f"Chroma check failed: {exc}",
            metadata=metadata,
        )


def _check_llm(settings: Settings) -> DependencyHealth:
    from app.llm.gemini import GEMINI_MODEL, is_gemini_configured
    from app.llm.groq import is_groq_configured

    groq_ok = is_groq_configured()
    gemini_ok = is_gemini_configured()
    if groq_ok or gemini_ok:
        return DependencyHealth(
            name="llm",
            status=DependencyStatus.OK,
            detail="At least one LLM provider is configured.",
            metadata={
                "default_provider": settings.llm_provider,
                "groq": {"configured": groq_ok, "model": settings.groq_model},
                "gemini": {"configured": gemini_ok, "model": GEMINI_MODEL},
            },
        )
    return DependencyHealth(
        name="llm",
        status=DependencyStatus.NOT_READY,
        detail="No LLM configured (set GROQ_API_KEY or GEMINI_API_KEY).",
        metadata={
            "default_provider": settings.llm_provider or None,
            "groq": {"configured": False, "model": settings.groq_model},
            "gemini": {"configured": False, "model": GEMINI_MODEL},
        },
    )


def _is_directory_writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def collect_dependency_health(settings: Settings) -> list[DependencyHealth]:
    return [
        _check_sqlite(settings),
        _check_chroma(settings),
        _check_llm(settings),
    ]


def aggregate_status(dependencies: list[DependencyHealth]) -> DependencyStatus:
    if any(dep.status == DependencyStatus.DEGRADED for dep in dependencies):
        return DependencyStatus.DEGRADED
    if all(dep.status == DependencyStatus.OK for dep in dependencies):
        return DependencyStatus.OK
    return DependencyStatus.NOT_READY
