"""Ground-truth artifacts for agent evaluation (not used at runtime retrieval)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.synthetic.scenarios import SCENARIO_SPECS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GROUND_TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"


def build_expected_decisions() -> dict[str, Any]:
    decisions: dict[str, Any] = {}
    for spec in SCENARIO_SPECS:
        decisions[spec.return_id] = {
            "scenario": spec.slug,
            "title": spec.title,
            "expected_investigation_outcome": spec.expected_investigation_outcome,
            "expected_signal": spec.expected_signal,
            "notes": spec.notes,
        }
    return decisions


def build_expected_tool_actions() -> dict[str, Any]:
    return {
        "R102": {
            "investigate": True,
            "expected_tools": [
                "get_return_details",
                "get_order_details",
                "get_inspection_results",
                "search_return_policy",
                "submit_create_investigation_case",
            ],
            "must_not": ["execute_action_request"],
        },
        "R101": {
            "investigate": True,
            "expected_tools": ["get_return_details", "search_return_policy", "submit_refund_request"],
            "approval_required": True,
        },
        "R106": {
            "investigate": True,
            "expected_tools": ["get_refund_status"],
            "must_not": ["execute_action_request"],
        },
        "R108": {
            "investigate": True,
            "expected_tools": [
                "get_return_details",
                "get_inspection_results",
                "submit_repair_recovery_task",
                "get_recovery_recommendation",
            ],
        },
        "R113": {
            "investigate": True,
            "expected_tools": ["get_inspection_results", "submit_create_investigation_case"],
            "expected_signal": "insufficient_evidence",
        },
        "R110": {
            "investigate": True,
            "expected_tools": ["get_inspection_results"],
            "expected_signal": "conflicting_inspection_findings",
        },
    }


def write_ground_truth_files(output_dir: Path | None = None) -> None:
    directory = output_dir or GROUND_TRUTH_DIR
    directory.mkdir(parents=True, exist_ok=True)

    csv_path = directory / "return_scenarios.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "return_id",
                "scenario_slug",
                "title",
                "expected_investigation_outcome",
                "expected_signal",
                "notes",
            ],
        )
        writer.writeheader()
        for spec in SCENARIO_SPECS:
            writer.writerow(
                {
                    "return_id": spec.return_id,
                    "scenario_slug": spec.slug,
                    "title": spec.title,
                    "expected_investigation_outcome": spec.expected_investigation_outcome,
                    "expected_signal": spec.expected_signal,
                    "notes": spec.notes,
                }
            )

    decisions_path = directory / "expected_decisions.json"
    decisions_path.write_text(
        json.dumps(build_expected_decisions(), indent=2),
        encoding="utf-8",
    )

    actions_path = directory / "expected_tool_actions.json"
    actions_path.write_text(
        json.dumps(build_expected_tool_actions(), indent=2),
        encoding="utf-8",
    )
