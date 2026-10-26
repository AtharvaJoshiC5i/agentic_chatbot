"""Batch C (part 2): ten supplier defect reports grounded in SQLite returns."""

from __future__ import annotations

from collections import Counter

from .context import ReturnContext, ShopSphereData, d, yes_no
from .corpus import Corpus
from .render import Doc

FAULT_REASONS = ("defective", "not_functioning", "damaged")


def _evidence_rows(contexts: list[ReturnContext]) -> list[list[str]]:
    rows = []
    for ctx in contexts:
        if ctx.inspections:
            insp = ctx.inspections[-1]
            result = f"{insp['inspection_result']} ({insp['product_condition']})"
            verified = yes_no(insp["defect_verified"])
            if len(ctx.inspections) > 1:
                verified = " / ".join(yes_no(i["defect_verified"]) for i in ctx.inspections) + " (conflicting)"
        else:
            result, verified = "no inspection on record", "—"
        rows.append([ctx.return_id, ctx["order_id"], ctx["return_reason"], d(ctx.requested), result, verified])
    return rows


EVIDENCE_HEADER = ["Return", "Order", "Reason", "Requested", "Inspection", "Defect verified"]


def _report(
    report_id: str,
    report_date: str,
    supplier: dict,
    title: str,
    products: str,
    batches: list[str],
    summary: str,
    evidence: list[ReturnContext],
    analysis: list[str],
    actions: list[str],
    severity: str,
) -> Doc:
    doc = Doc(
        title=f"Supplier Defect Report — {title}",
        subtitle=f"{report_id} · {supplier['supplier_name']} ({supplier['supplier_id']})",
        header=[
            ("Report ID", report_id),
            ("Report date", report_date),
            ("Supplier", f"{supplier['supplier_name']} ({supplier['supplier_id']})"),
            ("Supplier contact", supplier["contact_email"]),
            ("Supplier category", supplier["category"]),
            ("Products", products),
            ("Batch / lot codes", ", ".join(batches)),
            ("Severity", severity),
            ("Prepared by", "Returns Quality Analytics, ShopSphere Retail"),
        ],
        footer=f"{report_id} — Internal use only — ShopSphere Retail. Shared with supplier under NDA.",
    )
    doc.h("1. Summary")
    doc.p(summary)
    doc.h("2. Return evidence (from ShopSphere order and inspection systems)")
    doc.table(EVIDENCE_HEADER, _evidence_rows(evidence))
    doc.h("3. Recurring defect analysis")
    doc.bullets(analysis)
    doc.h("4. Requested supplier actions")
    doc.bullets(actions)
    doc.h("5. Commercial handling")
    doc.p(
        "Units with a verified defect are held for return-to-vendor (supplier_return) against the batch codes above. "
        "Units with conflicting or missing inspection evidence are excluded from any chargeback until the "
        "inspection evidence is complete."
    )
    return doc


def build(corpus: Corpus, data: ShopSphereData) -> None:
    g = data.get
    sup = data.suppliers

    scenario_reports = [
        dict(
            filename="supplier_defect_report_s001_homehive_air_purifier_thermal_inlet.pdf",
            report_id="SDR-2026-031", date="2026-03-16", supplier=sup["S001"],
            title="HomeHive Air Purifier 300: thermal damage at power inlet",
            products="HomeHive Air Purifier 300 (P_R104, P_R110, P_R115)",
            batches=["HH-AP300-B2602", "HH-AP300-B2603"],
            severity="Critical (safety)",
            summary="A returned HomeHive Air Purifier 300 (serial HA9933, return R115) showed scorch marks and melted plastic around the power inlet, and failed the insulation resistance test. The unit is quarantined. Because this is a safety-relevant failure, ShopSphere requests an immediate containment review of the affected lots.",
            evidence=[g("R115")],
            analysis=[
                "Failure location: power inlet housing and adjacent wiring. Thermal discolouration suggests a high-resistance joint at the inlet terminals.",
                "Customer report: burning smell during normal use; customer stopped use immediately.",
                "No other HomeHive units in the current return population show thermal damage, but the severity justifies lot-level containment.",
            ],
            actions=[
                "Provide inlet terminal crimp/solder process records for lots HH-AP300-B2602 and HH-AP300-B2603 within 48 hours.",
                "Submit an 8D report with root cause and containment within 10 business days.",
                "Confirm whether a field safety notice is required.",
                "Do not request the quarantined unit back for refurbishment; it is reserved for recycle/dispose after evidence capture.",
            ],
            meta={"return_id": "R115", "product_id": "P_R115"},
        ),
        dict(
            filename="supplier_defect_report_s001_homehive_e3_shutdown.docx",
            report_id="SDR-2026-032", date="2026-03-17", supplier=sup["S001"],
            title="HomeHive Air Purifier 300: intermittent E3 shutdown and carton strength",
            products="HomeHive Air Purifier 300 (P_R104, P_R110, P_R115)",
            batches=["HH-AP300-B2602"],
            severity="Major",
            summary="One return (R110) reports the unit shutting down with error E3. The two warehouse inspections disagree: the first reproduced the shutdown in 3 of 3 cycles, the second ran 60 minutes without a fault. A separate return (R104) arrived with a crushed carton and a cracked grille. The carrier recorded the crush, but the carton's corner protection is also flagged for review.",
            evidence=[g("R110"), g("R104")],
            analysis=[
                "E3 (sensor/control fault) appears intermittent, which can explain the conflicting inspection outcomes. A thermal or connector-related intermittent fault in the sensor harness is suspected.",
                "Carton: corner crush on R104 led to grille fracture. The grille clips may be too close to the carton wall.",
            ],
            actions=[
                "Share the E3 diagnostic procedure and the expected sensor tolerance.",
                "Review the sensor harness connector retention on lot HH-AP300-B2602.",
                "Propose improved corner protection (EPE corner blocks) for the 300 series carton.",
            ],
            meta={"return_id": "R110", "product_id": "P_R110"},
        ),
        dict(
            filename="supplier_defect_report_s003_flexfit_hub_pd_hdmi.pdf",
            report_id="SDR-2026-027", date="2026-03-18", supplier=sup["S003"],
            title="FlexFit USB-C Hub 7-in-1: power-delivery and port failures",
            products="FlexFit USB-C Hub 7-in-1 (P_R101, P_R105, P_R106, P_R109, P_R113)",
            batches=["FF-HUB7-B2601", "FF-HUB7-B2602"],
            severity="Major",
            summary="Several returns of the FlexFit USB-C Hub 7-in-1 report port or power-delivery failures. Two have inspection-verified defects (R105: PD pass-through does not charge the host and HDMI drops; R106: no HDMI signal). R113 reports dead USB-A ports, but no inspection has been recorded yet, so it is listed for information only and is excluded from defect counts.",
            evidence=[g("R105"), g("R106"), g("R113")],
            analysis=[
                "Verified failures cluster in the PD pass-through and HDMI paths, which share the hub's DisplayPort-alt-mode and PD controller.",
                "Failures appear within 2 weeks of first use, which suggests marginal components rather than wear.",
                "R113 cannot be counted until it has been inspected (evidence gap).",
            ],
            actions=[
                "Provide PD controller firmware version and change history for lots FF-HUB7-B2601/B2602.",
                "Run 72-hour burn-in on 20 retained samples with a 65 W load and share the results.",
                "Accept return-to-vendor of units with verified defects.",
            ],
            meta={"return_id": "R105", "product_id": "P_R105"},
        ),
        dict(
            filename="supplier_defect_report_s005_soundpeak_driver_and_serial_labels.docx",
            report_id="SDR-2026-024", date="2026-03-18", supplier=sup["S005"],
            title="SoundPeak Wireless Headphones Pro: driver dropout reports and serial label control",
            products="SoundPeak Wireless Headphones Pro (P_R102, P_R103, P_R107)",
            batches=["SP-WHP-B2511", "SP-WHP-B2602"],
            severity="Minor (under investigation)",
            summary="Two recent returns of SoundPeak Wireless Headphones Pro involve units whose returned serial differs from the serial recorded at dispatch (R102: purchased HP9081, received HP9012; R107: purchased HP7710, received HP7799). R102 also reports left-driver audio loss. ShopSphere asks the supplier to confirm the serial labelling and box-sticker controls before any defect attribution is made. Neither case is attributed to the supplier at this stage.",
            evidence=[g("R102"), g("R107"), g("R103")],
            analysis=[
                "Serial mismatches can come from labelling errors at the factory (unit label versus box sticker), from mis-scans at dispatch, or from handling after delivery. Additional verification is required in each case; no conclusion has been reached.",
                "Left-driver audio loss (R102) has not been verified against the purchased unit because identity is unconfirmed.",
                "R103 is included as a control: the serial matches (HP3301) and no defect was found.",
            ],
            actions=[
                "Confirm whether HP9012 and HP7799 were produced in the same lots as HP9081 and HP7710.",
                "Share the label-printing reconciliation report for lot SP-WHP-B2602.",
            ],
            meta={"product_id": "P_R102"},
        ),
        dict(
            filename="supplier_defect_report_s005_technova_ultrabook_power_and_keyboard.pdf",
            report_id="SDR-2026-029", date="2026-03-19", supplier=sup["S005"],
            title="TechNova Ultrabook 14: unexpected shutdowns and keyboard spares",
            products="TechNova Ultrabook 14 (P_R108, P_R112)",
            batches=["TN-UB14-B2512", "TN-UB14-B2601"],
            severity="Major",
            summary="Return R112 (serial LT8891) has a verified fault: the laptop shuts down unexpectedly and the power-management log shows power-loss events, which points to a mainboard power-rail fault. Return R108 (serial LT2044) has keyboard damage with cracked keycaps and two keys not registering. The damage is repairable by replacing the keyboard/top-case. ShopSphere requests mainboard failure analysis for R112 and keyboard/top-case spares for the R108 repair.",
            evidence=[g("R112"), g("R108")],
            analysis=[
                "R112: verified mainboard power fault inside the 24-month warranty; treated as a supplier quality issue.",
                "R108: physical keyboard damage; not attributed to a manufacturing defect. Listed here only for the spares request.",
            ],
            actions=[
                "Accept R112 mainboard for failure analysis; provide a replacement board under warranty.",
                "Supply 1 keyboard/top-case assembly (TN-UB14 TC-IN layout) for repair task R108.",
            ],
            meta={"return_id": "R112", "product_id": "P_R112"},
        ),
        dict(
            filename="supplier_defect_report_s002_urbanweave_sku_labelling.docx",
            report_id="SDR-2026-025", date="2026-03-22", supplier=sup["S002"],
            title="UrbanWeave Classic Cotton Shirt: SKU label discrepancies",
            products="UrbanWeave Classic Cotton Shirt (P_R111, P_R114)",
            batches=["UW-CCS-B2602"],
            severity="Minor",
            summary="Return R111 was received with a SKU label that does not match the ordered item. Return R114 has a return record whose reason and system note do not match the order line item. ShopSphere is reviewing its own pick-and-pack and data entry and also asks the supplier to confirm its labelling controls for lot UW-CCS-B2602.",
            evidence=[g("R111"), g("R114")],
            analysis=[
                "Both cases are record or label discrepancies, not fabric or stitching defects.",
                "Root cause may be supplier labelling, ShopSphere warehouse pick, or data entry; additional verification required.",
            ],
            actions=["Confirm SKU label print controls for lot UW-CCS-B2602.", "Provide size/colour label templates for cross-check."],
            meta={"return_id": "R111", "product_id": "P_R111"},
        ),
    ]
    for spec in scenario_reports:
        doc = _report(
            spec["report_id"], spec["date"], spec["supplier"], spec["title"], spec["products"], spec["batches"],
            spec["summary"], spec["evidence"], spec["analysis"], spec["actions"], spec["severity"],
        )
        corpus.add_doc(doc, spec["filename"], "supplier_defect_report", effective_date=spec["date"], **spec["meta"])

    # Bulk suppliers: rank by fault-related returns on their (non-scenario) products.
    scenario_suppliers = {"S001", "S002", "S003", "S005"}
    by_supplier: dict[str, list[ReturnContext]] = {}
    for ctx in data.bulk():
        if ctx["supplier_id"] in scenario_suppliers or ctx["return_reason"] not in FAULT_REASONS:
            continue
        by_supplier.setdefault(ctx["supplier_id"], []).append(ctx)
    ranked = sorted(by_supplier, key=lambda sid: (-len(by_supplier[sid]), sid))

    chosen: list[str] = []
    seen_categories: set[str] = set()
    for sid in ranked:  # prefer one supplier per category, then fill by volume
        if sup[sid]["category"] not in seen_categories:
            chosen.append(sid)
            seen_categories.add(sup[sid]["category"])
    for sid in ranked:
        if len(chosen) >= 4:
            break
        if sid not in chosen:
            chosen.append(sid)
    chosen = chosen[:4]

    defect_text = {
        "electronics": "power and charging faults, and housing cracks at the port openings",
        "home_appliances": "motor start failures and cracked panels at the mounting clips",
        "accessories": "connector and cable-strain failures",
        "fashion": "seam failures and fabric snags",
    }
    for number, sid in enumerate(chosen, start=41):
        supplier = sup[sid]
        returns = sorted(by_supplier[sid], key=lambda c: int(c.return_id[1:]))
        reasons = Counter(c["return_reason"] for c in returns)
        inspected = [c for c in returns if c.inspections]
        verified = [c for c in inspected if any(i["defect_verified"] for i in c.inspections)]
        product_counts = Counter(c["product_id"] for c in returns)
        top_product, top_count = product_counts.most_common(1)[0]
        category = supplier["category"]
        report_id = f"SDR-2026-0{number}"
        batches = [f"{sid}-LOT-25{q}" for q in ("Q3", "Q4")]
        summary = (
            f"Between {d(min(c.requested for c in returns))} and {d(max(c.requested for c in returns))}, "
            f"{len(returns)} returns of products supplied by {supplier['supplier_name']} were raised for fault-related "
            f"reasons ({', '.join(f'{k}: {v}' for k, v in sorted(reasons.items()))}). "
            f"{len(inspected)} have been inspected and {len(verified)} have a verified defect. "
            f"Product {top_product} accounts for {top_count} of these returns. "
            f"The evidence table lists the earliest {min(12, len(returns))}."
        )
        analysis = [
            f"Recurring pattern for this {category} supplier: {defect_text[category]}.",
            f"Verification rate: {len(verified)} of {len(inspected)} inspected returns ({(100 * len(verified) // max(len(inspected), 1))}%).",
            "Returns without an inspection are listed for completeness and are excluded from defect counts.",
        ]
        actions = [
            f"Provide incoming-quality data for lots {', '.join(batches)}.",
            "Submit a corrective action plan for the most frequent failure mode within 15 business days.",
            "Agree return-to-vendor terms for units with verified defects.",
        ]
        doc = _report(
            report_id, "2026-03-20", supplier, f"{category} returns quality review ({sid})",
            f"{len(product_counts)} catalogue products; most affected {top_product}", batches, summary,
            returns[:12], analysis, actions, "Major" if len(verified) >= 5 else "Minor",
        )
        ext = "pdf" if number % 2 else "docx"
        corpus.add_doc(
            doc,
            f"supplier_defect_report_{sid.lower()}_{category}_quality_review.{ext}",
            "supplier_defect_report",
            effective_date="2026-03-20",
            product_id=top_product,
        )
