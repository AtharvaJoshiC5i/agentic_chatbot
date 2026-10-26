"""Batch B: thirty inspection reports, one per inspections row in SQLite.

Scenario returns R101-R115 get hand-written findings (R113 deliberately has no
report because SQLite has no inspection row). Fifteen non-scenario inspections
are rendered from their structured fields.
"""

from __future__ import annotations

from .context import ReturnContext, ShopSphereData, d, stable_index, yes_no
from .corpus import Corpus
from .render import Doc

RESULT_LEGEND = (
    "Result codes (SOP WH-INS-07): PASS = inspection protocol completed and claim-relevant findings are "
    "conclusive; FAIL = findings do not support the claim as stated; INCONCLUSIVE = findings cannot be "
    "confirmed without further verification. Product condition codes follow the warehouse grading scale "
    "(new, like_new, open_box, damaged, defective, unsafe, for_parts)."
)

ACCESSORIES = {
    "SoundPeak Wireless Headphones Pro": "USB-C charging cable, 3.5 mm audio cable, carry case, quick-start guide",
    "TechNova Ultrabook 14": "65 W USB-C charger, power cord, quick-start guide",
    "HomeHive Air Purifier 300": "HEPA filter cartridge (installed), pre-filter, remote control, user manual",
    "FlexFit USB-C Hub 7-in-1": "travel pouch, user guide",
    "UrbanWeave Classic Cotton Shirt": "brand tags, spare button, garment bag",
}
GENERIC_ACCESSORIES = {
    "electronics": "charging cable, user manual, warranty card",
    "home_appliances": "power cord, user manual, warranty card",
    "accessories": "packaging insert, user guide",
    "fashion": "brand tags, garment bag",
}

# Scenario findings keyed by inspections.inspection_id (R110 has two rows).
SCENARIO_FINDINGS: dict[int, dict] = {
    1: {
        "slug": "valid_return",
        "findings": [
            "The hub was received in its original retail box with the inner tray intact. The outer sleeve had been opened along the tab; no tape or cutting damage was observed. The housing is clean with no scratches, dents or marks on the connectors.",
            "Functional test on the standard test host (USB-C laptop, 65 W charger): HDMI output at 4K/30 Hz, both USB-A ports, USB-C data, SD and microSD readers and power-delivery pass-through all operated correctly. Ethernet negotiated at 1 Gbps.",
            "The customer's stated reason is change of mind and no defect was claimed, so there was no defect to verify. The result code is recorded as INCONCLUSIVE only because the defect-verification step is not applicable; no exceptions were found.",
        ],
        "next": "No inconsistencies found. The request was raised 5 days after delivery, inside the 30-day accessories window (POL-ACC-2024-01). Eligible for standard resolution; refund requires analyst approval. Grade for open-box resale (grade A).",
    },
    2: {
        "slug": "serial_mismatch",
        "findings": [
            "Serial mismatch: the order line for O102 records purchased serial HP9081. The unit received at the warehouse carries serial HP9012 on its internal label and on the outer box sticker. The two serial numbers do not match.",
            "The serial label on the unit is intact, legible and shows no sign of removal or reprinting. The headphones are the same model as the order line (SoundPeak Wireless Headphones Pro) and all accessories are present.",
            "On power-up the unit pairs over Bluetooth, but the left driver produces no audio at any volume (condition: defective). Because the identity of the returned unit could not be matched to the purchase record, the defect was not verified against the purchased item (defect verified: No).",
            "Photographs of the serial label (front and rear), the box sticker and the accessory tray are attached to the inspection record.",
        ],
        "next": "Additional verification required. Hold the return; do not request or execute a refund while the serial mismatch is unresolved. Investigation case 1 (serial_mismatch, high priority) is assigned to analyst_02. Suggested checks: dispatch scan for O102, the customer's invoice or box photograph showing the serial, and whether HP9012 appears on any other order line.",
    },
    3: {
        "slug": "outside_return_window",
        "findings": [
            "The unit was received in its retail box with the seal opened. Serial HP3301 on the unit matches the purchased serial on order line O103.",
            "Cosmetic condition is good; light handling marks on the headband only. Both drivers, Bluetooth pairing, active noise cancellation and charging were tested and work correctly. No defect was claimed (reason: changed_mind) and none was found.",
            "Timeline check: delivered 2025-11-27, return requested 2026-01-21, which is 55 days after delivery.",
        ],
        "next": "The request is outside the electronics 30-day return window (POL-ELEC-2024-03, section 2). Route for policy exception review; the request cannot be approved as a standard return. If approved as an exception, the unit is suitable for open-box resale.",
    },
    4: {
        "slug": "delivery_damage",
        "findings": [
            "The air purifier arrived in the original carton, which shows crush marks on two corners and a split along the top flap. The delivery record for O104 contains the carrier note: “Carton crushed; visible impact damage on delivery scan.”",
            "Product: the front grille is cracked across the lower third and the left side panel has an impact dent about 4 cm wide. The damage pattern matches the crushed carton corners, which points to an impact in transit and not to use.",
            "On power-up the fan runs but rattles at speeds 2 and 3 because the grille rubs the impeller. Filters and the remote control are present. Damage verified (defect verified: Yes).",
        ],
        "next": "Damage confirmed and consistent with the recorded delivery issue. Investigation case 2 (delivery_dispute) remains open for the logistics claim under POL-DMG-2024-04. Refund value INR 12,999.00 is above INR 10,000 and requires returns supervisor approval. Recovery: supplier return or parts harvest; not resaleable as new.",
    },
    5: {
        "slug": "verified_defect",
        "findings": [
            "Serial EL5520 on the hub matches the order line for O105. The hub is clean, with no physical damage, bent connectors or cable strain.",
            "Defect reproduced: with a 65 W charger connected to the USB-C PD input, the host laptop did not charge in 3 of 3 attempts, and the HDMI output dropped every few minutes during a 20-minute test. All other ports worked.",
            "The fault is consistent with a manufacturing defect in the power-delivery circuit (defect verified: Yes).",
        ],
        "next": "Defect verified. Within the 30-day accessories window (requested 12 days after delivery). Refer for warranty review and supplier return to the accessories supplier (see supplier defect report for the FlexFit USB-C hub PD fault). A refund requires analyst approval.",
    },
    6: {
        "slug": "verified_defect_hdmi",
        "findings": [
            "The hub was received in its retail box with all packed items. No serial is recorded for this order line, so identity was confirmed by model and packaging.",
            "Defect reproduced: no HDMI signal on two different monitors and two cables. USB-A and USB-C data ports work. Power-delivery pass-through works.",
            "Condition: defective; accessories complete; defect verified: Yes.",
        ],
        "next": "Defect verified and inside the return window (7 days after delivery). Before any refund action, the refunds ledger must be checked for an existing completed refund on R106, because only one completed refund is allowed per return.",
    },
    7: {
        "slug": "multiple_record_inconsistencies",
        "findings": [
            "Several records for this return do not agree. The order line for O107 records purchased serial HP7710; the unit received carries serial HP7799. The return reason recorded is wrong_product, but the item received is the same model as the order line (SoundPeak Wireless Headphones Pro).",
            "Accessories are incomplete: the carry case and the 3.5 mm audio cable are missing. The unit has a cracked right ear-cup hinge and scuffing on the headband (condition: damaged).",
            "No functional defect could be confirmed (defect verified: No). {history}",
        ],
        "next": "Additional verification required: serial mismatch, missing accessories and a reason code that does not fit the item received. Investigation case 3 (general) is assigned to analyst_02 for manual review. No refund decision should be made until the case is resolved.",
    },
    8: {
        "slug": "keyboard_damage_repairable",
        "findings": [
            "Serial LT2044 on the base label matches the order line for O108. Charger and power cord are present.",
            "Keyboard damage: the keycaps for J and K are cracked, the right Shift keycap is missing, and the scissor mechanism under it is broken. In the key-matrix test, J and right Shift do not register. There is slight flex in the keyboard deck around the damaged keys. No liquid indicators are triggered.",
            "All other diagnostics pass: display (no dead pixels), battery health 94% of design capacity, SSD SMART status OK, both USB-C ports, Wi-Fi and webcam.",
            "Assessment: the damage is limited to the keyboard and top-case assembly. It is repairable by replacing the keyboard/top-case assembly (estimated 2.5 hours of bench labour). Condition: damaged; defect verified: Yes.",
        ],
        "next": "Repair-and-resell is feasible: create a repair task for keyboard/top-case replacement under RFB-LT-2025-01, then regrade as refurbished. The request was 9 days after delivery, inside the 30-day electronics window. Refund value INR 68,999.00 is above INR 50,000 and needs returns supervisor and finance controller approval.",
    },
    9: {
        "slug": "missing_accessories",
        "findings": [
            "Serial EL8812 matches the order line for O109. The retail box was opened; the hub itself is in good condition.",
            "Accessories incomplete: the travel pouch and the printed user guide listed on the product page are missing from the box.",
            "Functional test: all seven ports work on the standard test host. No defect found (defect verified: No).",
        ],
        "next": "Missing accessories: hold for policy exception review (POL-ACC-2024-01, section 4). Contact the customer about the missing travel pouch and user guide. Once complete, the unit is suitable for open-box resale.",
    },
    10: {
        "slug": "a_initial_defect_verified",
        "findings": [
            "First inspection of the HomeHive Air Purifier 300 returned under R110 (reason: not_functioning). No serial is recorded on the order line; identity was confirmed by model, rating label and packaging.",
            "The motor assembly is functional: the fan starts and holds all three speeds. The fault reported by the customer was reproduced in the control and sensor circuit. The unit shut down after 6–8 minutes of operation with error code E3 on the display, in 3 of 3 test cycles.",
            "Conclusion of this inspection: defect verified (Yes). Result PASS. Probable cause is the air-quality sensor or the control board.",
        ],
        "next": "Defect verified by this inspection. Recommend warranty review and supplier return for sensor/control-board analysis. Refund value INR 12,999.00 is above INR 10,000 and requires supervisor approval.",
    },
    11: {
        "slug": "b_second_defect_disputed",
        "findings": [
            "Second inspection of the same unit for R110, done the same day by a different technician.",
            "The unit ran continuously for 60 minutes, cycling through all three fan speeds and auto mode. It did not shut down and no E3 or other error code appeared. Air-quality sensor readings tracked the reference meter within tolerance. Motor current draw was normal.",
            "Conclusion of this inspection: defect not verified (No). Result FAIL: the findings do not support the not_functioning claim.",
            "This conclusion conflicts with the earlier inspection report IR-2026-00010 for the same return, which recorded an E3 shutdown in 3 of 3 cycles and a verified defect.",
        ],
        "next": "Conflicting inspection findings. The two reports for R110 disagree on whether the defect is verified. Investigation case 4 (conflicting_evidence) is open. A supervisor should arrange an independent tie-break test (for example an extended run of 4 hours or more at mains voltage) before any refund or recovery decision.",
    },
    12: {
        "slug": "wrong_product_sku_label",
        "findings": [
            "The garment received is new, unworn and unwashed, with brand tags attached. The garment bag is present.",
            "The SKU label on the returned garment does not match the SKU of the ordered item (product P_R111, UrbanWeave Classic Cotton Shirt) on order O111. The customer's return reason is wrong_product.",
            "No defect was assessed (defect verified: No). The result is INCONCLUSIVE until the SKU discrepancy is resolved.",
        ],
        "next": "Product mismatch: investigation case 5 (product_mismatch) is open. Check the pick-and-pack record for O111 to establish which SKU was dispatched. Inside the 15-day fashion window (4 days after delivery).",
    },
    13: {
        "slug": "warranty_failure",
        "findings": [
            "Serial LT8891 matches the order line for O112. No physical damage; the chassis and display are intact; charger present.",
            "Fault reproduced: the laptop powers on, then shuts down without warning within 2–10 minutes under light load. Memory test passes. Thermal readings are normal. The mainboard power-management log shows repeated unexpected power-loss events, which suggests a mainboard power-rail fault.",
            "Condition: defective; defect verified: Yes.",
        ],
        "next": "Verified failure within the 24-month warranty period. Open a warranty_review and route to TechNova authorised service for mainboard replacement, or refund with the approvals required for INR 68,999.00 (supervisor and finance controller).",
    },
    14: {
        "slug": "incorrect_return_record",
        "findings": [
            "The item received is a new, unworn shirt with tags attached, which matches the catalogue line item for O114: UrbanWeave Classic Cotton Shirt (product P_R114, category fashion).",
            "The return record gives the reason size_color_incorrect. The inspector's system note reads verbatim: “Return reason references size mismatch but line item is accessory SKU.” The catalogue shows the line item as a fashion SKU, not an accessory, so the return record, the system note and the order line do not agree.",
            "Size and colour on the garment were recorded from its labels for the analyst. No defect was assessed (defect verified: No).",
        ],
        "next": "Data correction needed: investigation case 6 (data_correction) is open. The analyst should reconcile the return reason, the line item and the system note before deciding the return. Additional verification required.",
    },
    15: {
        "slug": "unsafe_product",
        "findings": [
            "Serial HA9933 on the rating label matches the order line for O115.",
            "Unsafe condition: there are scorch marks around the power inlet, and the plastic of the inlet housing has melted and deformed. A strong burning odour was present when the carton was opened. The power cord insulation is discoloured near the plug.",
            "Electrical safety test: the insulation resistance test failed (below the 2 megohm acceptance limit). The unit was not powered further. Condition: unsafe; defect verified: Yes.",
            "The unit was bagged in a fire-safe quarantine bag and moved to the hazardous-goods cage, tagged QUARANTINE — DO NOT RESELL.",
        ],
        "next": "UNSAFE — NO RESALE. The unit must not be resold, refurbished for resale or returned to stock. Disposition is limited to recycle or dispose (RFB-SAF-2025-02) through an authorised e-waste recycler. Investigation case 7 (safety_concern, high priority) is open. Notify the supplier and the product safety lead the same day.",
    },
}

def _header(ctx: ReturnContext, insp: dict, report_id: str) -> list[tuple[str, str]]:
    inspector_id, inspector_name = ctx.inspector_for(insp)
    return [
        ("Report ID", report_id),
        ("Inspection record ID", str(insp["inspection_id"])),
        ("Return ID", ctx.return_id),
        ("Order ID", ctx["order_id"]),
        ("Customer ID", ctx["customer_id"]),
        ("Product", ctx.product_label),
        ("Category", ctx.category),
        ("Inspection date", insp["inspection_date"][:16]),
        ("Inspector", f"{inspector_name} ({inspector_id})"),
        ("Site", ctx.site),
    ]


def _serial_rows(ctx: ReturnContext, insp: dict) -> list[tuple[str, str]]:
    purchased = ctx["purchased_serial_number"]
    returned = insp["returned_serial_number"]
    if purchased is None and returned is None:
        match = "Not applicable (no serial recorded for this order line)"
    elif purchased == returned:
        match = "Yes"
    else:
        match = "No — MISMATCH"
    return [
        ("Purchased serial (order line)", purchased or "Not recorded"),
        ("Returned serial (unit received)", returned or "Not recorded"),
        ("Serial match", match),
    ]


def _timeline(ctx: ReturnContext) -> list[tuple[str, str]]:
    days = ctx.days_after_delivery
    window = ctx.window_days
    status = "within" if ctx.within_window else "outside"
    return [
        ("Order date", d(ctx.ordered)),
        ("Delivered", d(ctx.delivery)),
        ("Return requested", f"{d(ctx.requested)} ({days} days after delivery; {status} the {window}-day {ctx.category} window)"),
        ("Received at warehouse", d(ctx.received)),
        ("Return reason (recorded)", ctx["return_reason"]),
        ("Price paid", ctx.price),
    ]


def _report(ctx: ReturnContext, insp: dict, findings: list[str], next_step: str, system_note: str | None) -> Doc:
    report_id = f"IR-2026-{insp['inspection_id']:05d}"
    doc = Doc(
        title="Returns Inspection Report",
        subtitle=f"{report_id} · Return {ctx.return_id} · {ctx['product_name']}",
        header=_header(ctx, insp, report_id),
    )
    doc.h("1. Identification")
    doc.kv(_serial_rows(ctx, insp))
    doc.h("2. Timeline")
    doc.kv(_timeline(ctx))
    doc.h("3. Condition summary")
    packed = ACCESSORIES.get(ctx["product_name"], GENERIC_ACCESSORIES[ctx.category])
    doc.kv(
        [
            ("Product condition", insp["product_condition"]),
            ("Accessories expected", packed),
            ("Accessories complete", yes_no(insp["accessories_complete"])),
            ("Defect verified", yes_no(insp["defect_verified"])),
            ("Inspection result", insp["inspection_result"].upper()),
        ]
    )
    doc.h("4. Findings")
    for paragraph in findings:
        doc.p(paragraph)
    if system_note:
        doc.h("5. Inspector system note (verbatim from inspection record)")
        doc.p(f"“{system_note}”")
    doc.h("6. Recommended next step" if system_note else "5. Recommended next step")
    doc.p(next_step)
    doc.p(RESULT_LEGEND)
    doc.p(f"Signed: {ctx.inspector_for(insp)[1]}, {ctx.site.split(',')[0]}. This report records physical findings only; refund and recovery decisions are made by returns analysts under the applicable policy.")
    return doc


def _history_sentence(data: ShopSphereData, ctx: ReturnContext) -> str:
    """Describe the customer's other returns from SQLite (used in the R107 report)."""
    others = [c for c in data.returns.values() if c["customer_id"] == ctx["customer_id"] and c.return_id != ctx.return_id]
    if not others:
        return "The account has no other returns on record in the order system."
    parts = []
    for other in sorted(others, key=lambda c: int(c.return_id[1:])):
        mismatch = any(
            other["purchased_serial_number"] and i["returned_serial_number"] and i["returned_serial_number"] != other["purchased_serial_number"]
            for i in other.inspections
        )
        flag = ", with a serial mismatch on inspection" if mismatch else ""
        parts.append(f"{other.return_id} (reason: {other['return_reason']}, status: {other['return_status']}{flag})")
    return f"The account also has {len(others)} earlier return(s) on record: " + "; ".join(parts) + ". This is context for the analyst only; each return is assessed on its own evidence."


def _bulk_findings(ctx: ReturnContext, insp: dict) -> tuple[list[str], str]:
    """Build findings from the structured inspection fields (SQLite is the source of truth)."""
    cat = ctx.category
    condition = insp["product_condition"]
    verified = bool(insp["defect_verified"])
    result = insp["inspection_result"]
    reason = ctx["return_reason"]
    purchased, returned = ctx["purchased_serial_number"], insp["returned_serial_number"]
    mismatch = bool(purchased and returned and purchased != returned)

    findings = []
    if condition == "damaged":
        findings.append("The item was received in its outer shipping carton. On unpacking, the inspector recorded physical damage. Photographs of the damaged areas and the packaging are attached to the inspection record.")
    elif condition == "unsafe":
        findings.append("The unit was handled with extra care on receipt and isolated from other stock as soon as the condition was identified. Photographs of the affected areas are attached to the inspection record.")
    else:
        findings.append("The item was received in its retail packaging. The packaging had been opened and the contents show only light handling. Photographs of the item and packaging are attached to the inspection record.")

    if mismatch:
        findings.append(f"Serial mismatch: the order line records purchased serial {purchased}, but the unit received carries serial {returned}. The two serial numbers do not match, so additional verification is required before the identity of the returned unit can be confirmed.")
    elif purchased:
        findings.append(f"The serial number on the unit ({returned}) matches the purchased serial on the order line ({purchased}).")
    else:
        findings.append("No serial number is recorded for this order line; identity was confirmed from the product label, SKU and packaging.")
    findings.append("All accessories listed for the product were present." if insp["accessories_complete"] else "The accessories were incomplete: items listed for the product were missing from the box.")

    if verified:
        findings.append(f"Assessment: the reported problem was verified on the bench (defect verified: Yes). The findings support the reason recorded on the return ({reason}).")
    elif result == "fail":
        findings.append(f"Assessment: the findings do not support the reason recorded on the return ({reason}); the reported fault could not be reproduced (defect verified: No).")
    else:
        findings.append(f"Assessment: no defect was verified (defect verified: No). The findings neither confirm nor contradict the reason recorded on the return ({reason}).")

    window_text = (
        f"The request was raised {ctx.days_after_delivery} days after delivery, "
        f"{'within' if ctx.within_window else 'outside'} the {ctx.window_days}-day return window for {cat}."
    )
    if condition == "unsafe":
        next_step = "UNSAFE - NO RESALE. The unit must be quarantined and must not be resold, refurbished for resale or returned to stock. Disposition is limited to recycle or dispose (RFB-SAF-2025-02). Notify the Product Safety Lead and the supplier the same day. " + window_text
    elif mismatch:
        next_step = f"Additional verification required. Hold the return and do not request a refund while the serial mismatch is unresolved. Check the dispatch scan for order {ctx['order_id']} and whether serial {returned} appears on another order line. {window_text}"
    elif condition == "for_parts":
        next_step = f"Findings are conclusive and support the claim. The unit is not economically repairable and is graded for parts; recycle or supplier return are the feasible recovery routes. {window_text}"
    elif result == "fail":
        next_step = f"The findings do not support the claim as stated. A returns analyst should review the customer's description and consider a second inspection before deciding under the {cat} return policy. {window_text}"
    elif verified:
        next_step = f"Findings are conclusive and support the claim. Any refund is subject to the approval thresholds in the {cat} return policy. {window_text}"
    else:
        grade = "resale as new or open-box" if condition in ("new", "like_new") else "open-box resale"
        if reason == "changed_mind":
            basis = f"No defect was claimed or found; eligibility is assessed under the change-of-mind conditions of the {cat} return policy."
        elif reason == "missing_accessories":
            basis = f"The return is incomplete; hold it for policy exception review under the {cat} return policy until the missing items are returned or an exception is approved."
        else:
            basis = f"No defect was verified. The stated reason ({reason}) should be checked by a returns analyst against the order line under the {cat} return policy."
        next_step = f"{basis} {window_text} Once cleared, the item is suitable for {grade}."
    return findings, next_step


def _select_bulk(data: ShopSphereData) -> list[tuple[ReturnContext, dict]]:
    """Pick 15 non-scenario inspections spread over categories and condition codes.

    Unsafe and serial-mismatch inspections are preferred so those evidence types
    are represented; pending inspections are skipped (nothing to report yet).
    """
    quota = {"electronics": 4, "home_appliances": 4, "accessories": 4, "fashion": 3}
    chosen: list[tuple[ReturnContext, dict]] = []

    def priority(ctx: ReturnContext) -> int:
        insp = ctx.inspections[0]
        if insp["product_condition"] == "unsafe":
            return 0
        purchased = ctx["purchased_serial_number"]
        if purchased and insp["returned_serial_number"] and purchased != insp["returned_serial_number"]:
            return 1
        return 2

    for category, count in quota.items():
        pool = [
            ctx for ctx in data.bulk()
            if ctx.category == category and len(ctx.inspections) == 1 and ctx.inspections[0]["inspection_result"] != "pending"
        ]
        pool.sort(key=priority)  # stable: keeps return order within a priority
        seen_combos: set[tuple] = set()
        picked: list[tuple[ReturnContext, dict]] = []
        for ctx in pool:  # first pass: distinct (condition, verified, result) combinations
            insp = ctx.inspections[0]
            combo = (insp["product_condition"], insp["defect_verified"], insp["inspection_result"])
            if combo not in seen_combos:
                seen_combos.add(combo)
                picked.append((ctx, insp))
            if len(picked) == count:
                break
        for ctx in pool:  # top up if a category has fewer distinct combinations
            if len(picked) == count:
                break
            if all(ctx is not existing for existing, _ in picked):
                picked.append((ctx, ctx.inspections[0]))
        chosen += picked
    return chosen


def bulk_selection(data: ShopSphereData) -> list[str]:
    return [ctx.return_id for ctx, _ in _select_bulk(data)]


def build(corpus: Corpus, data: ShopSphereData) -> None:
    for return_id in [f"R{i}" for i in range(101, 116)]:
        ctx = data.get(return_id)
        if not ctx.inspections:
            # R113: SQLite has no inspection row; the evidence gap is intentional.
            continue
        for insp in ctx.inspections:
            spec = SCENARIO_FINDINGS[insp["inspection_id"]]
            history = _history_sentence(data, ctx)
            note = insp["inspector_notes"]
            note = None if note == "Scenario inspection record." else note
            findings = [text.replace("{history}", history) for text in spec["findings"]]
            doc = _report(ctx, insp, findings, spec["next"], note)
            corpus.add_doc(
                doc,
                f"inspection_{return_id}_{spec['slug']}.pdf",
                "inspection_report",
                effective_date=insp["inspection_date"][:10],
                return_id=return_id,
                product_id=ctx["product_id"],
            )

    for ctx, insp in _select_bulk(data):
        findings, next_step = _bulk_findings(ctx, insp)
        doc = _report(ctx, insp, findings, next_step, insp["inspector_notes"])
        corpus.add_doc(
            doc,
            f"inspection_{ctx.return_id}_{insp['product_condition']}_{ctx.category}.pdf",
            "inspection_report",
            effective_date=insp["inspection_date"][:10],
            return_id=ctx.return_id,
            product_id=ctx["product_id"],
        )
