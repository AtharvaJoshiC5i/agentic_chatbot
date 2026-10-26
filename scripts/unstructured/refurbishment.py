"""Batch D (part 2): five refurbishment / recovery guidelines."""

from __future__ import annotations

from .context import ShopSphereData
from .corpus import Corpus
from .render import Doc

METHODS = [
    ["resell_new", "Unopened or seal intact, passes inspection", "Return to sellable stock at full price"],
    ["open_box_resale", "Opened, complete, no defect, cosmetic grade A/B", "List as open-box at 10–25% discount"],
    ["repair_and_resell", "Single repairable fault, repair cost below 35% of resale value", "Bench repair, burn-in, regrade"],
    ["refurbish_and_resell", "Multiple minor faults or cosmetic wear; full refurbishment needed", "Full refurbishment, new packaging, 6-month ShopSphere warranty"],
    ["supplier_return", "Verified manufacturing defect covered by supplier agreement", "Return-to-vendor against batch code"],
    ["recycle", "Not economically repairable, or unsafe", "Authorised e-waste / textile recycler with certificate"],
    ["dispose", "Unsafe, contaminated, or recycling not possible", "Hazardous-waste disposal with certificate of destruction"],
]


def framework() -> Doc:
    doc = Doc(
        title="Returned Goods Recovery and Disposition Framework",
        subtitle="ShopSphere Retail — all categories",
        header=[("Guideline ID", "RFB-GEN-2025-01"), ("Version", "2.3"), ("Effective date", "2025-04-01"), ("Owner", "Reverse Logistics & Refurbishment"), ("Applies to", "electronics, fashion, home_appliances, accessories")],
        footer="RFB-GEN-2025-01 v2.3 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Purpose")
    doc.p("This framework decides what happens to a returned unit after inspection. It uses the recovery methods recorded in the recovery options and recovery tasks systems.")
    doc.h("2. Recovery methods")
    doc.table(["Method", "Entry criteria", "Action"], METHODS)
    doc.h("3. Decision order")
    doc.bullets(
        [
            "Step 1, safety gate: if the inspection condition is unsafe, the only permitted methods are recycle or dispose. No other method may be selected or approved.",
            "Step 2, identity gate: if the returned serial does not match the purchased serial, or the SKU does not match, the unit stays in hold until the investigation case is resolved.",
            "Step 3, evidence gate: if there is no inspection record, or inspections conflict, no recovery task is created until the evidence is complete.",
            "Step 4, value: choose the method with the highest expected net recovery (expected revenue minus repair, handling and other costs) among feasible methods.",
        ]
    )
    doc.h("4. Expected net recovery")
    doc.p("Expected net recovery = expected revenue − repair cost − handling cost − other cost. Methods whose net recovery is negative are marked not_feasible unless required for safety or compliance.")
    doc.h("5. Approvals")
    doc.bullets(
        [
            "repair_and_resell and refurbish_and_resell for units above INR 50,000 need supervisor approval.",
            "supplier_return needs a supplier defect report reference.",
            "dispose needs warehouse manager sign-off and a certificate of destruction.",
        ]
    )
    return doc


def laptops(data: ShopSphereData) -> Doc:
    r108 = data.get("R108")
    doc = Doc(
        title="Laptop Repair-and-Resell Guideline",
        subtitle="ShopSphere Retail — TechNova Ultrabook 14 and other laptops",
        header=[("Guideline ID", "RFB-LT-2025-01"), ("Version", "1.4"), ("Effective date", "2025-06-01"), ("Category", "electronics (laptops)"), ("Recovery methods", "repair_and_resell, refurbish_and_resell, supplier_return")],
        footer="RFB-LT-2025-01 v1.4 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. When repair-and-resell applies")
    doc.p("A returned laptop qualifies for repair_and_resell when the inspection shows a single repairable fault, all other diagnostics pass, the serial matches the order line, and the repair cost is below 35% of the expected refurbished resale value.")
    doc.h("2. Keyboard damage")
    doc.bullets(
        [
            "Cracked or missing keycaps, broken scissor mechanisms and non-registering keys are repaired by replacing the keyboard/top-case assembly. Individual keycap replacement is not used on TechNova Ultrabook 14 because of clip fragility.",
            "Check for liquid indicators before repair. If any are triggered, route to refurbish_and_resell with a full board inspection.",
            "Typical bench time: 2.5 hours, plus a 4-hour burn-in and a full key-matrix test.",
        ]
    )
    doc.h("3. Worked example")
    doc.p(
        f"Return {r108.return_id} (order {r108['order_id']}, serial {r108['purchased_serial_number']}): inspection IR-2026-00008 recorded keyboard damage (J and K keycaps cracked, right Shift missing, J and right Shift not registering) with all other diagnostics passing and battery health at 94%. "
        "This meets the criteria for repair_and_resell: replace the keyboard/top-case, burn in, regrade, and list as Refurbished Grade A if the cosmetic check passes."
    )
    doc.h("4. Grading after repair")
    doc.table(
        ["Grade", "Cosmetic", "Battery health"],
        [["Refurbished A", "No visible marks at 30 cm", ">= 85%"], ["Refurbished B", "Light marks on lid or base", ">= 75%"], ["Refurbished C", "Visible wear; fully functional", ">= 65%"]],
    )
    doc.h("5. Data security")
    doc.p("All storage is wiped to NIST 800-88 Purge level before any repair-and-resell or refurbishment. The wipe certificate is attached to the recovery task.")
    return doc


def safety(data: ShopSphereData) -> Doc:
    r115 = data.get("R115")
    doc = Doc(
        title="Unsafe Returned Products: Quarantine and No-Resale Guideline",
        subtitle="ShopSphere Retail — electrical and thermal safety",
        header=[("Guideline ID", "RFB-SAF-2025-02"), ("Version", "1.1"), ("Effective date", "2025-05-15"), ("Applies to", "Any unit with inspection condition = unsafe"), ("Permitted recovery methods", "recycle, dispose ONLY")],
        footer="RFB-SAF-2025-02 v1.1 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Rule")
    doc.p("A unit classified as unsafe must never be resold, sold as open-box, repaired for resale, refurbished for resale, or returned to stock. The only permitted recovery methods are recycle and dispose. Any recovery option of another type for an unsafe unit must be marked not_feasible.")
    doc.h("2. What counts as unsafe")
    doc.bullets(
        [
            "Thermal damage: scorch marks, melted plastic, burning odour.",
            "Electrical: failed insulation resistance or earth continuity test, exposed live parts.",
            "Battery: swelling, leakage, or venting.",
            "Mechanical: sharp edges or broken guards around moving parts.",
        ]
    )
    doc.h("3. Quarantine procedure")
    doc.bullets(
        [
            "Stop testing once unsafe is confirmed. Do not power the unit again.",
            "Bag the unit in a fire-safe bag, tag it QUARANTINE — DO NOT RESELL, and move it to the hazardous-goods cage.",
            "Open an investigation case of type safety_concern and notify the Product Safety Lead the same day.",
            "Raise a supplier defect report so the supplier can contain the affected lots.",
        ]
    )
    doc.h("4. Worked example")
    doc.p(
        f"Return {r115.return_id} (HomeHive Air Purifier 300, serial {r115['purchased_serial_number']}, order {r115['order_id']}): inspection IR-2026-00015 found scorch marks and melted plastic at the power inlet, and a failed insulation resistance test. "
        "The unit is unsafe. No resale is permitted. Disposition: recycle through an authorised e-waste recycler, or dispose if the recycler refuses thermally damaged units."
    )
    doc.h("5. Customer resolution")
    doc.p("The customer's refund or replacement is handled separately under the category return policy and its approval thresholds. The safety disposition of the unit does not reduce the customer's entitlement.")
    return doc


def open_box() -> Doc:
    doc = Doc(
        title="Open-Box Grading Guideline: Audio and Accessories",
        subtitle="ShopSphere Retail — SoundPeak headphones, FlexFit hubs and similar items",
        header=[("Guideline ID", "RFB-OB-2025-03"), ("Version", "1.0"), ("Effective date", "2025-07-01"), ("Recovery methods", "open_box_resale, refurbish_and_resell, supplier_return")],
        footer="RFB-OB-2025-03 v1.0 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Eligibility for open-box resale")
    doc.bullets(
        [
            "Inspection condition new, like_new or open_box; defect verified No.",
            "All accessories present. Missing accessories may be replaced from spares stock before listing.",
            "Serial matches the order line (serial-tracked products).",
        ]
    )
    doc.h("2. Grades")
    doc.table(
        ["Grade", "Criteria", "Discount"],
        [["A", "No marks; packaging opened only", "10%"], ["B", "Light handling marks; packaging worn", "18%"], ["C", "Visible marks; functional; replacement packaging", "25% (or refurbish_and_resell)"]],
    )
    doc.h("3. Hygiene for audio products")
    doc.p("Headphone ear cushions and headbands are replaced with new parts and the unit is sanitised with an alcohol-free disinfectant before open-box listing. In-ear products whose seal has been broken cannot be sold as open-box; they go to refurbish_and_resell with new ear tips, or to recycle.")
    doc.h("4. Accessories")
    doc.p("USB-C hubs are tested on all ports, including power-delivery pass-through at 65 W, before open-box listing. Units with a verified port fault go to supplier_return under the relevant supplier defect report.")
    return doc


def textiles() -> Doc:
    doc = Doc(
        title="Fashion and Textile Re-commerce and Recycling Guideline",
        subtitle="ShopSphere Retail — apparel, footwear and textile accessories",
        header=[("Guideline ID", "RFB-TX-2025-01"), ("Version", "1.2"), ("Effective date", "2025-04-15"), ("Category", "fashion"), ("Recovery methods", "resell_new, open_box_resale, refurbish_and_resell, supplier_return, recycle")],
        footer="RFB-TX-2025-01 v1.2 — Internal use only — ShopSphere Retail.",
    )
    doc.h("1. Resell as new")
    doc.p("Unworn, unwashed items with all brand tags attached and the original SKU label are re-tagged where needed, steamed and returned to stock (resell_new).")
    doc.h("2. Items that cannot be resold")
    doc.bullets(
        [
            "Hygiene-sealed items (innerwear, swimwear, socks) with a broken seal go to recycle.",
            "Worn, washed or perfumed items go to textile recycle. Items with stains go to recycle.",
            "Items with a SKU label mismatch are held until the investigation case is resolved, then re-labelled and returned to stock.",
        ]
    )
    doc.h("3. Minor repair")
    doc.p("Loose buttons and short seam openings (under 2 cm) on otherwise new items may be repaired in-house and sold as open-box (open_box_resale).")
    doc.h("4. Recycling partners")
    doc.p("Textile recycling is done through partners certified under the Global Recycled Standard. Each batch is logged with a recycling certificate.")
    return doc


def build(corpus: Corpus, data: ShopSphereData) -> None:
    corpus.add_doc(framework(), "refurbishment_guideline_recovery_disposition_framework.pdf", "refurbishment_guideline", effective_date="2025-04-01", policy_version="2.3")
    corpus.add_doc(laptops(data), "refurbishment_guideline_laptop_repair_and_resell.docx", "refurbishment_guideline", effective_date="2025-06-01", policy_version="1.4", return_id="R108", product_id="P_R108")
    corpus.add_doc(safety(data), "refurbishment_guideline_unsafe_products_no_resale.pdf", "refurbishment_guideline", effective_date="2025-05-15", policy_version="1.1", return_id="R115", product_id="P_R115")
    corpus.add_doc(open_box(), "refurbishment_guideline_open_box_grading_audio_accessories.docx", "refurbishment_guideline", effective_date="2025-07-01", policy_version="1.0")
    corpus.add_doc(textiles(), "refurbishment_guideline_fashion_textile_recommerce.pdf", "refurbishment_guideline", effective_date="2025-04-15", policy_version="1.2")
