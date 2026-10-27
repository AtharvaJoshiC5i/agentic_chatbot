"""Tool-result grounding for operator-facing chat replies."""

from app.agents.tool_grounding import enforce_tool_grounding
from app.models.enums import UserRole


def test_receipt_error_blocks_false_success_claim() -> None:
    text = "## Actions performed\nRecorded warehouse receipt for R371."
    events = [
        {
            "tool": "record_warehouse_receipt",
            "_result_content": '{"error": "invalid_transition", "message": "Return already received."}',
        }
    ]
    out = enforce_tool_grounding(text, events, role=UserRole.WAREHOUSE_MANAGER)
    assert "## Correction (system — tool results)" in out
    assert "was **not** saved" in out
    assert "Recorded warehouse receipt" in out


def test_unit_not_found_blocks_serial_verified_claim() -> None:
    text = "We confirmed the serial matches inventory."
    events = [
        {
            "tool": "get_product_unit",
            "_result_content": '{"error": "unit_not_found", "serial_number": "SN001645"}',
        }
    ]
    out = enforce_tool_grounding(text, events, role=UserRole.WAREHOUSE_MANAGER)
    assert "not** in the product-units registry" in out


def test_successful_receipt_no_correction() -> None:
    text = "Receipt is on file for this return."
    events = [
        {
            "tool": "record_warehouse_receipt",
            "_result_content": '{"return_id": "R105", "received_date": "2026-01-01"}',
        }
    ]
    out = enforce_tool_grounding(text, events, role=UserRole.WAREHOUSE_MANAGER)
    assert "## Correction" not in out
