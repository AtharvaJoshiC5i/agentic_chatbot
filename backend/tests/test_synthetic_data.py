"""Phase 3 synthetic data generation, load, and validation."""

from pathlib import Path

from sqlalchemy import select

from app.models.tables import Inspection, Refund
from app.synthetic.generator import generate_synthetic_data
from app.synthetic.ground_truth import write_ground_truth_files
from app.synthetic.loader import load_bundle
from app.synthetic.validate import validate_loaded_database


def test_generate_meets_volume_targets() -> None:
    bundle = generate_synthetic_data()
    assert len(bundle.returns) == 500
    assert any(row["return_id"] == "R102" for row in bundle.returns)


def test_r102_serial_mismatch_in_bundle() -> None:
    bundle = generate_synthetic_data()
    inspection = next(row for row in bundle.inspections if row["return_id"] == "R102")
    item = next(
        row
        for row in bundle.order_items
        if row["order_item_id"]
        == next(r["order_item_id"] for r in bundle.returns if r["return_id"] == "R102")
    )
    assert item["purchased_serial_number"] == "HP9081"
    assert inspection["returned_serial_number"] == "HP9012"


def test_load_and_validate_database(db_session) -> None:
    bundle = generate_synthetic_data()
    load_bundle(db_session, bundle)
    report = validate_loaded_database(db_session)
    assert report.ok, report.errors

    r106_refunds = db_session.execute(
        select(Refund).where(Refund.return_id == "R106")
    ).scalars().all()
    assert len(r106_refunds) == 1
    assert r106_refunds[0].refund_status == "completed"

    r113_inspections = db_session.execute(
        select(Inspection).where(Inspection.return_id == "R113")
    ).scalars().all()
    assert len(r113_inspections) == 0


def test_ground_truth_files_created(tmp_path: Path) -> None:
    write_ground_truth_files(tmp_path)
    assert (tmp_path / "return_scenarios.csv").exists()
    assert (tmp_path / "expected_decisions.json").exists()
    assert (tmp_path / "expected_tool_actions.json").exists()
