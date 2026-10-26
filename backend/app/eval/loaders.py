"""Load evaluation artifacts from data/ground_truth."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.synthetic.ground_truth import GROUND_TRUTH_DIR


def load_expected_decisions(path: Path | None = None) -> dict[str, Any]:
    file_path = path or (GROUND_TRUTH_DIR / "expected_decisions.json")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_expected_tool_actions(path: Path | None = None) -> dict[str, Any]:
    file_path = path or (GROUND_TRUTH_DIR / "expected_tool_actions.json")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_return_scenarios_csv(path: Path | None = None) -> list[dict[str, str]]:
    file_path = path or (GROUND_TRUTH_DIR / "return_scenarios.csv")
    with file_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
