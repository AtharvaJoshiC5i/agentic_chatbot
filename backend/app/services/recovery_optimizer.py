"""Deterministic second-life recovery optimizer (F6)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import FeasibilityStatus, ProductCondition, RecoveryMethod
from app.models.tables import Inspection, Product, RecoveryOption, Return, OrderItem


class RecoveryOptimizerError(Exception):
    def __init__(self, message: str, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


RESALE_METHODS = frozenset(
    {
        RecoveryMethod.RESELL_NEW.value,
        RecoveryMethod.OPEN_BOX.value,
        RecoveryMethod.REPAIR_RESELL.value,
        RecoveryMethod.REFURBISH_RESELL.value,
    }
)


@dataclass(frozen=True)
class RankedRecoveryOption:
    option_id: int
    recovery_method: str
    expected_net_recovery_paise: int
    feasibility_status: str
    expected_revenue_paise: int
    total_cost_paise: int
    rank: int
    eligible: bool
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class RecoveryRecommendation:
    return_id: str
    unsafe_product: bool
    ranked_options: list[RankedRecoveryOption]
    recommended_option_id: int | None
    recommended_method: str | None
    rationale: str
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "return_id": self.return_id,
            "unsafe_product": self.unsafe_product,
            "recommended_option_id": self.recommended_option_id,
            "recommended_method": self.recommended_method,
            "rationale": self.rationale,
            "requires_approval": self.requires_approval,
            "ranked_options": [
                {
                    "option_id": row.option_id,
                    "recovery_method": row.recovery_method,
                    "expected_net_recovery_paise": row.expected_net_recovery_paise,
                    "feasibility_status": row.feasibility_status,
                    "expected_revenue_paise": row.expected_revenue_paise,
                    "total_cost_paise": row.total_cost_paise,
                    "rank": row.rank,
                    "eligible": row.eligible,
                    "exclusion_reason": row.exclusion_reason,
                }
                for row in self.ranked_options
            ],
        }


def _is_unsafe_return(session: Session, return_id: str) -> bool:
    inspections = session.execute(
        select(Inspection).where(Inspection.return_id == return_id)
    ).scalars().all()
    return any(row.product_condition == ProductCondition.UNSAFE.value for row in inspections)


def _product_category(session: Session, return_id: str) -> str | None:
    return_row = session.get(Return, return_id)
    if return_row is None:
        return None
    item = session.get(OrderItem, return_row.order_item_id)
    if item is None:
        return None
    product = session.get(Product, item.product_id)
    return product.category if product else None


def list_recovery_options(session: Session, return_id: str) -> list[RecoveryOption]:
    return list(
        session.execute(
            select(RecoveryOption)
            .where(RecoveryOption.return_id == return_id)
            .order_by(RecoveryOption.expected_net_recovery.desc(), RecoveryOption.option_id)
        ).scalars()
    )


def optimize_recovery(session: Session, return_id: str) -> RecoveryRecommendation:
    if session.get(Return, return_id) is None:
        raise RecoveryOptimizerError("Return not found", "not_found")

    options = list_recovery_options(session, return_id)
    if not options:
        raise RecoveryOptimizerError("No recovery options modeled for this return", "no_options")

    unsafe = _is_unsafe_return(session, return_id)
    category = _product_category(session, return_id)

    draft_rows: list[RankedRecoveryOption] = []
    for option in options:
        eligible = True
        reason: str | None = None
        if option.feasibility_status == FeasibilityStatus.NOT_FEASIBLE.value:
            eligible = False
            reason = "marked_not_feasible"
        elif unsafe and option.recovery_method in RESALE_METHODS:
            eligible = False
            reason = "unsafe_product_resale_blocked"
        draft_rows.append(
            RankedRecoveryOption(
                option_id=option.option_id,
                recovery_method=option.recovery_method,
                expected_net_recovery_paise=option.expected_net_recovery,
                feasibility_status=option.feasibility_status,
                expected_revenue_paise=option.expected_revenue,
                total_cost_paise=option.repair_cost + option.handling_cost + option.other_cost,
                rank=0,
                eligible=eligible,
                exclusion_reason=reason,
            )
        )

    eligible_rows = sorted(
        [row for row in draft_rows if row.eligible],
        key=lambda row: (-row.expected_net_recovery_paise, row.recovery_method, row.option_id),
    )
    rank_by_id = {row.option_id: index for index, row in enumerate(eligible_rows, start=1)}
    ranked_rows = [
        RankedRecoveryOption(
            option_id=row.option_id,
            recovery_method=row.recovery_method,
            expected_net_recovery_paise=row.expected_net_recovery_paise,
            feasibility_status=row.feasibility_status,
            expected_revenue_paise=row.expected_revenue_paise,
            total_cost_paise=row.total_cost_paise,
            rank=rank_by_id.get(row.option_id, 0),
            eligible=row.eligible,
            exclusion_reason=row.exclusion_reason,
        )
        for row in draft_rows
    ]
    ranked_rows.sort(key=lambda row: (row.rank if row.rank else 999, row.option_id))

    recommended: RankedRecoveryOption | None = eligible_rows[0] if eligible_rows else None
    requires_approval = False
    rationale = "No eligible recovery path after policy filters."

    if recommended is not None:
        requires_approval = (
            recommended.feasibility_status == FeasibilityStatus.REQUIRES_APPROVAL.value
        )
        rationale = (
            f"Selected {recommended.recovery_method} with highest net recovery "
            f"({recommended.expected_net_recovery_paise} paise)"
        )
        if unsafe:
            rationale += " while blocking resale paths due to unsafe product disposition."
        elif category:
            rationale += f" for category {category}."
        else:
            rationale += "."

    return RecoveryRecommendation(
        return_id=return_id,
        unsafe_product=unsafe,
        ranked_options=ranked_rows,
        recommended_option_id=recommended.option_id if recommended else None,
        recommended_method=recommended.recovery_method if recommended else None,
        rationale=rationale,
        requires_approval=requires_approval,
    )
