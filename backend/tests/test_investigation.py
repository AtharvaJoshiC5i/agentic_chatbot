"""Phase 8 deterministic investigation engine tests."""

import json
from pathlib import Path

import pytest

from app.investigation.investigation import run_investigation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH_PATH = PROJECT_ROOT / "data/ground_truth/expected_decisions.json"


@pytest.fixture(scope="module")
def expected_decisions() -> dict:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("return_id", [f"R{i}" for i in range(101, 116)])
def test_investigation_matches_ground_truth(
    populated_db, expected_decisions: dict, return_id: str
) -> None:
    expected = expected_decisions[return_id]
    report = run_investigation(populated_db, return_id)
    assert report is not None
    assert report.f4_outcome == expected["expected_investigation_outcome"]
    assert report.f2_signal == expected["expected_signal"]


def test_investigation_unknown_return(populated_db) -> None:
    assert run_investigation(populated_db, "R999") is None


def test_investigation_twelve_checks(populated_db) -> None:
    report = run_investigation(populated_db, "R102")
    assert report is not None
    assert len(report.checks) == 12
    check_ids = {check.check_id for check in report.checks}
    assert "return_window_eligibility" in check_ids
    assert "serial_number_match" in check_ids
