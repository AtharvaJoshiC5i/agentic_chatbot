"""Product unit lookup matches order-line purchased serials."""

import json

from sqlalchemy import select

from app.agents.context import clear_agent_context, set_agent_context
from app.models.enums import UserRole
from app.models.tables import OrderItem
from app.security.deps import CurrentUser
from app.tools.sql_tools import get_product_unit


def test_get_product_unit_by_purchased_serial(populated_db) -> None:
    item = populated_db.execute(
        select(OrderItem)
        .where(OrderItem.purchased_serial_number.isnot(None))
        .limit(1)
    ).scalar_one()
    purchased = item.purchased_serial_number
    assert purchased

    set_agent_context(
        populated_db,
        CurrentUser(user_id=1, username="wh", role=UserRole.WAREHOUSE_MANAGER),
    )
    try:
        raw = get_product_unit.invoke({"serial_number": purchased})
    finally:
        clear_agent_context()
    data = json.loads(raw)
    assert "error" not in data
    assert data.get("matched_via") == "purchased_serial_number" or data["serial_number"] == purchased
