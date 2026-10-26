"""Batch A (part 2): ten warranty documents (product-level and category-level)."""

from __future__ import annotations

from collections import Counter

from .context import ShopSphereData, inr
from .corpus import Corpus
from .render import Doc

# Product-level warranties for the named catalogue products (PRODUCT_LIBRARY).
PRODUCT_WARRANTIES = {
    "SoundPeak Wireless Headphones Pro": {
        "code": "WTY-SP-HP-2025-01",
        "file": "warranty_soundpeak_wireless_headphones_pro.pdf",
        "covered": [
            "Failure of either driver, including one-sided audio or distortion at normal volume.",
            "Bluetooth pairing or connection failures not resolved by a factory reset.",
            "Battery that holds less than 70% of rated capacity within the warranty period.",
            "Charging port failure without physical damage.",
        ],
        "excluded": [
            "Physical damage, cracked headband or torn ear cushions from use.",
            "Liquid damage.",
            "Units whose serial label is missing or does not match the purchase record (additional verification required before any claim).",
        ],
        "serial": "Serial-tracked. The serial on the unit must match order_items.purchased_serial_number.",
    },
    "TechNova Ultrabook 14": {
        "code": "WTY-TN-UB14-2025-01",
        "file": "warranty_technova_ultrabook_14.pdf",
        "covered": [
            "Mainboard, memory and storage failures.",
            "Display defects (dead pixels above the published threshold, backlight failure).",
            "Keyboard and trackpad failures not caused by impact or liquid.",
            "Battery below 80% of design capacity within 12 months; below 60% within 24 months.",
        ],
        "excluded": [
            "Accidental damage (impact, cracked keys, bent chassis) unless an accidental damage plan was purchased; such units may still be repaired at cost.",
            "Software issues and data loss. Customers must back up data before service.",
        ],
        "serial": "Serial-tracked. Service is booked against the serial on the order line.",
    },
    "HomeHive Air Purifier 300": {
        "code": "WTY-HH-AP300-2025-02",
        "file": "warranty_homehive_air_purifier_300.docx",
        "covered": [
            "Fan motor and motor control board.",
            "Air quality sensor and display.",
            "Power supply and power inlet assembly.",
        ],
        "excluded": [
            "Filters (consumable; 6 month replacement interval).",
            "Damage from use on unstable voltage without a stabiliser where the manual requires one.",
        ],
        "serial": "Serial-tracked at dispatch where a serial is recorded on the order line.",
        "safety": "Any unit showing overheating, scorch marks, melting or burning odour is not repaired under warranty. It is replaced or refunded and the returned unit is quarantined for recycle or dispose only.",
    },
    "FlexFit USB-C Hub 7-in-1": {
        "code": "WTY-FF-HUB7-2025-01",
        "file": "warranty_flexfit_usb_c_hub_7_in_1.docx",
        "covered": [
            "Port failures (HDMI, USB-A, USB-C power delivery, SD/microSD, Ethernet).",
            "Intermittent disconnection under rated load.",
        ],
        "excluded": ["Bent connectors and cable strain damage.", "Use with chargers above the rated 100 W input."],
        "serial": "Not serial-tracked by default; where a serial is recorded on the order line it is checked on return.",
    },
    "UrbanWeave Classic Cotton Shirt": {
        "code": "WTY-UW-SHIRT-2025-01",
        "file": "warranty_urbanweave_classic_cotton_shirt.pdf",
        "covered": [],
        "excluded": [],
        "serial": "Not serial-tracked. Identity is confirmed from the SKU label and brand tags.",
    },
}


def _product_ids_for(data: ShopSphereData, name: str) -> list[str]:
    return sorted(pid for pid, p in data.products.items() if p["product_name"] == name)


def _product_warranty(data: ShopSphereData, name: str, spec: dict) -> tuple[Doc, str]:
    product_ids = _product_ids_for(data, name)
    sample = data.products[product_ids[0]]
    months = sample["warranty_months"]
    doc = Doc(
        title=f"Warranty Terms — {name}",
        subtitle=f"{sample['brand']} · category {sample['category']}",
        header=[
            ("Warranty document", spec["code"]),
            ("Version", "1.0"),
            ("Effective date", "2025-01-01"),
            ("Brand", sample["brand"]),
            ("Category", sample["category"]),
            ("Warranty period (months)", str(months)),
            ("Catalogue product IDs", ", ".join(product_ids)),
            ("List price", inr(sample["original_price"])),
        ],
        footer=f"{spec['code']} — Internal use only — ShopSphere Retail.",
    )
    if months == 0:
        doc.h("1. Warranty coverage")
        doc.p(
            f"{name} carries no manufacturer warranty (0 months). Quality issues are handled only under the "
            "Fashion and Apparel Return Policy (POL-FASH-2024-02) within its 15-day return window. "
            "Manufacturing defects reported after the window may be reviewed as a policy exception by a "
            "returns supervisor; they are not warranty claims."
        )
        doc.h("2. Identity checks")
        doc.p(spec["serial"])
        doc.h("3. Care instructions referenced in defect assessment")
        doc.bullets(["Machine wash cold, inside out.", "Do not bleach.", "Warm iron.", "Shrinkage up to 3% after first wash is within specification."])
        return doc, product_ids[0]

    doc.h("1. Warranty period")
    doc.p(
        f"The warranty runs for {months} months from the delivery date recorded in the ShopSphere delivery "
        "system. During the category return window a fault is handled as a return; after the window it is "
        "handled as a warranty claim (repair, replacement, or refund at ShopSphere's discretion)."
    )
    doc.h("2. What is covered")
    doc.bullets(spec["covered"])
    doc.h("3. What is not covered")
    doc.bullets(spec["excluded"])
    doc.h("4. Identity and serial verification")
    doc.p(spec["serial"])
    if "safety" in spec:
        doc.h("5. Safety")
        doc.p(spec["safety"])
    doc.h("Claim procedure")
    doc.bullets(
        [
            "Customer raises a claim quoting order ID; support opens a return with reason defective or not_functioning.",
            "Warehouse inspection verifies the defect (defect_verified = Yes) before the claim is accepted.",
            "An investigation case of type warranty_review is opened when the claim falls outside the return window.",
        ]
    )
    return doc, product_ids[0]


def _tiers(data: ShopSphereData, category: str) -> str:
    months = sorted({p["warranty_months"] for p in data.products.values() if p["category"] == category})
    parts = [str(m) for m in months]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " or " + parts[-1]


def _tier_table(data: ShopSphereData, category: str) -> list[list[str]]:
    counts = Counter(p["warranty_months"] for p in data.products.values() if p["category"] == category)
    return [[f"{months} months", str(counts[months])] for months in sorted(counts)]


def _category_warranty(data: ShopSphereData, category: str, code: str, title: str, paragraphs: list[tuple[str, str]], bullets: list[str]) -> Doc:
    doc = Doc(
        title=title,
        subtitle=f"ShopSphere Retail — category {category}",
        header=[
            ("Warranty document", code),
            ("Version", "2.0"),
            ("Effective date", "2025-01-01"),
            ("Category", category),
            ("Products in catalogue", str(sum(1 for p in data.products.values() if p["category"] == category))),
        ],
        footer=f"{code} — Internal use only — ShopSphere Retail.",
    )
    doc.h("Warranty tiers in the current catalogue")
    doc.p("The warranty period for each product is recorded in products.warranty_months. Current distribution:")
    doc.table(["Warranty period", "Number of products"], _tier_table(data, category))
    for heading, text in paragraphs:
        doc.h(heading)
        doc.p(text)
    doc.h("Standard conditions")
    doc.bullets(bullets)
    return doc


def build(corpus: Corpus, data: ShopSphereData) -> None:
    for name, spec in PRODUCT_WARRANTIES.items():
        doc, product_id = _product_warranty(data, name, spec)
        corpus.add_doc(doc, spec["file"], "warranty", effective_date="2025-01-01", product_id=product_id, policy_version="1.0")

    category_docs = [
        (
            "electronics",
            "WTY-ELEC-2025-01",
            "Electronics Category Warranty Terms",
            "warranty_category_electronics.docx",
            [
                ("Tier definitions", f"Electronics in the current catalogue carry {_tiers(data, 'electronics')} months of warranty. Audio products typically carry 12 months (SoundPeak Wireless Headphones Pro: 12). Laptops typically carry 24 months (TechNova Ultrabook 14: 24). A product with 0 months of warranty would be covered only by the 30-day return window in POL-ELEC-2024-03."),
                ("Return window versus warranty", "Within 30 days from delivery a fault is processed as a return. From day 31 until the end of the warranty period it is processed as a warranty claim. A change-of-mind request after day 30 is not a warranty claim and is routed to policy exception review."),
            ],
            [
                "Warranty starts on the delivery date.",
                "The serial number on the returned unit must match the purchased serial number; a mismatch requires additional verification before any warranty action.",
                "Repaired units carry the remainder of the original warranty or 90 days, whichever is longer.",
            ],
        ),
        (
            "home_appliances",
            "WTY-HOME-2025-01",
            "Home Appliances Warranty and Service Terms",
            "warranty_category_home_appliances.pdf",
            [
                ("On-site service", "Appliances above 10 kg are serviced on site by an authorised partner. Air purifiers and small appliances are collected for bench service."),
                ("Safety exclusions", "A unit classified as unsafe on inspection is not repaired. The customer receives a replacement or refund and the unit is quarantined (see RFB-SAF-2025-02)."),
            ],
            [
                "HomeHive Air Purifier 300 carries 24 months.",
                "Consumables (filters, gaskets, bulbs) are excluded.",
                "Installation damage by non-authorised installers is excluded.",
            ],
        ),
        (
            "accessories",
            "WTY-ACC-2025-01",
            "Accessories Limited Warranty",
            "warranty_category_accessories.docx",
            [
                ("Coverage", f"Accessories in the current catalogue carry {_tiers(data, 'accessories')} months. FlexFit USB-C Hub 7-in-1 carries 6 months. Accessories with 0 months are covered by the 30-day return window only."),
                ("Replacement first", "Accessory warranty claims are resolved by like-for-like replacement where stock exists; refund otherwise."),
            ],
            ["Physical damage to connectors is excluded.", "Missing packed items are a return-policy matter, not a warranty matter."],
        ),
        (
            "fashion",
            "WTY-FASH-2025-01",
            "Fashion Quality Assurance Terms",
            "warranty_category_fashion.pdf",
            [
                ("Coverage", f"Fashion items in the current catalogue carry {_tiers(data, 'fashion')} months of warranty (UrbanWeave Classic Cotton Shirt: 0). Footwear and outerwear with a non-zero period are covered against sole separation or zipper failure, as recorded in the catalogue."),
                ("Quality complaints", "Seam failure, colour bleeding or misprint reported within the 15-day return window are handled as returns. After the window, items with 0 months of warranty may be considered only as a supervisor-approved policy exception."),
            ],
            ["Normal wear, pilling and fading are excluded.", "Items altered after delivery are excluded."],
        ),
    ]
    for category, code, title, filename, paragraphs, bullets in category_docs:
        doc = _category_warranty(data, category, code, title, paragraphs, bullets)
        corpus.add_doc(doc, filename, "warranty", effective_date="2025-01-01", policy_version="2.0")

    claims = Doc(
        title="Warranty Claims Handling Procedure",
        subtitle="ShopSphere Retail — cross-category procedure for support and returns analysts",
        header=[("Procedure", "WTY-PROC-2025-03"), ("Version", "1.2"), ("Effective date", "2025-03-01"), ("Applies to", "All categories with warranty_months > 0")],
        footer="WTY-PROC-2025-03 v1.2 — Internal use only — ShopSphere Retail.",
    )
    claims.h("1. Determine the route")
    claims.table(
        ["Days since delivery", "Warranty months", "Route"],
        [
            ["Within category return window", "Any", "Return (category return policy)"],
            ["After window, within warranty period", "> 0", "Warranty claim; open warranty_review case"],
            ["After warranty period", "Any", "Out-of-warranty repair at cost, or policy exception review"],
            ["Any", "0", "Return window only; no warranty claim"],
        ],
    )
    claims.h("2. Evidence required")
    claims.bullets(
        [
            "Order ID, return ID and product ID.",
            "Purchased serial number (serial-tracked products) and the serial read from the returned unit.",
            "Inspection report with defect_verified = Yes.",
        ]
    )
    claims.h("3. Worked example")
    r112 = data.get("R112")
    claims.p(
        f"Return {r112.return_id} (order {r112['order_id']}): {r112['product_name']}, serial "
        f"{r112['purchased_serial_number']}, delivered {r112['delivery_date'][:10]}, return requested "
        f"{r112['request_date'][:10]} ({r112.days_after_delivery} days after delivery). The product carries "
        f"{r112['warranty_months']} months of warranty, so a verified failure is well within the warranty period."
    )
    claims.h("4. Outcomes")
    claims.bullets(
        [
            "Repair: create a repair task; repaired unit returned to the customer.",
            "Replacement: dispatch a like-for-like unit; the returned unit follows the recovery framework.",
            "Refund: only with approvals per the category policy thresholds.",
        ]
    )
    corpus.add_doc(claims, "warranty_claims_handling_procedure.docx", "warranty", effective_date="2025-03-01", policy_version="1.2")
