"""Investigation inconsistency signals (F2) derived from facts and checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SignalCode = Literal[
    "no_inconsistency_detected",
    "additional_verification_required",
    "duplicate_refund_attempt",
    "manual_investigation_required",
    "conflicting_inspection_findings",
    "product_mismatch",
    "insufficient_evidence",
]


@dataclass(frozen=True)
class SignalContext:
    has_completed_refund: bool
    """Non-terminal refund row (requested/approved) alongside or after a completed refund."""
    has_open_refund: bool
    inspection_count: int
    return_received: bool
    serial_mismatch: bool
    product_mismatch: bool
    conflicting_inspections: bool
    delivery_dispute: bool
    unsafe_product: bool
    data_record_conflict: bool
    accessories_incomplete: bool
    outside_return_window: bool
    verification_issue_count: int
    open_investigation_case: bool


def count_verification_issues(ctx: SignalContext) -> int:
    issues = 0
    if ctx.serial_mismatch:
        issues += 1
    if ctx.product_mismatch:
        issues += 1
    if ctx.delivery_dispute:
        issues += 1
    if ctx.data_record_conflict:
        issues += 1
    if not ctx.return_received and ctx.inspection_count == 0:
        issues += 0
    return issues


def derive_primary_signal(ctx: SignalContext) -> SignalCode:
    """F2 — single primary signal for dashboards, alerts, and eval harness.

    ``duplicate_refund_attempt`` applies when a completed refund exists *and* an open
    refund row is still pending (a new payout request). A return that is already fully
    refunded with no open request shows ``no_inconsistency_detected`` (see R106 at rest).
    """
    if ctx.conflicting_inspections:
        return "conflicting_inspection_findings"
    if ctx.return_received and ctx.inspection_count == 0:
        return "insufficient_evidence"
    if ctx.has_completed_refund and ctx.has_open_refund:
        return "duplicate_refund_attempt"
    if ctx.unsafe_product:
        return "manual_investigation_required"
    if ctx.verification_issue_count >= 2 or (
        ctx.serial_mismatch and ctx.product_mismatch
    ):
        return "manual_investigation_required"
    if ctx.product_mismatch:
        return "product_mismatch"
    if ctx.outside_return_window:
        return "additional_verification_required"
    if ctx.accessories_incomplete:
        return "additional_verification_required"
    if ctx.serial_mismatch or ctx.delivery_dispute or ctx.data_record_conflict:
        return "additional_verification_required"
    if ctx.open_investigation_case and ctx.verification_issue_count >= 1:
        return "additional_verification_required"
    return "no_inconsistency_detected"
