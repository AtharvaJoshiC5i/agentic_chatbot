"""SQLAlchemy engine factory and SQLite pragmas."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, event, create_engine
from sqlalchemy.pool import StaticPool

from app.config import get_settings


def _sqlite_on_connect(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    connect_args: dict = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    if url.endswith(":memory:") or url.rstrip("/").endswith(":memory:"):
        engine = create_engine(
            url,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

    if url.startswith("sqlite"):
        event.listen(engine, "connect", _sqlite_on_connect)

    return engine


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    from app.database.session import dispose_session_maker

    dispose_session_maker()
