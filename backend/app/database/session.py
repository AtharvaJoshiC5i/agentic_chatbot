"""Database session factory and FastAPI dependency."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import get_engine


@lru_cache
def get_session_maker() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def dispose_session_maker() -> None:
    get_session_maker.cache_clear()


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session; callers commit explicit write transactions."""
    session = get_session_maker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
