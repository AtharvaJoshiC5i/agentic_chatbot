"""Issue type coercion for agent case creation."""

from app.models.enums import IssueType
from app.services.issue_types import coerce_issue_type


def test_inspection_needed_maps_to_missing_inspection() -> None:
    assert coerce_issue_type("inspection_needed") == IssueType.MISSING_INSPECTION


def test_defective_product_maps_to_warranty_review() -> None:
    assert coerce_issue_type("defective_product") == IssueType.WARRANTY_REVIEW


def test_canonical_values_unchanged() -> None:
    assert coerce_issue_type("serial_mismatch") == IssueType.SERIAL_MISMATCH
