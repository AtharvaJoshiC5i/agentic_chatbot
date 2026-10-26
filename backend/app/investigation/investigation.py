"""Deterministic investigation engine — twelve checks, F2/F3/F4 outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.investigation.policy import PolicyEvaluation, evaluate_policy
from app.investigation.signals import SignalContext, derive_primary_signal
from app.models.enums import IssueType, ProductCondition, RefundStatus, ReturnReason, ReturnStatus
from app.models.tables import (
    Delivery,
    Inspection,
    InvestigationCase,
    Order,
    OrderItem,
    Product,
    Refund,
    Return,
)

InvestigationOutcome = Literal[
    "eligible_for_standard_resolution",
    "manual_investigation_required",
    "policy_exception_review_required",
    "warranty_review_required",
    "additional_inspection_required",
]

CheckStatus = Literal["pass", "fail", "warn", "skip"]


@dataclass
class InvestigationCheck:
    check_id: str
    title: str
    status: CheckStatus
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvestigationReport:
    return_id: str
    scenario_slug: str | None
    checks: list[InvestigationCheck]
    f2_signal: str
    f3_policy: PolicyEvaluation
    f4_outcome: InvestigationOutcome
    recommended_actions: list[str]
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "return_id": self.return_id,
            "scenario_slug": self.scenario_slug,
            "checks": [
                {
                    "check_id": c.check_id,
                    "title": c.title,
                    "status": c.status,
                    "summary": c.summary,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "f2_signal": self.f2_signal,
            "f3_policy": self.f3_policy.to_dict(),
            "f4_outcome": self.f4_outcome,
            "recommended_actions": self.recommended_actions,
            "generated_at": self.generated_at,
        }


@dataclass
class _Facts:
    return_row: Return
    order_item: OrderItem
    product: Product
    order: Order
    delivery: Delivery | None
    inspections: list[Inspection]
    refunds: list[Refund]
    cases: list[InvestigationCase]
    purchased_serial: str | None
    returned_serial: str | None
    policy: PolicyEvaluation
    serial_mismatch: bool
    product_mismatch: bool
    conflicting_inspections: bool
    unsafe_product: bool
    data_record_conflict: bool
    delivery_dispute: bool
    accessories_incomplete: bool
    has_completed_refund: bool
    has_open_refund: bool
    open_investigation_case: bool
    verification_issue_count: int


def _note_contains(notes: str | None, fragment: str) -> bool:
    return fragment.lower() in (notes or "").lower()


def _load_facts(session: Session, return_id: str) -> _Facts | None:
    return_row = session.get(Return, return_id)
    if return_row is None:
        return None

    order_item = session.get(OrderItem, return_row.order_item_id)
    if order_item is None:
        return None
    product = session.get(Product, order_item.product_id)
    order = session.get(Order, order_item.order_id)
    if product is None or order is None:
        return None

    delivery = session.execute(
        select(Delivery).where(Delivery.order_id == order.order_id)
    ).scalar_one_or_none()

    inspections = list(
        session.execute(select(Inspection).where(Inspection.return_id == return_id))
        .scalars()
        .all()
    )
    refunds = list(
        session.execute(select(Refund).where(Refund.return_id == return_id)).scalars().all()
    )
    cases = list(
        session.execute(select(InvestigationCase).where(InvestigationCase.return_id == return_id))
        .scalars()
        .all()
    )

    purchased_serial = order_item.purchased_serial_number
    returned_serial = None
    if inspections:
        returned_serial = inspections[-1].returned_serial_number

    policy = evaluate_policy(
        product_category=product.category,
        warranty_months=product.warranty_months,
        delivery_date=delivery.delivery_date if delivery else None,
        return_request_date=return_row.request_date,
        order_date=order.order_date,
    )

    serial_mismatch = bool(
        purchased_serial
        and returned_serial
        and purchased_serial.strip() != returned_serial.strip()
    )

    product_mismatch = return_row.return_reason == ReturnReason.WRONG_PRODUCT.value or any(
        _note_contains(i.inspector_notes, "sku label does not match") for i in inspections
    ) or any(c.issue_type == IssueType.PRODUCT_MISMATCH.value for c in cases)

    defect_flags = {i.defect_verified for i in inspections}
    conflicting_inspections = len(inspections) >= 2 and len(defect_flags) > 1

    unsafe_product = any(
        i.product_condition == ProductCondition.UNSAFE.value for i in inspections
    )

    data_record_conflict = any(
        c.issue_type == IssueType.DATA_CORRECTION.value for c in cases
    ) or any(
        _note_contains(i.inspector_notes, "line item is accessory")
        or _note_contains(i.inspector_notes, "return reason references")
        for i in inspections
    )

    delivery_dispute = bool(delivery and delivery.delivery_issue) or any(
        c.issue_type == IssueType.DELIVERY_DISPUTE.value for c in cases
    )

    accessories_incomplete = any(not i.accessories_complete for i in inspections)

    primary_refund_key = f"refund-{return_id}-primary"
    has_completed_refund = any(
        r.refund_status == RefundStatus.COMPLETED.value and r.idempotency_key == primary_refund_key
        for r in refunds
    )
    has_open_refund = any(
        r.refund_status not in (RefundStatus.COMPLETED.value, RefundStatus.CANCELLED.value)
        for r in refunds
    )

    from app.services.case_transitions import ACTIVE_CASE_STATUSES

    _active_case_values = {s.value for s in ACTIVE_CASE_STATUSES}
    open_investigation_case = any(c.case_status in _active_case_values for c in cases)

    verification_issue_count = sum(
        1
        for flag in (
            serial_mismatch,
            product_mismatch,
            delivery_dispute,
            data_record_conflict,
            accessories_incomplete and not product_mismatch,
        )
        if flag
    )

    return _Facts(
        return_row=return_row,
        order_item=order_item,
        product=product,
        order=order,
        delivery=delivery,
        inspections=inspections,
        refunds=refunds,
        cases=cases,
        purchased_serial=purchased_serial,
        returned_serial=returned_serial,
        policy=policy,
        serial_mismatch=serial_mismatch,
        product_mismatch=product_mismatch,
        conflicting_inspections=conflicting_inspections,
        unsafe_product=unsafe_product,
        data_record_conflict=data_record_conflict,
        delivery_dispute=delivery_dispute,
        accessories_incomplete=accessories_incomplete,
        has_completed_refund=has_completed_refund,
        has_open_refund=has_open_refund,
        open_investigation_case=open_investigation_case,
        verification_issue_count=verification_issue_count,
    )


def _run_checks(facts: _Facts) -> list[InvestigationCheck]:
    checks: list[InvestigationCheck] = []

    checks.append(
        InvestigationCheck(
            check_id="return_record_valid",
            title="Return record",
            status="pass",
            summary=f"Return {facts.return_row.return_id} is {facts.return_row.return_status}.",
        )
    )

    if facts.delivery is None or facts.delivery.delivery_date is None:
        checks.append(
            InvestigationCheck(
                check_id="delivery_recorded",
                title="Delivery evidence",
                status="fail",
                summary="No confirmed delivery date on file.",
            )
        )
    else:
        checks.append(
            InvestigationCheck(
                check_id="delivery_recorded",
                title="Delivery evidence",
                status="pass",
                summary="Delivery date is recorded.",
                details={"delivery_date": facts.delivery.delivery_date},
            )
        )

    if facts.policy.within_return_window is False:
        checks.append(
            InvestigationCheck(
                check_id="return_window_eligibility",
                title="Return window",
                status="fail",
                summary=(
                    f"Request is {facts.policy.days_after_delivery} days after delivery; "
                    f"policy allows {facts.policy.return_window_days} days for {facts.policy.product_category}."
                ),
                details=facts.policy.to_dict(),
            )
        )
    elif facts.policy.within_return_window is True:
        checks.append(
            InvestigationCheck(
                check_id="return_window_eligibility",
                title="Return window",
                status="pass",
                summary="Return request falls within the standard window.",
                details=facts.policy.to_dict(),
            )
        )
    else:
        checks.append(
            InvestigationCheck(
                check_id="return_window_eligibility",
                title="Return window",
                status="skip",
                summary="Unable to compute return window (missing dates).",
            )
        )

    if facts.purchased_serial and facts.returned_serial:
        status: CheckStatus = "fail" if facts.serial_mismatch else "pass"
        checks.append(
            InvestigationCheck(
                check_id="serial_number_match",
                title="Serial consistency",
                status=status,
                summary=(
                    f"Purchased {facts.purchased_serial} vs returned {facts.returned_serial}."
                ),
            )
        )
    else:
        checks.append(
            InvestigationCheck(
                check_id="serial_number_match",
                title="Serial consistency",
                status="skip",
                summary="Product is not serial-tracked or inspection serial not recorded.",
            )
        )

    pm_status: CheckStatus = "fail" if facts.product_mismatch else "pass"
    checks.append(
        InvestigationCheck(
            check_id="product_sku_match",
            title="Product identity",
            status=pm_status,
            summary="Returned item matches ordered SKU."
            if pm_status == "pass"
            else "Evidence indicates wrong product or SKU label mismatch.",
        )
    )

    if facts.return_row.received_date and not facts.inspections:
        checks.append(
            InvestigationCheck(
                check_id="inspection_completed",
                title="Warehouse inspection",
                status="fail",
                summary="Return received but no inspection record exists.",
            )
        )
    elif facts.inspections:
        checks.append(
            InvestigationCheck(
                check_id="inspection_completed",
                title="Warehouse inspection",
                status="pass",
                summary=f"{len(facts.inspections)} inspection record(s) on file.",
            )
        )
    else:
        checks.append(
            InvestigationCheck(
                check_id="inspection_completed",
                title="Warehouse inspection",
                status="warn",
                summary="Return not yet received; inspection pending.",
            )
        )

    ci_status: CheckStatus = "fail" if facts.conflicting_inspections else "pass"
    checks.append(
        InvestigationCheck(
            check_id="inspection_findings_consistent",
            title="Inspection consistency",
            status=ci_status,
            summary="Inspection findings are consistent."
            if ci_status == "pass"
            else "Conflicting defect verification across inspections.",
        )
    )

    acc_status: CheckStatus = "fail" if facts.accessories_incomplete else "pass"
    checks.append(
        InvestigationCheck(
            check_id="accessories_verification",
            title="Accessories completeness",
            status=acc_status,
            summary="All accessories accounted for."
            if acc_status == "pass"
            else "Accessories reported incomplete.",
        )
    )

    dd_status: CheckStatus = "fail" if facts.delivery_dispute else "pass"
    checks.append(
        InvestigationCheck(
            check_id="delivery_dispute_evidence",
            title="Delivery dispute",
            status=dd_status,
            summary="No carrier or delivery damage dispute flagged."
            if dd_status == "pass"
            else "Delivery damage or carrier dispute requires review.",
            details={"delivery_issue": facts.delivery.delivery_issue if facts.delivery else None},
        )
    )

    if facts.has_completed_refund:
        checks.append(
            InvestigationCheck(
                check_id="refund_status_clear",
                title="Refund status",
                status="warn",
                summary="A completed refund already exists for this return.",
            )
        )
    else:
        checks.append(
            InvestigationCheck(
                check_id="refund_status_clear",
                title="Refund status",
                status="pass",
                summary="No completed refund blocking a new resolution path.",
            )
        )

    risk_status: CheckStatus = (
        "fail" if facts.verification_issue_count >= 2 else "pass"
    )
    checks.append(
        InvestigationCheck(
            check_id="customer_history_risk",
            title="Compound verification risk",
            status=risk_status,
            summary="Single verification dimension flagged."
            if risk_status == "pass"
            else "Multiple independent verification issues detected on this return.",
            details={"verification_issue_count": facts.verification_issue_count},
        )
    )

    safety_status: CheckStatus = "fail" if facts.unsafe_product else "pass"
    checks.append(
        InvestigationCheck(
            check_id="safety_and_warranty_gate",
            title="Safety disposition",
            status=safety_status,
            summary="No unsafe-product quarantine required."
            if safety_status == "pass"
            else "Unsafe condition recorded; block resale and escalate.",
        )
    )

    return checks


def _derive_outcome(facts: _Facts, signal: str) -> InvestigationOutcome:
    if facts.return_row.received_date and not facts.inspections:
        return "additional_inspection_required"

    if facts.unsafe_product:
        return "manual_investigation_required"

    if facts.conflicting_inspections:
        return "manual_investigation_required"

    if facts.product_mismatch:
        return "manual_investigation_required"

    if facts.serial_mismatch or facts.delivery_dispute or facts.data_record_conflict:
        return "manual_investigation_required"

    if facts.verification_issue_count >= 2:
        return "manual_investigation_required"

    if facts.policy.within_return_window is False:
        return "policy_exception_review_required"

    if facts.accessories_incomplete:
        return "policy_exception_review_required"

    defect_warranty_reason = facts.return_row.return_reason in {
        ReturnReason.DEFECTIVE.value,
        ReturnReason.NOT_FUNCTIONING.value,
    }
    if facts.has_completed_refund:
        return "eligible_for_standard_resolution"

    if (
        facts.inspections
        and any(i.defect_verified for i in facts.inspections)
        and defect_warranty_reason
        and facts.return_row.return_reason != ReturnReason.DAMAGED.value
        and facts.policy.within_warranty_period
    ):
        return "warranty_review_required"

    return "eligible_for_standard_resolution"


def _recommended_actions(facts: _Facts, outcome: InvestigationOutcome) -> list[str]:
    actions: list[str] = []
    if outcome == "additional_inspection_required":
        if facts.open_investigation_case and not facts.inspections:
            actions.append("warehouse_receive_and_inspect")
        else:
            actions.append("create_inspection_task")
    if outcome == "manual_investigation_required" and not facts.cases:
        actions.append("create_investigation_case")
    if facts.serial_mismatch:
        actions.append("verify_serial_with_supplier")
    if facts.product_mismatch:
        actions.append("confirm_product_identity")
    if outcome == "policy_exception_review_required":
        actions.append("search_return_policy")
    if outcome == "warranty_review_required":
        actions.append("open_warranty_review")
    if facts.unsafe_product:
        actions.append("quarantine_unit")
    if facts.has_completed_refund:
        actions.append("block_duplicate_refund")
    return actions


def run_investigation(session: Session, return_id: str) -> InvestigationReport | None:
    from app.database.base import utc_now
    from app.synthetic.scenarios import SCENARIO_BY_RETURN_ID

    facts = _load_facts(session, return_id)
    if facts is None:
        return None

    signal_ctx = SignalContext(
        has_completed_refund=facts.has_completed_refund,
        has_open_refund=facts.has_open_refund,
        inspection_count=len(facts.inspections),
        return_received=facts.return_row.received_date is not None,
        serial_mismatch=facts.serial_mismatch,
        product_mismatch=facts.product_mismatch,
        conflicting_inspections=facts.conflicting_inspections,
        delivery_dispute=facts.delivery_dispute,
        unsafe_product=facts.unsafe_product,
        data_record_conflict=facts.data_record_conflict,
        accessories_incomplete=facts.accessories_incomplete,
        outside_return_window=facts.policy.within_return_window is False,
        verification_issue_count=facts.verification_issue_count,
        open_investigation_case=facts.open_investigation_case,
    )
    signal = derive_primary_signal(signal_ctx)
    checks = _run_checks(facts)
    outcome = _derive_outcome(facts, signal)
    spec = SCENARIO_BY_RETURN_ID.get(return_id)

    return InvestigationReport(
        return_id=return_id,
        scenario_slug=spec.slug if spec else None,
        checks=checks,
        f2_signal=signal,
        f3_policy=facts.policy,
        f4_outcome=outcome,
        recommended_actions=_recommended_actions(facts, outcome),
        generated_at=utc_now(),
    )


def investigation_workflow_context(session: Session, facts: _Facts) -> dict[str, Any]:
    """Structured handoff facts for agents (aligned with return_workflow snapshot)."""
    from app.services.return_workflow import build_return_workflow_snapshot

    return build_return_workflow_snapshot(session, facts.return_row.return_id)
