"""Normalize investigation case issue_type values from agents and APIs."""

from app.models.enums import IssueType
from app.services.cases import CaseServiceError

# LLM and legacy aliases → canonical IssueType values.
_ALIASES: dict[str, str] = {
    "inspection_needed": IssueType.MISSING_INSPECTION.value,
    "inspection_required": IssueType.MISSING_INSPECTION.value,
    "needs_inspection": IssueType.MISSING_INSPECTION.value,
    "awaiting_inspection": IssueType.MISSING_INSPECTION.value,
    "additional_inspection_required": IssueType.MISSING_INSPECTION.value,
    "missing_inspection": IssueType.MISSING_INSPECTION.value,
    "defective_product": IssueType.WARRANTY_REVIEW.value,
    "defective": IssueType.WARRANTY_REVIEW.value,
    "not_functioning": IssueType.WARRANTY_REVIEW.value,
    "manual_investigation_required": IssueType.GENERAL.value,
    "investigation_required": IssueType.GENERAL.value,
    "policy_exception_review_required": IssueType.POLICY_EXCEPTION.value,
    "warranty_review_required": IssueType.WARRANTY_REVIEW.value,
    "serial_mismatch": IssueType.SERIAL_MISMATCH.value,
    "product_mismatch": IssueType.PRODUCT_MISMATCH.value,
    "conflicting_evidence": IssueType.CONFLICTING_EVIDENCE.value,
    "delivery_dispute": IssueType.DELIVERY_DISPUTE.value,
    "safety_concern": IssueType.SAFETY_CONCERN.value,
    "data_correction": IssueType.DATA_CORRECTION.value,
    "duplicate_refund": IssueType.DUPLICATE_REFUND.value,
    "general": IssueType.GENERAL.value,
}


def coerce_issue_type(raw: str | IssueType) -> IssueType:
    if isinstance(raw, IssueType):
        return raw
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        raise CaseServiceError("issue_type is required", "invalid_issue_type")
    canonical = _ALIASES.get(key, key)
    try:
        return IssueType(canonical)
    except ValueError:
        raise CaseServiceError(
            f"Invalid issue_type '{raw}'. Use one of: {', '.join(s.value for s in IssueType)}.",
            "invalid_issue_type",
        ) from None


def issue_type_values_for_prompt() -> str:
    return ", ".join(s.value for s in IssueType)
