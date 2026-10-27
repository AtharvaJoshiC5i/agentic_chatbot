"""Generate ShopSphere structured synthetic datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from faker import Faker

from app.models.enums import (
    AccountStatus,
    ApprovalStatus,
    CasePriority,
    CaseStatus,
    DeliveryStatus,
    FeasibilityStatus,
    InspectionResult,
    IssueType,
    OrderStatus,
    ProductCondition,
    ProductUnitStatus,
    RecoveryMethod,
    RefundStatus,
    RequestedResolution,
    ReturnReason,
    ReturnStatus,
    TaskStatus,
)
from app.synthetic.bulk import build_bulk_returns
from app.synthetic.catalog import CATALOG, VARIANTS
from app.synthetic.constants import BRANDS_BY_CATEGORY, CATEGORY_WEIGHTS, RANDOM_SEED, VOLUMES
from app.synthetic.scenarios import (
    SCENARIO_BY_RETURN_ID,
    ScenarioReturnProfile,
    scenario_profiles,
)

UTC = timezone.utc


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _paise(rupees: float) -> int:
    return int(round(rupees * 100))


def _id_num(prefix: str, number: int, width: int = 5) -> str:
    return f"{prefix}{number:0{width}d}"


PRODUCT_LIBRARY: dict[str, dict[str, Any]] = {
    "headphones": {
        "product_name": "SoundPeak Wireless Headphones Pro",
        "category": "electronics",
        "brand": "SoundPeak",
        "original_price": _paise(4999),
        "warranty_months": 12,
        "serial_tracked": True,
    },
    "laptop": {
        "product_name": "TechNova Ultrabook 14",
        "category": "electronics",
        "brand": "TechNova",
        "original_price": _paise(68999),
        "warranty_months": 24,
        "serial_tracked": True,
    },
    "fashion_item": {
        "product_name": "UrbanWeave Classic Cotton Shirt",
        "category": "fashion",
        "brand": "UrbanWeave",
        "original_price": _paise(1899),
        "warranty_months": 0,
        "serial_tracked": False,
    },
    "appliance": {
        "product_name": "HomeHive Air Purifier 300",
        "category": "home_appliances",
        "brand": "HomeHive",
        "original_price": _paise(12999),
        "warranty_months": 24,
        "serial_tracked": True,
    },
    "accessory": {
        "product_name": "FlexFit USB-C Hub 7-in-1",
        "category": "accessories",
        "brand": "FlexFit",
        "original_price": _paise(2499),
        "warranty_months": 6,
        "serial_tracked": False,
    },
}


@dataclass
class SyntheticDataBundle:
    customers: list[dict[str, Any]] = field(default_factory=list)
    suppliers: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    orders: list[dict[str, Any]] = field(default_factory=list)
    order_items: list[dict[str, Any]] = field(default_factory=list)
    product_units: list[dict[str, Any]] = field(default_factory=list)
    deliveries: list[dict[str, Any]] = field(default_factory=list)
    returns: list[dict[str, Any]] = field(default_factory=list)
    inspections: list[dict[str, Any]] = field(default_factory=list)
    refunds: list[dict[str, Any]] = field(default_factory=list)
    investigation_cases: list[dict[str, Any]] = field(default_factory=list)
    recovery_options: list[dict[str, Any]] = field(default_factory=list)
    recovery_tasks: list[dict[str, Any]] = field(default_factory=list)


def generate_synthetic_data(seed: int = RANDOM_SEED) -> SyntheticDataBundle:
    rng = np.random.default_rng(seed)
    # Second, independent stream for realism logic: leaves the original draw order (and
    # therefore the reserved R101-R115 scenario rows) untouched.
    rng2 = np.random.default_rng(seed + 7919)
    product_nouns: dict[str, str] = {}
    fake = Faker("en_IN")
    Faker.seed(seed)

    bundle = SyntheticDataBundle()
    now = _utc(datetime(2026, 3, 20, 12, 0, 0))

    categories = list(CATEGORY_WEIGHTS.keys())
    cat_probs = np.array([CATEGORY_WEIGHTS[c] for c in categories], dtype=float)
    cat_probs /= cat_probs.sum()

    # --- Suppliers ---
    for index in range(1, VOLUMES.suppliers + 1):
        category = categories[int(rng.choice(len(categories), p=cat_probs))]
        bundle.suppliers.append(
            {
                "supplier_id": _id_num("S", index, 3),
                "supplier_name": fake.company(),
                "category": category,
                "contact_email": f"supplier{index}@shopsphere.invalid",
            }
        )

    suppliers_by_category: dict[str, list[str]] = {c: [] for c in categories}
    for supplier in bundle.suppliers:
        suppliers_by_category[supplier["category"]].append(supplier["supplier_id"])

    # --- Customers ---
    for index in range(1, VOLUMES.customers + 1):
        created = now - timedelta(days=int(rng.integers(30, 900)))
        bundle.customers.append(
            {
                "customer_id": _id_num("C", index),
                "customer_name": fake.name(),
                "email": f"customer{index}@shopsphere.invalid",
                "account_created_at": created,
                "account_status": AccountStatus.ACTIVE.value,
            }
        )

    # --- Products (catalog + scenario-specific) ---
    product_ids_by_key: dict[str, str] = {}
    for index in range(1, VOLUMES.products + 1):
        category = categories[int(rng.choice(len(categories), p=cat_probs))]
        supplier_id = suppliers_by_category[category][int(rng.integers(0, len(suppliers_by_category[category])))]
        rng.uniform(499, 75000)  # draw kept so later random streams stay identical
        fake.catch_phrase()
        fake.company()
        rng.choice([0, 6, 12, 24], p=[0.2, 0.2, 0.4, 0.2])

        model, noun, low, high, warranties = CATALOG[category][int(rng2.integers(len(CATALOG[category])))]
        brand = BRANDS_BY_CATEGORY[category][int(rng2.integers(len(BRANDS_BY_CATEGORY[category])))]
        variant = VARIANTS[int(rng2.integers(len(VARIANTS)))]
        price_rupees = int(round(float(rng2.uniform(low, high)) / 50) * 50) - 1
        product_id = _id_num("P", index)
        product_nouns[product_id] = noun
        bundle.products.append(
            {
                "product_id": product_id,
                "product_name": f"{brand} {model}{variant}",
                "category": category,
                "brand": brand,
                "original_price": _paise(price_rupees),
                "warranty_months": int(warranties[int(rng2.integers(len(warranties)))]),
                "serial_tracked": category == "electronics" or category == "home_appliances",
                "supplier_id": supplier_id,
                "stock_on_hand": 0 if index % 8 == 0 else 5 + (index * 7) % 40,
            }
        )

    for scenario_id, profile in scenario_profiles().items():
        product_id = f"P_{scenario_id}"
        template = PRODUCT_LIBRARY[profile.product_key]
        category = template["category"]
        supplier_id = suppliers_by_category[category][0]
        bundle.products.append(
            {
                "product_id": product_id,
                "product_name": template["product_name"],
                "category": category,
                "brand": template["brand"],
                "original_price": template["original_price"],
                "warranty_months": template["warranty_months"],
                "serial_tracked": template["serial_tracked"],
                "supplier_id": supplier_id,
                "stock_on_hand": 20,
            }
        )
        product_ids_by_key[scenario_id] = product_id
        product_nouns[product_id] = template["product_name"].split(" ", 1)[-1].lower()

    # --- Orders & items (bulk) ---
    order_item_id = 1
    order_item_ids_for_returns: list[int] = []

    for index in range(1, VOLUMES.orders - len(scenario_profiles()) + 1):
        customer_id = _id_num("C", int(rng.integers(1, VOLUMES.customers + 1)))
        order_date = now - timedelta(days=int(rng.integers(10, 400)))
        bundle.orders.append(
            {
                "order_id": _id_num("O", index),
                "customer_id": customer_id,
                "order_date": order_date,
                "total_amount": 0,
                "order_status": OrderStatus.FULFILLED.value,
            }
        )

    # Scenario orders O101..O115
    scenario_order_items: dict[str, int] = {}
    for scenario_num, return_id in enumerate(scenario_profiles().keys(), start=101):
        profile = scenario_profiles()[return_id]
        customer_id = _id_num("C", scenario_num)
        order_id = f"O{return_id[1:]}"
        order_date = now - timedelta(days=profile.order_age_days)
        product_id = product_ids_by_key[return_id]
        product = next(p for p in bundle.products if p["product_id"] == product_id)
        bundle.orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": order_date,
                "total_amount": product["original_price"],
                "order_status": OrderStatus.FULFILLED.value,
            }
        )
        item = {
            "order_item_id": order_item_id,
            "order_id": order_id,
            "product_id": product_id,
            "quantity": 1,
            "unit_price": product["original_price"],
            "purchased_serial_number": profile.purchased_serial,
        }
        bundle.order_items.append(item)
        scenario_order_items[return_id] = order_item_id
        order_item_ids_for_returns.append(order_item_id)
        if profile.purchased_serial:
            bundle.product_units.append(
                {
                    "product_unit_id": len(bundle.product_units) + 1,
                    "order_item_id": order_item_id,
                    "serial_number": profile.purchased_serial,
                    "unit_status": ProductUnitStatus.DELIVERED.value,
                }
            )
        order_item_id += 1

    # Fill remaining order items across bulk orders
    bulk_orders = [o for o in bundle.orders if not o["order_id"].startswith("O10") and not o["order_id"].startswith("O11")]
    # Fix: scenario orders are O101-O115 - bulk are O00001 style
    bulk_orders = [o for o in bundle.orders if o["order_id"].startswith("O0")]

    while len(bundle.order_items) < VOLUMES.order_items:
        order = bulk_orders[int(rng.integers(0, len(bulk_orders)))]
        product = bundle.products[int(rng.integers(0, VOLUMES.products))]
        quantity = int(rng.choice([1, 1, 1, 2, 3]))
        line_total = product["original_price"] * quantity
        order["total_amount"] += line_total
        serial = None
        if product["serial_tracked"]:
            serial = f"SN{order_item_id:06d}"
        bundle.order_items.append(
            {
                "order_item_id": order_item_id,
                "order_id": order["order_id"],
                "product_id": product["product_id"],
                "quantity": quantity,
                "unit_price": product["original_price"],
                "purchased_serial_number": serial,
            }
        )
        if serial:
            for unit_offset in range(quantity):
                unit_serial = serial if quantity == 1 else f"{serial}-{unit_offset + 1}"
                bundle.product_units.append(
                    {
                        "product_unit_id": len(bundle.product_units) + 1,
                        "order_item_id": order_item_id,
                        "serial_number": unit_serial,
                        "unit_status": ProductUnitStatus.DELIVERED.value,
                    }
                )
        if len(order_item_ids_for_returns) < VOLUMES.returns - len(scenario_profiles()):
            if rng.random() < 0.2:
                order_item_ids_for_returns.append(order_item_id)
        order_item_id += 1

    # Ensure enough candidate order items for non-scenario returns
    while len(order_item_ids_for_returns) < VOLUMES.returns - len(scenario_profiles()):
        order_item_ids_for_returns.append(int(rng.integers(1, order_item_id)))

    # --- Deliveries (one per order) ---
    for order in bundle.orders:
        order_date = order["order_date"]
        dispatch_delay = int(rng.integers(1, 4))
        delivery_delay = int(rng.integers(1, 6))
        dispatch_date = order_date + timedelta(days=dispatch_delay)
        delivery_date = dispatch_date + timedelta(days=delivery_delay)
        delivery_issue = None
        if order["order_id"] == "O104":
            delivery_issue = "Carton crushed; visible impact damage on delivery scan."
        bundle.deliveries.append(
            {
                "delivery_id": f"D{order['order_id'][1:]}",
                "order_id": order["order_id"],
                "dispatch_date": dispatch_date,
                "delivery_date": delivery_date,
                "delivery_status": DeliveryStatus.DELIVERED.value,
                "delivery_issue": delivery_issue,
            }
        )

    # --- Returns: scenarios first ---
    inspection_id = 1
    refund_id = 1
    case_id = 1

    def add_inspection(
        return_id: str,
        profile: ScenarioReturnProfile | None,
        inspection_date: datetime,
        *,
        defect_verified: bool,
        result: InspectionResult,
        notes: str,
        returned_serial: str | None,
        condition: ProductCondition,
    ) -> None:
        nonlocal inspection_id
        bundle.inspections.append(
            {
                "inspection_id": inspection_id,
                "return_id": return_id,
                "inspection_date": inspection_date,
                "returned_serial_number": returned_serial,
                "product_condition": condition.value,
                "accessories_complete": profile.accessories_complete if profile else True,
                "defect_verified": defect_verified,
                "inspection_result": result.value,
                "inspector_notes": notes,
            }
        )
        inspection_id += 1

    for return_id, profile in scenario_profiles().items():
        order = next(o for o in bundle.orders if o["order_id"] == f"O{return_id[1:]}")
        delivery = next(d for d in bundle.deliveries if d["order_id"] == order["order_id"])
        request_date = delivery["delivery_date"] + timedelta(days=profile.days_after_delivery)
        received_date = request_date + timedelta(days=int(rng.integers(2, 5)))
        bundle.returns.append(
            {
                "return_id": return_id,
                "order_item_id": scenario_order_items[return_id],
                "request_date": request_date,
                "return_reason": profile.return_reason.value,
                "customer_description": SCENARIO_BY_RETURN_ID[return_id].notes,
                "requested_resolution": RequestedResolution.REFUND.value,
                "return_status": profile.return_status.value,
                "received_date": received_date if profile.return_status != ReturnStatus.REQUESTED else None,
            }
        )
        if profile.inspection_count > 0 and profile.product_condition is not None:
            base_date = received_date + timedelta(days=1)
            if profile.conflicting_inspections:
                add_inspection(
                    return_id,
                    profile,
                    base_date,
                    defect_verified=True,
                    result=InspectionResult.PASS,
                    notes="Initial inspection indicates functional motor assembly.",
                    returned_serial=profile.returned_serial,
                    condition=ProductCondition.DEFECTIVE,
                )
                add_inspection(
                    return_id,
                    profile,
                    base_date + timedelta(hours=6),
                    defect_verified=False,
                    result=InspectionResult.FAIL,
                    notes="Second inspection disputes defect; conflicting technician findings.",
                    returned_serial=profile.returned_serial,
                    condition=ProductCondition.DEFECTIVE,
                )
            else:
                notes = "Scenario inspection record."
                if return_id == "R102":
                    notes = (
                        "Returned unit serial HP9012 does not match purchase record HP9081. "
                        "Additional verification required."
                    )
                if return_id == "R111":
                    notes = "Received SKU label does not match ordered fashion item."
                if return_id == "R114":
                    notes = "Return reason references size mismatch but line item is accessory SKU."
                add_inspection(
                    return_id,
                    profile,
                    base_date,
                    defect_verified=profile.defect_verified,
                    result=InspectionResult.PASS if profile.defect_verified else InspectionResult.INCONCLUSIVE,
                    notes=notes,
                    returned_serial=profile.returned_serial,
                    condition=profile.product_condition,
                )
        if profile.completed_refund:
            bundle.refunds.append(
                {
                    "refund_id": refund_id,
                    "return_id": return_id,
                    "refund_amount": PRODUCT_LIBRARY[profile.product_key]["original_price"],
                    "refund_status": RefundStatus.COMPLETED.value,
                    "approval_status": ApprovalStatus.APPROVED.value,
                    "processed_date": received_date + timedelta(days=3),
                    "idempotency_key": f"refund-{return_id}-primary",
                }
            )
            refund_id += 1
        if profile.open_case and profile.case_issue_type is not None:
            bundle.investigation_cases.append(
                {
                    "case_id": case_id,
                    "return_id": return_id,
                    "issue_type": profile.case_issue_type.value,
                    "priority": CasePriority.HIGH.value
                    if return_id in {"R102", "R115"}
                    else CasePriority.MEDIUM.value,
                    "assigned_to": "analyst_02",
                    "case_status": CaseStatus.IN_PROGRESS.value,
                    "created_at": received_date + timedelta(days=2),
                    "due_date": received_date + timedelta(days=7),
                    "resolution_notes": None,
                }
            )
            case_id += 1

    # Open refund requests that belong to the reserved scenarios (explicit, not random).
    for return_id, key in (("R107", "headphones"), ("R108", "laptop"), ("R110", "appliance")):
        bundle.refunds.append(
            {
                "refund_id": refund_id,
                "return_id": return_id,
                "refund_amount": PRODUCT_LIBRARY[key]["original_price"],
                "refund_status": RefundStatus.REQUESTED.value,
                "approval_status": ApprovalStatus.PENDING.value,
                "processed_date": None,
                "idempotency_key": f"refund-{return_id}-pending",
            }
        )
        refund_id += 1

    # --- Bulk returns R116+ and everything that hangs off them ---
    build_bulk_returns(bundle, rng2, now, product_nouns)

    _finalize_order_totals(bundle)
    _renumber_product_units(bundle)
    _assert_volumes(bundle)
    return bundle


def _finalize_order_totals(bundle: SyntheticDataBundle) -> None:
    totals: dict[str, int] = {}
    for item in bundle.order_items:
        totals[item["order_id"]] = totals.get(item["order_id"], 0) + item["unit_price"] * item["quantity"]
    for order in bundle.orders:
        if order["order_id"] in totals:
            order["total_amount"] = totals[order["order_id"]]


def _renumber_product_units(bundle: SyntheticDataBundle) -> None:
    for index, unit in enumerate(bundle.product_units, start=1):
        unit["product_unit_id"] = index


def _assert_volumes(bundle: SyntheticDataBundle) -> None:
    assert len(bundle.customers) == VOLUMES.customers
    assert len(bundle.suppliers) == VOLUMES.suppliers
    assert len(bundle.products) == VOLUMES.products + len(scenario_profiles())
    assert len(bundle.orders) == VOLUMES.orders
    assert len(bundle.order_items) == VOLUMES.order_items
    assert len(bundle.deliveries) == VOLUMES.deliveries
    assert len(bundle.returns) == VOLUMES.returns
    assert len(bundle.inspections) == VOLUMES.inspections
    assert len(bundle.refunds) == VOLUMES.refunds
    assert len(bundle.investigation_cases) == VOLUMES.investigation_cases
    assert len(bundle.recovery_options) == VOLUMES.recovery_options
    assert len(bundle.recovery_tasks) == VOLUMES.recovery_tasks
    for return_id in scenario_profiles():
        assert any(row["return_id"] == return_id for row in bundle.returns)
