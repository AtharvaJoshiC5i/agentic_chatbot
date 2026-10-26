"""Shared pytest fixtures for database-backed tests."""

from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.connection import dispose_engine, get_engine
from app.database.session import get_session_maker
from app.models.enums import AccountStatus, OrderStatus
from app.models.tables import Customer, Order, Product, Supplier
from app.database.base import utc_now


@pytest.fixture()
def migrated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Isolated SQLite file with Alembic migrations applied."""
    db_path = tmp_path / "test_shopsphere.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    dispose_engine()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    yield db_path

    dispose_engine()
    get_settings.cache_clear()


@pytest.fixture()
def db_session(migrated_db: Path) -> Generator[Session, None, None]:
    session = get_session_maker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def populated_db(db_session: Session) -> Session:
    """Migrated SQLite database with Phase 3 synthetic structured data loaded."""
    from app.synthetic.generator import generate_synthetic_data
    from app.synthetic.loader import load_bundle

    load_bundle(db_session, generate_synthetic_data())
    return db_session


@pytest.fixture()
def sample_catalog(db_session: Session) -> dict[str, str]:
    """Minimal customer, supplier, product, and order for relationship tests."""
    now = utc_now()
    customer = Customer(
        customer_id="C_TEST_001",
        customer_name="Test Customer",
        email="test.customer@example.invalid",
        account_created_at=now,
        account_status=AccountStatus.ACTIVE,
    )
    supplier = Supplier(
        supplier_id="S_TEST_001",
        supplier_name="Test Supplier",
        category="electronics",
        contact_email="supplier@example.invalid",
    )
    product = Product(
        product_id="P_TEST_001",
        product_name="Test Headphones",
        category="electronics",
        brand="ShopSphere",
        original_price=499900,
        warranty_months=12,
        serial_tracked=True,
        supplier_id=supplier.supplier_id,
    )
    order = Order(
        order_id="O_TEST_001",
        customer_id=customer.customer_id,
        order_date=now,
        total_amount=499900,
        order_status=OrderStatus.FULFILLED,
    )
    db_session.add_all([customer, supplier, product, order])
    db_session.commit()
    return {
        "customer_id": customer.customer_id,
        "supplier_id": supplier.supplier_id,
        "product_id": product.product_id,
        "order_id": order.order_id,
    }
