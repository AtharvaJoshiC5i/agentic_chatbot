from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.database.base import Base
from app.models import (  # noqa: F401 — register metadata
    ActionRequest,
    AuditLog,
    Customer,
    Delivery,
    DocumentMetadata,
    Inspection,
    InvestigationCase,
    Order,
    OrderItem,
    Product,
    ProductUnit,
    RecoveryOption,
    RecoveryTask,
    Refund,
    Return,
    ReturnEvent,
    Supplier,
    SystemAlert,
    User,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    url = get_url()
    configuration["sqlalchemy.url"] = url
    if url.startswith("sqlite"):
        configuration["sqlalchemy.connect_args"] = {
            "check_same_thread": False,
            "timeout": 30.0,
        }

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
