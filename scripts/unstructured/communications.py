"""Batch D (part 1): thirty support communications (EML threads)."""

from __future__ import annotations

from datetime import datetime, timedelta

from .context import ReturnContext, ShopSphereData, d, inr
from .corpus import Corpus
from .render import Email

SUPPORT = "ShopSphere Customer Care <support@shopsphere.invalid>"
ANALYST = "Returns Analyst analyst_02 <analyst02@shopsphere.invalid>"
WAREHOUSE = "Warehouse Operations <wh-ops@shopsphere.invalid>"
REFURB = "Refurbishment Centre Bhiwandi <refurb-centre@shopsphere.invalid>"
SUPERVISOR = "Returns Supervisor <returns-supervisor@shopsphere.invalid>"
FINANCE = "Finance Refunds Desk <refunds-finance@shopsphere.invalid>"
SAFETY = "Product Safety Lead <product-safety@shopsphere.invalid>"
CARRIER = "SwiftKart Logistics Claims <claims@swiftkart-logistics.invalid>"

CUSTOMER_SIGN = "Warm regards,\nAnanya\nShopSphere Customer Care"
INTERNAL_SIGN = "analyst_02\nReturns Investigations, ShopSphere Retail"


def _cust(ctx: ReturnContext) -> str:
    return f"{ctx['customer_name']} <{ctx['customer_email']}>"


def _mid(key: str) -> str:
    return f"<{key}@support.shopsphere.invalid>"


def _headers(ctx: ReturnContext, internal: bool = False) -> dict[str, str]:
    headers = {"X-ShopSphere-Return-ID": ctx.return_id, "X-ShopSphere-Order-ID": ctx["order_id"]}
    if internal:
        headers["X-ShopSphere-Classification"] = "Internal"
    return headers


def _scenario_messages(data: ShopSphereData) -> list[tuple[str, ReturnContext, Email]]:
    g = data.get
    r102, r106, r108 = g("R102"), g("R106"), g("R108")
    r104, r110, r113, r115 = g("R104"), g("R110"), g("R113"), g("R115")
    r101, r103, r105, r107, r109, r111, r112, r114 = (g(x) for x in ("R101", "R103", "R105", "R107", "R109", "R111", "R112", "R114"))
    refund106 = r106.completed_refund
    assert refund106 is not None, "R106 must have a completed refund in SQLite"
    refund106_date = d(datetime.fromisoformat(refund106["processed_date"]))
    case = {ctx.return_id: ctx.cases[0] for ctx in (r102, r104, r107, r110, r111, r114, r115)}

    msgs: list[tuple[str, ReturnContext, Email]] = []

    # ---- R102: serial mismatch thread
    msgs.append(("support_R102_additional_verification_required.eml", r102, Email(
        sender=SUPPORT, to=_cust(r102),
        subject=f"Your return {r102.return_id} needs additional verification",
        sent_at=datetime(2026, 3, 14, 10, 30), message_id=_mid("r102-1"),
        in_reply_to="<cmp-2026-0102@customers.shopsphere.invalid>",
        references=["<cmp-2026-0102@customers.shopsphere.invalid>"],
        body=f"""Dear {r102['customer_name']},

Thank you for returning the SoundPeak Wireless Headphones Pro from order {r102['order_id']}. Our warehouse received the item on {d(r102.received)} and inspected it on 2026-03-13.

The serial number on the unit we received (HP9012) is different from the serial number recorded when your order was dispatched (HP9081). This can happen for several reasons, including labelling or scanning errors, so we need to complete some additional verification before we can process your return. Your return is on hold until then.

To help us, please reply with:
- a photo of the barcode sticker on the outer box you received, and
- your invoice, if you have it to hand.

We will update you as soon as the review is complete.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r102))))
    msgs.append(("support_R102_internal_serial_check_request.eml", r102, Email(
        sender=ANALYST, to=WAREHOUSE, cc=SUPERVISOR,
        subject=f"[Case {case['R102']['case_id']}] R102 serial mismatch HP9081 vs HP9012 - dispatch check",
        sent_at=datetime(2026, 3, 14, 15, 10), message_id=_mid("r102-2"),
        body=f"""Hi team,

Investigation case {case['R102']['case_id']} (serial_mismatch, priority {case['R102']['priority']}, due {case['R102']['due_date'][:10]}) is open for return R102 / order O102.

- Purchased serial (order line): HP9081
- Returned serial (inspection IR-2026-00002): HP9012
- Inspection result: inconclusive; defect verified: No (identity not confirmed)

Please check:
1. The dispatch scan log for O102: which serial was scanned at pack-out?
2. Whether HP9012 appears on any other order line or in stock.
3. CCTV at the pack station for the dispatch date (2026-02-24), if it is still retained.

Please do not request a refund on R102 until the case is resolved. The outcome remains "additional verification required" until we have the dispatch evidence.

Thanks,
{INTERNAL_SIGN}""",
        extra_headers=_headers(r102, internal=True))))
    msgs.append(("support_R102_reply_to_customer_follow_up.eml", r102, Email(
        sender=SUPPORT, to=_cust(r102),
        subject=f"Re: Return {r102.return_id} on hold - why?",
        sent_at=datetime(2026, 3, 17, 11, 0), message_id=_mid("r102-3"),
        in_reply_to="<cmp-2026-0102-f@customers.shopsphere.invalid>",
        references=[_mid("r102-1"), "<cmp-2026-0102-f@customers.shopsphere.invalid>"],
        body=f"""Dear {r102['customer_name']},

Thank you for your reply, and we're sorry for the wait. We are not suggesting you did anything wrong. A mismatch like this is often caused by a label or scanning error on our side or the manufacturer's, and we have asked our warehouse to check the dispatch records for your order.

A photo of the barcode sticker on the outer box would be very helpful. Please reply to this email with it attached. We aim to complete the review by {case['R102']['due_date'][:10]}.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r102))))

    # ---- R106: refund already completed thread
    msgs.append(("support_R106_refund_confirmation.eml", r106, Email(
        sender=SUPPORT, to=_cust(r106),
        subject=f"Refund processed for return {r106.return_id}",
        sent_at=datetime.fromisoformat(refund106["processed_date"]).replace(hour=14), message_id=_mid("r106-1"),
        body=f"""Dear {r106['customer_name']},

Your return {r106.return_id} for the FlexFit USB-C Hub 7-in-1 (order {r106['order_id']}) has been approved. A refund of {inr(refund106['refund_amount'])} was processed on {refund106_date} to your original payment method.

Depending on your bank, it can take 5–7 business days for the amount to show in your account.

{CUSTOMER_SIGN}""",
        extra_headers={**_headers(r106), "X-ShopSphere-Refund-ID": str(refund106["refund_id"])})))
    msgs.append(("support_R106_customer_requests_refund_again.eml", r106, Email(
        sender=_cust(r106), to=SUPPORT,
        subject=f"Refund not received for return {r106.return_id} - please process",
        sent_at=datetime(2026, 3, 12, 9, 20), message_id="<r106-cust-2@customers.shopsphere.invalid>",
        body=f"""Hi,

I returned the USB-C hub (order {r106['order_id']}, return {r106.return_id}) but I can't see the refund in my account yet. Please process the refund.

{r106['customer_name']}""",
        extra_headers=_headers(r106))))
    msgs.append(("support_R106_refund_already_processed.eml", r106, Email(
        sender=SUPPORT, to=_cust(r106),
        subject=f"Re: Refund not received for return {r106.return_id} - please process",
        sent_at=datetime(2026, 3, 12, 12, 45), message_id=_mid("r106-3"),
        in_reply_to="<r106-cust-2@customers.shopsphere.invalid>",
        references=[_mid("r106-1"), "<r106-cust-2@customers.shopsphere.invalid>"],
        body=f"""Dear {r106['customer_name']},

Thank you for checking with us. The refund for return {r106.return_id} has already been completed. {inr(refund106['refund_amount'])} was processed on {refund106_date} to your original payment method (refund ID {refund106['refund_id']}, status: completed). Because the refund is complete, a second refund will not be issued for this return.

Banks can take up to 5–7 business days to post a credit. If you still cannot see it after {d(datetime.fromisoformat(refund106['processed_date']) + timedelta(days=10))}, please share a bank statement for the period and we will raise a trace with our payments team.

{CUSTOMER_SIGN}""",
        extra_headers={**_headers(r106), "X-ShopSphere-Refund-ID": str(refund106["refund_id"])})))
    msgs.append(("support_R106_internal_duplicate_refund_blocked.eml", r106, Email(
        sender=ANALYST, to=FINANCE,
        subject="R106 - repeat refund request; existing completed refund confirmed",
        sent_at=datetime(2026, 3, 12, 13, 5), message_id=_mid("r106-4"),
        body=f"""Hi Finance,

For your records: the customer for return R106 asked for a refund today. The ledger shows refund ID {refund106['refund_id']} for {inr(refund106['refund_amount'])}, status completed, approval {refund106['approval_status']}, processed {refund106_date} (idempotency key {refund106['idempotency_key']}).

No new refund request has been raised, because a return may have only one completed refund. The customer has been told the processed date and that bank posting can take up to 7 business days. Please let me know if a payment trace is needed later.

{INTERNAL_SIGN}""",
        extra_headers=_headers(r106, internal=True))))

    # ---- R108: repairable laptop thread
    refund108 = r108.refunds[0] if r108.refunds else None
    refund_line = (
        f"Your refund request of {inr(refund108['refund_amount'])} has been raised and is pending approval (status: {refund108['refund_status']}). Refunds of this value need sign-off from our returns supervisor and finance team."
        if refund108 else "Our team will confirm the refund next steps shortly."
    )
    msgs.append(("support_R108_inspection_update_keyboard_damage.eml", r108, Email(
        sender=SUPPORT, to=_cust(r108),
        subject=f"Update on your return {r108.return_id} - TechNova Ultrabook 14",
        sent_at=datetime(2026, 3, 8, 11, 15), message_id=_mid("r108-1"),
        body=f"""Dear {r108['customer_name']},

We received your TechNova Ultrabook 14 (serial LT2044, order {r108['order_id']}) on {d(r108.received)} and our inspection team checked it on 2026-03-07. They confirmed the keyboard damage you reported: the J, K and right Shift keys are damaged, and J and Shift do not register. Everything else on the laptop passed our tests.

{refund_line} We will email you as soon as it is approved.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r108))))
    msgs.append(("support_R108_repair_task_request.eml", r108, Email(
        sender=ANALYST, to=REFURB,
        subject="R108 - repair task: TechNova Ultrabook 14 keyboard/top-case replacement (LT2044)",
        sent_at=datetime(2026, 3, 8, 14, 40), message_id=_mid("r108-2"),
        body=f"""Hi Refurbishment team,

Please create a repair task for return R108:
- Unit: TechNova Ultrabook 14, serial LT2044 (matches the order line)
- Inspection IR-2026-00008: keyboard damage (J and K keycaps cracked, right Shift missing, J and right Shift not registering); all other diagnostics pass; battery health 94%
- Proposed recovery: repair_and_resell, keyboard/top-case replacement under RFB-LT-2025-01, then regrade as refurbished

Please confirm parts availability and the expected bench time.

{INTERNAL_SIGN}""",
        extra_headers=_headers(r108, internal=True))))
    msgs.append(("support_R108_repair_parts_confirmation.eml", r108, Email(
        sender=REFURB, to=ANALYST,
        subject="Re: R108 - repair task: TechNova Ultrabook 14 keyboard/top-case replacement (LT2044)",
        sent_at=datetime(2026, 3, 10, 10, 5), message_id=_mid("r108-3"),
        in_reply_to=_mid("r108-2"), references=[_mid("r108-2")],
        body="""Hi,

Repair task logged for R108. We have no TC-IN layout top-case in stock; we have requested one from the TechNova supply account (S005), ETA 7–10 days. Bench time is about 2.5 hours, plus a 4-hour burn-in. After repair the unit qualifies for Refurbished Grade A if the cosmetic check passes.

Regards,
Refurbishment Centre, Bhiwandi""",
        extra_headers=_headers(r108, internal=True))))

    # ---- R104: delivery damage
    c104 = case["R104"]
    msgs.append(("support_R104_carrier_damage_claim.eml", r104, Email(
        sender=ANALYST, to=CARRIER,
        subject=f"Transit damage claim - shipment for order {r104['order_id']} (delivery {r104['delivery_id']})",
        sent_at=datetime(2026, 3, 15, 16, 0), message_id=_mid("r104-1"),
        body=f"""Dear Claims team,

We are filing a transit damage claim for delivery {r104['delivery_id']} (order {r104['order_id']}), delivered on {d(r104.delivery)}.

Your delivery scan recorded: "{r104['delivery_issue']}"

Our inspection (IR-2026-00004, 2026-03-14) found a cracked front grille and an impact dent on the left side panel, consistent with the crushed carton corners. The product is a HomeHive Air Purifier 300, value {r104.price}.

Please acknowledge the claim and share the hub handling log for this consignment. ShopSphere reference: investigation case {c104['case_id']} (delivery_dispute).

Regards,
{INTERNAL_SIGN}""",
        extra_headers=_headers(r104, internal=True))))
    msgs.append(("support_R104_customer_damage_update.eml", r104, Email(
        sender=SUPPORT, to=_cust(r104),
        subject=f"Your damaged air purifier - return {r104.return_id}",
        sent_at=datetime(2026, 3, 15, 17, 30), message_id=_mid("r104-2"),
        in_reply_to="<cmp-2026-0104@customers.shopsphere.invalid>",
        references=["<cmp-2026-0104@customers.shopsphere.invalid>"],
        body=f"""Dear {r104['customer_name']},

Thank you for reporting the damage quickly and for the photos. Our inspection confirmed the damage, and our delivery partner's records also note the crushed carton. You will not be charged for damage that happened in transit.

Your refund needs approval because of the order value. We will confirm by email once it is approved.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r104))))

    # ---- R110: conflicting inspections
    c110 = case["R110"]
    msgs.append(("support_R110_conflicting_inspections_escalation.eml", r110, Email(
        sender=ANALYST, to=SUPERVISOR,
        subject=f"[Case {c110['case_id']}] R110 - two inspections disagree, tie-break test needed",
        sent_at=datetime(2026, 3, 14, 12, 20), message_id=_mid("r110-1"),
        body=f"""Hi,

Return R110 (HomeHive Air Purifier 300, order O110) has two inspection records from 2026-03-13 that disagree:

- IR-2026-00010 (12:00): fault reproduced (E3 shutdown in 3 of 3 cycles); defect verified Yes; result PASS.
- IR-2026-00011 (18:00): 60-minute run with no fault; defect verified No; result FAIL.

I have not taken a refund or recovery decision. The refund request ({inr(r110.refunds[0]['refund_amount'])}) stays at "{r110.refunds[0]['refund_status']}" while case {c110['case_id']} (conflicting_evidence) is open. Could you approve an independent tie-break test (4 hours or more at mains voltage, a third technician) and let me know who should run it?

{INTERNAL_SIGN}""",
        extra_headers=_headers(r110, internal=True))))
    msgs.append(("support_R110_customer_review_delay.eml", r110, Email(
        sender=SUPPORT, to=_cust(r110),
        subject=f"Your return {r110.return_id} - review in progress",
        sent_at=datetime(2026, 3, 15, 10, 10), message_id=_mid("r110-2"),
        body=f"""Dear {r110['customer_name']},

Thank you for your patience. Our technicians are still reviewing the air purifier you returned (order {r110['order_id']}). We are running one more test to confirm the shutdown fault you described before we make a decision. You do not need to do anything at the moment.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r110))))

    # ---- R113: missing inspection
    msgs.append(("support_R113_return_received_inspection_pending.eml", r113, Email(
        sender=SUPPORT, to=_cust(r113),
        subject=f"We've received your return {r113.return_id}",
        sent_at=datetime(2026, 3, 14, 18, 0), message_id=_mid("r113-1"),
        body=f"""Dear {r113['customer_name']},

Your FlexFit USB-C Hub 7-in-1 (order {r113['order_id']}) reached our returns centre on {d(r113.received)}. It is waiting for inspection. We will contact you once the inspection is done.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r113))))
    msgs.append(("support_R113_internal_no_inspection_record.eml", r113, Email(
        sender=ANALYST, to=WAREHOUSE,
        subject="R113 - received 2026-03-14 but no inspection record; please schedule inspection",
        sent_at=datetime(2026, 3, 18, 9, 45), message_id=_mid("r113-2"),
        body=f"""Hi Warehouse team,

Return R113 (FlexFit USB-C Hub 7-in-1, order {r113['order_id']}) shows status "{r113['return_status']}" with a received date of {d(r113.received)}, but there is no inspection record in the system and no inspection report on file.

The customer reports that the USB-A ports stopped working (reason: defective). Without an inspection we have insufficient evidence for a decision. Please create an inspection task and confirm the bin location of the unit.

No refund will be requested until an inspection is recorded.

{INTERNAL_SIGN}""",
        extra_headers=_headers(r113, internal=True))))

    # ---- R115: unsafe
    c115 = case["R115"]
    msgs.append(("support_R115_safety_quarantine_notice.eml", r115, Email(
        sender=ANALYST, to=SAFETY, cc=f"{SUPERVISOR}, {WAREHOUSE}",
        subject=f"[SAFETY][Case {c115['case_id']}] R115 HomeHive Air Purifier 300 HA9933 - unsafe, no resale",
        sent_at=datetime(2026, 3, 14, 16, 30), message_id=_mid("r115-1"),
        body=f"""Product Safety Lead,

Inspection IR-2026-00015 (2026-03-14) classified the returned HomeHive Air Purifier 300, serial HA9933 (return R115, order O115), as UNSAFE. Findings: scorch marks and melted plastic at the power inlet, burning odour, and a failed insulation resistance test.

Actions taken:
- Unit quarantined in the hazardous-goods cage, tagged QUARANTINE - DO NOT RESELL.
- Investigation case {c115['case_id']} (safety_concern, priority {c115['priority']}) opened.
- Disposition restricted to recycle or dispose per RFB-SAF-2025-02. No resale, refurbishment for resale, or return to stock.
- Supplier S001 to be notified through a supplier defect report.

Please advise if a field safety notice should be considered.

{INTERNAL_SIGN}""",
        extra_headers=_headers(r115, internal=True))))
    msgs.append(("support_R115_customer_safety_acknowledgement.eml", r115, Email(
        sender=SUPPORT, to=_cust(r115),
        subject=f"Your air purifier safety report - return {r115.return_id}",
        sent_at=datetime(2026, 3, 15, 9, 0), message_id=_mid("r115-2"),
        in_reply_to="<cmp-2026-0115@customers.shopsphere.invalid>",
        references=["<cmp-2026-0115@customers.shopsphere.invalid>"],
        body=f"""Dear {r115['customer_name']},

Thank you for stopping use of the air purifier and reporting this to us straight away. Our inspection team has confirmed a safety issue with the unit. It has been isolated and will not be resold. It will be sent for safe recycling.

Our team is reviewing your return as a priority. We will contact you shortly with the resolution.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r115))))

    # ---- one message each for the remaining scenarios
    msgs.append(("support_R101_refund_submitted_for_approval.eml", r101, Email(
        sender=SUPPORT, to=_cust(r101),
        subject=f"Your return {r101.return_id} has been inspected",
        sent_at=datetime(2026, 3, 13, 17, 0), message_id=_mid("r101-1"),
        body=f"""Dear {r101['customer_name']},

Your FlexFit USB-C Hub 7-in-1 (order {r101['order_id']}) was received on {d(r101.received)} and inspected on 2026-03-13. Everything was in order and all items were present. Your return was raised {r101.days_after_delivery} days after delivery, well within our 30-day window for accessories.

Your refund of {r101.price} will now be submitted for approval. We will confirm once it has been processed.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r101))))
    msgs.append(("support_R103_outside_return_window_review.eml", r103, Email(
        sender=SUPPORT, to=_cust(r103),
        subject=f"Re: Want to return headphones - order {r103['order_id']}",
        sent_at=datetime(2026, 1, 22, 11, 30), message_id=_mid("r103-1"),
        in_reply_to="<cmp-2026-0103@customers.shopsphere.invalid>",
        references=["<cmp-2026-0103@customers.shopsphere.invalid>"],
        body=f"""Dear {r103['customer_name']},

Thank you for getting in touch. Your SoundPeak Wireless Headphones Pro were delivered on {d(r103.delivery)}, and your return request was raised on {d(r103.requested)}, which is {r103.days_after_delivery} days after delivery. Our electronics return policy allows returns within 30 days from delivery, so this request is outside the standard return window.

We have registered your request as return {r103.return_id} and passed it to our team for a policy exception review. Please send the headphones back in their original box using the pickup we will arrange. We will let you know the outcome of the review.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r103))))
    msgs.append(("support_R105_defect_verified_warranty_review.eml", r105, Email(
        sender=SUPPORT, to=_cust(r105),
        subject=f"Inspection result for return {r105.return_id}",
        sent_at=datetime(2026, 2, 28, 16, 20), message_id=_mid("r105-1"),
        body=f"""Dear {r105['customer_name']},

Our technicians have confirmed the fault on your FlexFit USB-C Hub 7-in-1 (serial EL5520, order {r105['order_id']}): the hub does not pass charge to your laptop and the HDMI output drops out. Thank you for describing it so clearly in chat.

Your return is now with our returns team for resolution. We will confirm the refund once it is approved.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r105))))
    msgs.append(("support_R107_additional_information_request.eml", r107, Email(
        sender=SUPPORT, to=_cust(r107),
        subject=f"Your return {r107.return_id} - we need a little more information",
        sent_at=datetime(2026, 3, 14, 13, 10), message_id=_mid("r107-1"),
        body=f"""Dear {r107['customer_name']},

Thank you for returning the item from order {r107['order_id']}. During inspection we found that some details of the returned item differ from our dispatch record, and the carry case and audio cable were not in the box. To complete our review, could you please:

- send a photo of the item and packaging exactly as you received it, if you still have one, and
- check whether the carry case or 3.5 mm cable may have been kept separately.

Your return is under review (reference: case {case['R107']['case_id']}). We will be in touch once it is complete.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r107))))
    msgs.append(("support_R109_missing_accessories_follow_up.eml", r109, Email(
        sender=SUPPORT, to=_cust(r109),
        subject=f"Return {r109.return_id} - missing travel pouch and user guide",
        sent_at=datetime(2026, 3, 14, 15, 0), message_id=_mid("r109-1"),
        body=f"""Dear {r109['customer_name']},

We inspected the FlexFit USB-C Hub 7-in-1 (serial EL8812, order {r109['order_id']}) on 2026-03-14. The hub works correctly. The travel pouch and the printed user guide were not in the box we received.

Because the return is not complete, it has gone to our returns team for review under our accessories policy. If you have the pouch, please let us know and we will arrange a pickup.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r109))))
    msgs.append(("support_R111_product_mismatch_case_opened.eml", r111, Email(
        sender=SUPPORT, to=_cust(r111),
        subject=f"Your return {r111.return_id} - checking the item you received",
        sent_at=datetime(2026, 3, 22, 12, 30), message_id=_mid("r111-1"),
        in_reply_to="<cmp-2026-0111@customers.shopsphere.invalid>",
        references=["<cmp-2026-0111@customers.shopsphere.invalid>"],
        body=f"""Dear {r111['customer_name']},

Thank you for returning the shirt from order {r111['order_id']}. We confirmed that the label on the shirt does not match the item you ordered. We are now checking our packing records to find out how this happened (reference: case {case['R111']['case_id']}). Once that is done we will arrange your exchange or refund.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r111))))
    msgs.append(("support_R112_warranty_review_update.eml", r112, Email(
        sender=SUPPORT, to=_cust(r112),
        subject=f"Warranty review for your TechNova Ultrabook 14 - return {r112.return_id}",
        sent_at=datetime(2026, 2, 18, 10, 40), message_id=_mid("r112-1"),
        in_reply_to="<cmp-2026-0112@customers.shopsphere.invalid>",
        references=["<cmp-2026-0112@customers.shopsphere.invalid>"],
        body=f"""Dear {r112['customer_name']},

We inspected your TechNova Ultrabook 14 (serial LT8891, order {r112['order_id']}) on 2026-02-17 and confirmed the unexpected shutdowns you reported. The laptop is within its 24-month warranty.

Your case is now with our warranty team, who will confirm whether a repair through TechNova authorised service or a refund is the best option. We will update you within 3 business days.

{CUSTOMER_SIGN}""",
        extra_headers=_headers(r112))))
    msgs.append(("support_R114_internal_data_correction.eml", r114, Email(
        sender=ANALYST, to=SUPERVISOR,
        subject=f"[Case {case['R114']['case_id']}] R114 - return reason vs line item discrepancy",
        sent_at=datetime(2026, 3, 17, 15, 25), message_id=_mid("r114-1"),
        body=f"""Hi,

R114 (order {r114['order_id']}) needs a data correction before we decide it:
- Return reason on record: {r114['return_reason']}
- Order line item: {r114['product_name']} ({r114['product_id']}, category {r114.category})
- Inspection system note (IR-2026-00014): "Return reason references size mismatch but line item is accessory SKU."

The physical item matches the fashion line item, so the inspection note's reference to an accessory SKU appears to be a record error. I recommend correcting the note and confirming the size details with the customer. Case {case['R114']['case_id']} (data_correction) remains open. Additional verification required.

{INTERNAL_SIGN}""",
        extra_headers=_headers(r114, internal=True))))
    return msgs


def _bulk_messages(data: ShopSphereData, exclude: set[str]) -> list[tuple[str, ReturnContext, Email]]:
    bulk = [ctx for ctx in data.bulk() if ctx.return_id not in exclude]

    def first(pred) -> ReturnContext:
        return next(ctx for ctx in bulk if pred(ctx))

    resolved = first(lambda c: c["return_status"] == "resolved" and c.completed_refund is not None)
    requested = first(lambda c: c["return_status"] == "requested")
    inspecting = first(lambda c: c["return_status"] == "inspecting" and c.received is not None)
    investigating = first(lambda c: c["return_status"] == "investigating")

    refund = resolved.completed_refund
    processed = datetime.fromisoformat(refund["processed_date"])
    out = [
        (f"support_{resolved.return_id}_refund_processed.eml", resolved, Email(
            sender=SUPPORT, to=_cust(resolved),
            subject=f"Refund processed for return {resolved.return_id}",
            sent_at=processed.replace(hour=15), message_id=_mid(f"{resolved.return_id.lower()}-1"),
            body=f"""Dear {resolved['customer_name']},

Your return {resolved.return_id} (order {resolved['order_id']}, {resolved.product_label}) is complete. A refund of {inr(refund['refund_amount'])} was processed on {d(processed)} to your original payment method. Please allow 5–7 business days for your bank to show the credit.

{CUSTOMER_SIGN}""",
            extra_headers={**_headers(resolved), "X-ShopSphere-Refund-ID": str(refund["refund_id"])})),
        (f"support_{requested.return_id}_pickup_scheduled.eml", requested, Email(
            sender=SUPPORT, to=_cust(requested),
            subject=f"Pickup scheduled for return {requested.return_id}",
            sent_at=(requested.requested + timedelta(days=1)).replace(hour=10), message_id=_mid(f"{requested.return_id.lower()}-1"),
            body=f"""Dear {requested['customer_name']},

We have received your return request {requested.return_id} for order {requested['order_id']} ({requested.product_label}). A pickup has been scheduled for {d(requested.requested + timedelta(days=3))} between 10:00 and 18:00. Please keep the item packed, with all accessories, in its original packaging if possible.

{CUSTOMER_SIGN}""",
            extra_headers=_headers(requested))),
        (f"support_{inspecting.return_id}_inspection_in_progress.eml", inspecting, Email(
            sender=SUPPORT, to=_cust(inspecting),
            subject=f"Your return {inspecting.return_id} is being inspected",
            sent_at=(inspecting.received + timedelta(days=1)).replace(hour=12), message_id=_mid(f"{inspecting.return_id.lower()}-1"),
            body=f"""Dear {inspecting['customer_name']},

Your return {inspecting.return_id} (order {inspecting['order_id']}) arrived at our returns centre on {d(inspecting.received)} and is now being inspected. We will email you with the result and next steps.

{CUSTOMER_SIGN}""",
            extra_headers=_headers(inspecting))),
        (f"support_{investigating.return_id}_under_review.eml", investigating, Email(
            sender=SUPPORT, to=_cust(investigating),
            subject=f"Your return {investigating.return_id} is under review",
            sent_at=(investigating.requested + timedelta(days=5)).replace(hour=11), message_id=_mid(f"{investigating.return_id.lower()}-1"),
            body=f"""Dear {investigating['customer_name']},

Thank you for your patience with return {investigating.return_id} (order {investigating['order_id']}). Our returns team needs to verify a few details before completing it. We may contact you for photos or more information. No action is needed from you right now.

{CUSTOMER_SIGN}""",
            extra_headers=_headers(investigating))),
    ]
    return out


def build(corpus: Corpus, data: ShopSphereData) -> None:
    scenario = _scenario_messages(data)
    messages = scenario + _bulk_messages(data, exclude=set())
    for filename, ctx, email in messages:
        corpus.add_email(email, filename, "support_communication", return_id=ctx.return_id, product_id=ctx["product_id"])
