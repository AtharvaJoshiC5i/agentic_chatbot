"""Request-scoped context for agent tools.

LangGraph may invoke tools on worker threads. Never share the FastAPI request ``Session``
across threads — use a scoped session per thread (removed on clear).
"""

from contextvars import ContextVar
from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs, var_child_runnable_config
from sqlalchemy.orm import Session, scoped_session

from app.database.session import get_session_maker
from app.security.deps import CurrentUser

AGENT_USER_CONFIG_KEY = "agent_user"

_test_db_session: ContextVar[Session | None] = ContextVar("agent_test_db_session", default=None)
_current_user: ContextVar[CurrentUser | None] = ContextVar("agent_current_user", default=None)


@lru_cache
def _agent_scoped_sessions() -> scoped_session[Session]:
    return scoped_session(get_session_maker())


def set_agent_context(session: Session, user: CurrentUser) -> None:
    """Bind an existing session (unit tests)."""
    _test_db_session.set(session)
    _current_user.set(user)


def apply_agent_context_if_provided(
    session: Session | None,
    user: CurrentUser | None,
) -> None:
    """Re-bind user when LangGraph runs off the main request thread."""
    if user is not None:
        _current_user.set(user)


def agent_run_config(
    _session: Session | None,
    user: CurrentUser | None,
) -> RunnableConfig | None:
    if user is None:
        return None
    return RunnableConfig(configurable={AGENT_USER_CONFIG_KEY: user})


def merge_agent_run_config(
    base: RunnableConfig | None,
    session: Session | None,
    user: CurrentUser | None,
) -> RunnableConfig | None:
    agent_part = agent_run_config(session, user)
    if base is None:
        return agent_part
    if agent_part is None:
        return base
    return merge_configs(base, agent_part)


def _user_from_runnable_configurable() -> CurrentUser | None:
    config = var_child_runnable_config.get()
    if not config:
        return None
    conf = config.get("configurable") or {}
    user = conf.get(AGENT_USER_CONFIG_KEY)
    return user if isinstance(user, CurrentUser) else None


def get_agent_user() -> CurrentUser:
    user = _current_user.get()
    if user is None:
        user = _user_from_runnable_configurable()
    if user is None:
        raise RuntimeError("Agent user context is not set for this request.")
    return user


def get_agent_db() -> Session:
    test_session = _test_db_session.get()
    if test_session is not None:
        return test_session
    get_agent_user()
    return _agent_scoped_sessions()()


def clear_agent_context() -> None:
    _test_db_session.set(None)
    try:
        _agent_scoped_sessions().remove()
    except Exception:
        pass
    _current_user.set(None)


def dispose_agent_scoped_sessions() -> None:
    """Test teardown helper."""
    clear_agent_context()
    _agent_scoped_sessions.cache_clear()
