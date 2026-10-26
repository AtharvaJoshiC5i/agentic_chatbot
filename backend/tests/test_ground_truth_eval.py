"""Phase 14 ground-truth evaluation harness."""

import json

from app.eval.harness import run_full_eval


def test_full_ground_truth_eval_passes(populated_db) -> None:
    report = run_full_eval(populated_db)
    if not report.passed:
        failures = json.dumps([c.__dict__ for c in report.failed], indent=2)
        raise AssertionError(f"Ground-truth eval failed:\n{failures}")
    assert report.passed
    assert len(report.checks) >= 40


def test_eval_report_serializable(populated_db) -> None:
    payload = run_full_eval(populated_db).to_dict()
    assert "passed" in payload
    assert payload["total"] > 0
