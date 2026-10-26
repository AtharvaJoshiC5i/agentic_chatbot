"""Post-process agent replies for workspace operators (plain language, INR, no jargon)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.enums import UserRole

# Whole-word / phrase replacements (investigation & workflow enums → plain English).
_PHRASE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("eligible_for_standard_resolution", "eligible for a standard refund"),
    ("manual_investigation_required", "needs a manual investigation"),
    ("policy_exception_review_required", "needs a policy exception review"),
    ("warranty_review_required", "needs a warranty review"),
    ("additional_inspection_required", "needs another warehouse inspection"),
    ("additional_verification_required", "needs extra verification before we pay out"),
    ("no_inconsistency_detected", "no red flags in our automated checks"),
    ("ineligible_for_refund", "not eligible for a refund"),
    ("like_new", "like new"),
    ("pending supervisor approval", "waiting for a supervisor to approve"),
    ("Phase 8 investigation", "automated investigation"),
    ("Phase 8", ""),
    ("run_return_investigation", "automated investigation"),
    ("F2 signal", "risk signal"),
    ("F3 policy", "policy check"),
    ("F4 outcome", "decision"),
)

_TOOL_NAME_PATTERN = re.compile(
    r"\b(get_|search_|submit_|execute_|list_|run_)[a-z0-9_]+\b",
    re.IGNORECASE,
)

_AMOUNT = r"(\d{1,3}(?:,\d{3})*|\d+)"

_PAISE_PATTERN = re.compile(
    rf"(?<!\d){_AMOUNT}\s*paise\b",
    re.IGNORECASE,
)

_PAISE_PARENTHESES_PATTERN = re.compile(
    rf"\({_AMOUNT}\s*paise\)",
    re.IGNORECASE,
)

_ACTION_ID_PATTERN = re.compile(
    r"\baction\s*(?:request\s*)?(?:ID|id|#)\s*[:#]?\s*(\d+)\b",
    re.IGNORECASE,
)

_NET_RECOVERY_PAISE_PATTERN = re.compile(
    rf"(expected\s+)?net\s+recovery\s+value\s*\({_AMOUNT}\s*paise\)",
    re.IGNORECASE,
)


def _parse_amount(raw: str) -> int:
    return int(raw.replace(",", ""))


def format_inr_from_paise(paise: int) -> str:
    rupees = paise / 100.0
    return f"₹{rupees:,.2f}"


def _replace_paise_amounts(text: str) -> str:
    def net_recovery_sub(match: re.Match[str]) -> str:
        prefix = match.group(1) or ""
        amount = _parse_amount(match.group(2))
        label = "expected refund amount" if prefix else "amount"
        return f"{label} of {format_inr_from_paise(amount)}"

    text = _NET_RECOVERY_PAISE_PATTERN.sub(net_recovery_sub, text)

    def paren_sub(match: re.Match[str]) -> str:
        return format_inr_from_paise(_parse_amount(match.group(1)))

    text = _PAISE_PARENTHESES_PATTERN.sub(paren_sub, text)

    def paise_sub(match: re.Match[str]) -> str:
        return format_inr_from_paise(_parse_amount(match.group(1)))

    return _PAISE_PATTERN.sub(paise_sub, text)


def _replace_phrases(text: str) -> str:
    for old, new in _PHRASE_REPLACEMENTS:
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    return text


def _humanize_action_ids(text: str) -> str:
    return _ACTION_ID_PATTERN.sub(lambda m: f"request #{m.group(1)}", text)


def _strip_tool_names_from_prose(text: str) -> str:
    """Remove bare tool identifiers left in sentences; keep Agent trace for technical detail."""

    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("what i did") and _TOOL_NAME_PATTERN.search(stripped):
            continue
        if stripped.startswith("- ") and _TOOL_NAME_PATTERN.fullmatch(
            stripped[2:].strip().replace(" ", "_").lower()
        ):
            continue
        cleaned = _TOOL_NAME_PATTERN.sub("", line)
        cleaned = re.sub(r"\(\s*\)", "", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        lines.append(cleaned.rstrip())
    return "\n".join(lines).strip()


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def format_operator_response(text: str, *, role: UserRole | None = None) -> str:
    """
    Normalize the final assistant message for shop-floor users.

    Technical tool names belong in Agent trace / supporting evidence, not this string.
    """
    if not text or not text.strip():
        return text

    out = text.strip()
    out = _replace_phrases(out)
    out = _replace_paise_amounts(out)
    out = _humanize_action_ids(out)
    out = _strip_tool_names_from_prose(out)
    out = _collapse_blank_lines(out)

    return out
