"""Ensure demo workspace users exist (idempotent)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.enums import UserRole
from app.models.tables import User
from app.security.passwords import hash_password

# (username, role value, password) — roles must match UserRole / ck_users_role in SQLite.
DEMO_USERS: tuple[tuple[str, str, str], ...] = (
    ("returns_supervisor", UserRole.RETURNS_SUPERVISOR.value, "ShopSphere@Super1"),
    ("returns_analyst", UserRole.RETURNS_ANALYST.value, "ShopSphere@Analyst1"),
    ("warehouse_mgr", UserRole.WAREHOUSE_MANAGER.value, "ShopSphere@Warehouse1"),
)


def ensure_demo_users(session: Session) -> int:
    """Insert or refresh demo users. Returns count created."""
    settings = get_settings()
    sync_passwords = settings.app_env.strip().lower() in {"development", "dev", "local"}
    created = 0
    for username, role, password in DEMO_USERS:
        row = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if row is None:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    active=True,
                )
            )
            created += 1
        elif sync_passwords:
            row.password_hash = hash_password(password)
            row.role = role
            row.active = True
        session.commit()
    return created
