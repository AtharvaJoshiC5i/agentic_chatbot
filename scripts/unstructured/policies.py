"""Batch A (part 1): five return policy documents."""

from __future__ import annotations

from .context import RETURN_WINDOW_DAYS
from .corpus import Corpus
from .render import Doc

APPROVAL_THRESHOLDS = [
    ["Up to INR 10,000", "Returns analyst", "Every refund raised by the returns investigation assistant needs a human approval before execution."],
    ["INR 10,000.01 to INR 50,000", "Returns supervisor", "Analyst recommendation plus supervisor sign-off."],
    ["Above INR 50,000", "Returns supervisor and Finance controller", "Dual approval; inspection report must be attached."],
    ["Any amount with an open investigation case", "Returns supervisor", "Refund is held until the case is resolved."],
]

COMMON_REFUND_RULES = [
    "A return may have at most one completed refund. Before any refund is requested, the refunds ledger must be checked; if a completed refund already exists for the return_id, no further refund may be requested or executed.",
    "Refunds are issued to the original payment method within 5–7 business days of approval. Store credit is issued only when the customer selects it.",
    "Refund amounts may not exceed the unit price paid on the order line (order_items.unit_price), excluding any promotional cashback already reversed.",
]

NEUTRAL_LANGUAGE = (
    "Investigation notes must describe evidence, not customer intent. Where records disagree "
    "(for example serial numbers or SKUs), the outcome is recorded as “additional verification "
    "required” and the case is routed for manual review."
)


def _policy_header(policy_id: str, version: str, effective: str, category: str, window: str, owner: str) -> list[tuple[str, str]]:
    return [
        ("Policy ID", policy_id),
        ("Version", version),
        ("Effective date", effective),
        ("Applicable category", category),
        ("Return window (days)", window),
        ("Policy owner", owner),
        ("Review cycle", "Annual, or earlier on regulatory change"),
    ]


def electronics() -> tuple[Doc, dict]:
    window = RETURN_WINDOW_DAYS["electronics"]
    doc = Doc(
        title="Electronics Return Policy",
        subtitle="ShopSphere Retail — serial-tracked electronics (audio, laptops, wearables, small devices)",
        header=_policy_header("POL-ELEC-2024-03", "3.2", "2025-01-01", "electronics", str(window), "Returns Policy Office, Mumbai"),
        footer="POL-ELEC-2024-03 v3.2 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose and scope")
    doc.p(
        "This policy defines when electronics purchased on ShopSphere may be returned, what evidence is "
        "required, and how refunds are approved. It applies to every product whose catalogue category is "
        "electronics, including SoundPeak audio products and TechNova laptops. Serial-tracked products are "
        "subject to the additional identity checks in section 4."
    )
    doc.h("2. Return window")
    doc.p(
        f"The standard electronics return window is {window} days from delivery. The delivery date is the "
        "date recorded in the ShopSphere delivery system (deliveries.delivery_date); day 0 is the day of "
        f"delivery. A return request raised on or before day {window} is within the window. A request raised "
        f"after day {window} is outside the return window and cannot be approved under this policy; it is "
        "routed to policy exception review, and where the product is still covered by its manufacturer "
        "warranty the customer is offered the warranty route instead."
    )
    doc.table(
        ["Situation", "Window", "Route"],
        [
            ["Change of mind (unused, complete, original packaging)", f"{window} days from delivery", "Standard return"],
            ["Not functioning / defective", f"{window} days from delivery", "Return with inspection; warranty afterwards"],
            ["Damaged on arrival", "Report within 48 hours (see POL-DMG-2024-04)", "Damage claim"],
            ["Wrong product delivered", f"{window} days from delivery", "Manual investigation of SKU/serial"],
            ["Request after the window", "—", "Policy exception review or warranty claim"],
        ],
    )
    doc.h("3. Eligibility")
    doc.bullets(
        [
            "Change of mind: the product must be unused, factory reset, free of personal accounts, and returned with all accessories and original packaging.",
            "Defect or not functioning: the fault must be verified by a warehouse inspection before a refund is approved. An inspection that cannot reproduce the fault is recorded as inconclusive and escalated.",
            "Missing accessories: a return with incomplete accessories is not eligible for a full refund without policy exception review.",
            "Wrong product: the returned item is checked against the order line SKU and, where applicable, the purchased serial number.",
        ]
    )
    doc.h("4. Serial-tracked products")
    doc.p(
        "For serial-tracked products the serial number dispatched is stored on the order line "
        "(order_items.purchased_serial_number). The receiving warehouse records the serial of the unit "
        "actually returned (inspections.returned_serial_number). If the two differ, the return is placed on "
        "hold, an investigation case of type serial_mismatch is opened, and no refund may be requested until "
        "the mismatch is resolved. " + NEUTRAL_LANGUAGE
    )
    doc.h("5. Exceptions and non-returnable items")
    doc.bullets(
        [
            "Software licences or digital codes that have been activated.",
            "Products with a removed, altered or illegible serial label (handled as additional verification required).",
            "Products with liquid exposure indicators triggered, unless the damage is reported as delivery damage under POL-DMG-2024-04.",
            "Policy exceptions outside the window may be approved only by a returns supervisor, with the reason recorded on the investigation case.",
        ]
    )
    doc.h("6. Required documentation")
    doc.bullets(
        [
            "Order ID and return ID.",
            "Purchased serial number (from the invoice or order line) and photograph of the serial label on the returned unit.",
            "Description of the fault and, for defects, the steps to reproduce.",
            "Confirmation that personal data has been erased (laptops and smart devices).",
        ]
    )
    doc.h("7. Refund approval thresholds")
    doc.table(["Refund amount", "Approver", "Notes"], APPROVAL_THRESHOLDS)
    doc.h("8. Refund rules")
    doc.bullets(COMMON_REFUND_RULES)
    doc.h("9. Related documents")
    doc.bullets(
        [
            "POL-DMG-2024-04 Damaged Products and Damaged-in-Transit Policy",
            "WTY-ELEC-2025-01 Electronics Category Warranty Terms",
            "RFB-GEN-2025-01 Returned Goods Recovery and Disposition Framework",
        ]
    )
    return doc, {"policy_version": "3.2", "effective_date": "2025-01-01"}


def fashion() -> tuple[Doc, dict]:
    window = RETURN_WINDOW_DAYS["fashion"]
    doc = Doc(
        title="Fashion and Apparel Return Policy",
        subtitle="ShopSphere Retail — clothing, footwear and textiles (including UrbanWeave)",
        header=_policy_header("POL-FASH-2024-02", "2.4", "2025-01-01", "fashion", str(window), "Returns Policy Office, Mumbai"),
        footer="POL-FASH-2024-02 v2.4 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose and scope")
    doc.p(
        "This policy covers returns and exchanges for products in the fashion category, including shirts, "
        "trousers, dresses, footwear and textile accessories. Fashion products are not serial-tracked; "
        "identity checks rely on the SKU label, brand tags and the order line."
    )
    doc.h("2. Return window")
    doc.p(
        f"Fashion items may be returned within {window} days from delivery (day 0 is the delivery date in the "
        "delivery system). Requests after the window are routed to policy exception review."
    )
    doc.h("3. Eligibility: size and colour")
    doc.bullets(
        [
            "Size or colour exchanges are accepted when the item is unworn, unwashed and has all brand tags attached.",
            "If the size or colour delivered differs from the order line, the return is treated as a fulfilment error and the customer is not charged return shipping.",
            "If the customer ordered the size received, the return is a change-of-mind return and standard conditions apply.",
        ]
    )
    doc.h("4. Hygiene and sealed items")
    doc.p(
        "Innerwear, swimwear, socks and items supplied in a hygiene seal cannot be returned once the seal is "
        "broken, except where the item is defective or a different product was delivered. Inspectors must "
        "record whether the hygiene seal was intact on receipt."
    )
    doc.h("5. Wrong product and record discrepancies")
    doc.p(
        "When the SKU label on the returned item does not match the order line, or the reason on the return "
        "record does not fit the product purchased (for example a size complaint against a non-sized item), "
        "the inspector records the discrepancy verbatim and an investigation case is opened (product_mismatch "
        "or data_correction). " + NEUTRAL_LANGUAGE
    )
    doc.h("6. Required documentation")
    doc.bullets(["Order ID and return ID.", "Photograph of brand tags and SKU label.", "For defects: photograph of the defect (seam failure, dye bleed, misprint)."])
    doc.h("7. Refund approval thresholds")
    doc.table(["Refund amount", "Approver", "Notes"], APPROVAL_THRESHOLDS)
    doc.h("8. Refund rules")
    doc.bullets(COMMON_REFUND_RULES)
    return doc, {"policy_version": "2.4", "effective_date": "2025-01-01"}


def home_appliances() -> tuple[Doc, dict]:
    window = RETURN_WINDOW_DAYS["home_appliances"]
    doc = Doc(
        title="Home Appliances Return Policy",
        subtitle="ShopSphere Retail — air purifiers, kitchen and cleaning appliances (including HomeHive)",
        header=_policy_header("POL-HOME-2024-05", "1.8", "2025-01-01", "home_appliances", f"15 (change of mind) / {window} (defect or damage)", "Returns Policy Office, Mumbai"),
        footer="POL-HOME-2024-05 v1.8 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose and scope")
    doc.p(
        "This policy covers returns of home appliances, including HomeHive air purifiers. Large or installed "
        "appliances require scheduled pickup and, where applicable, de-installation by an authorised partner."
    )
    doc.h("2. Return windows")
    doc.table(
        ["Situation", "Window (days from delivery)", "Conditions"],
        [
            ["Change of mind", "15", "Unused, not installed, original carton and all filters/accessories"],
            ["Defect or not functioning", str(window), "Fault verified by inspection; afterwards the 24-month warranty applies where offered"],
            ["Damaged on arrival", "Report within 48 hours", "See POL-DMG-2024-04"],
            ["Safety concern (overheating, burning smell, sparking)", "Any time", "Customer must stop using the product; pickup is prioritised"],
        ],
    )
    doc.h("3. Installation")
    doc.bullets(
        [
            "Appliances installed by a ShopSphere authorised partner keep their return eligibility; the installation date is recorded on the service ticket.",
            "Damage caused by third-party installation is not covered by this policy.",
            "Air purifiers do not require installation; filters must be returned with the unit.",
        ]
    )
    doc.h("4. Pickup")
    doc.bullets(
        [
            "Pickup is scheduled within 3 business days of an approved return request.",
            "The customer should repack the unit in the original carton where available; the pickup agent records outer packaging condition.",
            "Units reported as unsafe are collected in a fire-safe bag and labelled for quarantine on arrival.",
        ]
    )
    doc.h("5. Safety")
    doc.p(
        "Any appliance that an inspector classifies as unsafe (for example thermal damage, exposed live parts, "
        "insulation failure) must be quarantined and may not be resold, refurbished for resale or returned to "
        "stock. Disposition is limited to recycle or dispose under RFB-SAF-2025-02. An investigation case of "
        "type safety_concern is opened and the supplier is notified."
    )
    doc.h("6. Required documentation")
    doc.bullets(["Order ID and return ID.", "Photographs of the unit and rating label.", "Description of fault; error codes where shown.", "Installation ticket (installed appliances only)."])
    doc.h("7. Refund approval thresholds")
    doc.table(["Refund amount", "Approver", "Notes"], APPROVAL_THRESHOLDS)
    doc.h("8. Refund rules")
    doc.bullets(COMMON_REFUND_RULES)
    return doc, {"policy_version": "1.8", "effective_date": "2025-01-01"}


def accessories() -> tuple[Doc, dict]:
    window = RETURN_WINDOW_DAYS["accessories"]
    doc = Doc(
        title="Accessories Return Policy",
        subtitle="ShopSphere Retail — hubs, cables, cases, bags and small accessories (including FlexFit)",
        header=_policy_header("POL-ACC-2024-01", "2.1", "2025-01-01", "accessories", str(window), "Returns Policy Office, Mumbai"),
        footer="POL-ACC-2024-01 v2.1 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose and scope")
    doc.p("This policy covers accessories such as USB-C hubs, chargers, cables, protective cases and bags, including FlexFit products.")
    doc.h("2. Return window")
    doc.p(f"Accessories may be returned within {window} days from delivery. Requests after day {window} are routed to policy exception review.")
    doc.h("3. Opened package rules")
    doc.table(
        ["Package state", "Eligibility", "Resolution"],
        [
            ["Unopened, seal intact", "Eligible", "Full refund"],
            ["Opened, unused, all contents present", "Eligible", "Full refund; item graded for open-box resale"],
            ["Opened, used, functioning (change of mind)", "Eligible within window", "Full refund after inspection; open-box or refurbish route"],
            ["Opened, contents missing", "Policy exception review", "No full refund until missing items are returned or an exception is approved"],
            ["Defective (verified)", "Eligible", "Refund, or warranty replacement after the window"],
        ],
    )
    doc.h("4. Missing accessories")
    doc.p(
        "Inspectors record accessories_complete for every return. If any packed item listed on the product "
        "page is missing (for example the travel pouch of a USB-C hub), the return is held for policy exception "
        "review. The customer is contacted to send the missing items before a partial or full refund is considered."
    )
    doc.h("5. Required documentation")
    doc.bullets(["Order ID and return ID.", "Photograph of package contents.", "For defects: description of the port or function that fails and the host device used."])
    doc.h("6. Refund approval thresholds")
    doc.table(["Refund amount", "Approver", "Notes"], APPROVAL_THRESHOLDS)
    doc.h("7. Refund rules")
    doc.bullets(COMMON_REFUND_RULES)
    return doc, {"policy_version": "2.1", "effective_date": "2025-01-01"}


def damaged() -> tuple[Doc, dict]:
    doc = Doc(
        title="Damaged Products and Damaged-in-Transit Policy",
        subtitle="ShopSphere Retail — all categories",
        header=_policy_header("POL-DMG-2024-04", "1.5", "2025-02-01", "all (electronics, fashion, home_appliances, accessories)", "Report within 2 days (48 hours) of delivery", "Returns Policy Office with Logistics Claims"),
        footer="POL-DMG-2024-04 v1.5 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose and scope")
    doc.p(
        "This policy covers products that arrive damaged, and products damaged in transit on the return leg. "
        "It applies across all categories and works alongside the category return policies."
    )
    doc.h("2. Reporting window and photographs")
    doc.bullets(
        [
            "Customers should report visible damage within 48 hours of delivery.",
            "Photographs are required of: the outer carton (all sides), the shipping label, the inner packaging, and the damaged product.",
            "Reports received after 48 hours are still reviewed, but the case is routed for manual investigation and the supporting evidence must be stronger.",
        ]
    )
    doc.h("3. Delivery records")
    doc.p(
        "The delivery partner records exceptions on the delivery scan (deliveries.delivery_issue). A recorded "
        "delivery issue such as a crushed carton is strong supporting evidence for a damage claim but does not "
        "replace the warehouse inspection. Investigators must cite both the delivery record and the inspection "
        "findings. A delivery_dispute investigation case is opened where the carrier claim is contested."
    )
    doc.h("4. Responsibility")
    doc.bullets(
        [
            "Customers are not charged for damage caused by the carrier.",
            "ShopSphere files a claim with the logistics partner within 7 days of the inspection confirming transit damage.",
            "If inspection finds no damage consistent with the claim, the outcome is recorded as additional verification required and the customer is contacted for further photographs.",
        ]
    )
    doc.h("5. Return-leg damage")
    doc.p(
        "If a product is damaged during reverse pickup, the pickup agent's condition notes and photographs are "
        "compared with the warehouse inspection. Return-leg damage is never deducted from the customer's refund."
    )
    doc.h("6. Refund approval thresholds")
    doc.table(["Refund amount", "Approver", "Notes"], APPROVAL_THRESHOLDS)
    doc.h("7. Refund rules")
    doc.bullets(COMMON_REFUND_RULES)
    return doc, {"policy_version": "1.5", "effective_date": "2025-02-01"}


POLICIES = (
    (electronics, "return_policy_electronics_pol_elec_2024_03.pdf"),
    (fashion, "return_policy_fashion_pol_fash_2024_02.docx"),
    (home_appliances, "return_policy_home_appliances_pol_home_2024_05.pdf"),
    (accessories, "return_policy_accessories_pol_acc_2024_01.docx"),
    (damaged, "return_policy_damaged_in_transit_pol_dmg_2024_04.pdf"),
)


def build(corpus: Corpus) -> None:
    for factory, filename in POLICIES:
        doc, meta = factory()
        corpus.add_doc(
            doc,
            filename,
            "return_policy",
            effective_date=meta["effective_date"],
            policy_version=meta["policy_version"],
        )
