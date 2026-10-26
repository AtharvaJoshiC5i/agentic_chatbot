"""Deterministic return-policy evaluation (F3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# Mirrors policy documents / scripts/unstructured/context.py
RETURN_WINDOW_DAYS: dict[str, int] = {
    "electronics": 30,
    "fashion": 15,
    "home_appliances": 30,
    "accessories": 30,
}

DEFAULT_RETURN_WINDOW_DAYS = 30


def normalize_category(category: str | None) -> str:
    if not category:
        return "accessories"
    key = category.strip().lower()
    if key in RETURN_WINDOW_DAYS:
        return key
    return "accessories"


def days_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    delta = end.date() - start.date()
    return int(delta.days)


@dataclass(frozen=True)
class PolicyEvaluation:
    """F3 — structured policy snapshot used by the investigation engine."""

    product_category: str
    return_window_days: int
    days_after_delivery: int | None
    within_return_window: bool | None
    warranty_months: int
    order_age_days: int | None
    within_warranty_period: bool | None
    delivery_date: datetime | None
    return_request_date: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "product_category": self.product_category,
            "return_window_days": self.return_window_days,
            "days_after_delivery": self.days_after_delivery,
            "within_return_window": self.within_return_window,
            "warranty_months": self.warranty_months,
            "order_age_days": self.order_age_days,
            "within_warranty_period": self.within_warranty_period,
            "delivery_date": self.delivery_date,
            "return_request_date": self.return_request_date,
        }


def evaluate_policy(
    *,
    product_category: str | None,
    warranty_months: int,
    delivery_date: datetime | None,
    return_request_date: datetime | None,
    order_date: datetime | None,
) -> PolicyEvaluation:
    category = normalize_category(product_category)
    window_days = RETURN_WINDOW_DAYS.get(category, DEFAULT_RETURN_WINDOW_DAYS)
    days_after_delivery = days_between(delivery_date, return_request_date)
    within_window: bool | None
    if days_after_delivery is None:
        within_window = None
    else:
        within_window = days_after_delivery <= window_days

    order_age_days = days_between(order_date, return_request_date)
    within_warranty: bool | None
    if warranty_months <= 0:
        within_warranty = False
    elif order_date is None or return_request_date is None:
        within_warranty = None
    else:
        # Approximate calendar months as 30-day blocks (deterministic, documented).
        warranty_end = order_date + timedelta(days=warranty_months * 30)
        within_warranty = return_request_date <= warranty_end

    return PolicyEvaluation(
        product_category=category,
        return_window_days=window_days,
        days_after_delivery=days_after_delivery,
        within_return_window=within_window,
        warranty_months=warranty_months,
        order_age_days=order_age_days,
        within_warranty_period=within_warranty,
        delivery_date=delivery_date,
        return_request_date=return_request_date,
    )
