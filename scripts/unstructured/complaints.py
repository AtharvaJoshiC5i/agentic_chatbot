"""Batch C (part 1): fifty customer complaints (EML and TXT)."""

from __future__ import annotations

from datetime import datetime, timedelta

from .context import ReturnContext, ShopSphereData, d, stable_index
from .corpus import Corpus
from .render import Email

SUPPORT = "ShopSphere Customer Care <support@shopsphere.invalid>"


def _ticket(return_id: str, suffix: str = "") -> str:
    return f"CMP-2026-{int(return_id[1:]):04d}{suffix}"


def _customer(ctx: ReturnContext) -> str:
    return f"{ctx['customer_name']} <{ctx['customer_email']}>"


def _at(day: datetime, hour: int, minute: int = 0) -> datetime:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _txt(channel: str, ticket: str, ctx: ReturnContext, when: datetime, subject: str, body: str) -> str:
    return "\n".join(
        [
            "ShopSphere Retail — Customer Complaint Record",
            f"Ticket ID: {ticket}",
            f"Channel: {channel}",
            f"Received: {when.strftime('%Y-%m-%d %H:%M')} IST",
            f"Customer ID: {ctx['customer_id']}",
            f"Customer name: {ctx['customer_name']}",
            f"Order ID: {ctx['order_id']}",
            f"Return ID: {ctx.return_id}",
            f"Product: {ctx.product_label}",
            f"Subject: {subject}",
            "-" * 60,
            body.strip(),
            "-" * 60,
            "Internal use only — ShopSphere Retail.",
        ]
    )


# --------------------------------------------------------------------- scenarios


def _scenario_complaints(data: ShopSphereData) -> list[dict]:
    g = data.get
    r = {rid: g(rid) for rid in [f"R{i}" for i in range(101, 116)]}
    return [
        {
            "ctx": r["R101"], "fmt": "txt", "channel": "Web return form", "slug": "change_of_mind_hub",
            "when": _at(r["R101"].requested, 10, 12),
            "subject": "Return request - USB-C hub not needed",
            "body": f"""Reason selected: Changed my mind

Hi, I ordered the FlexFit USB-C Hub 7-in-1 on order {r['R101']['order_id']} and it was delivered on {d(r['R101'].delivery)}. My office has now issued me a docking station so I don't need the hub any more. I opened the box to check it but have not really used it. Everything is back in the box including the pouch and guide. Please arrange a pickup and refund to my original payment method.

Thanks,
{r['R101']['customer_name']}""",
        },
        {
            "ctx": r["R102"], "fmt": "eml", "slug": "headphones_left_side_no_sound",
            "when": _at(r["R102"].requested, 9, 41),
            "subject": f"Headphones not working - order {r['R102']['order_id']}",
            "body": f"""Hello ShopSphere team,

I bought SoundPeak Wireless Headphones Pro on order {r['R102']['order_id']}. They were delivered on {d(r['R102'].delivery)}. Since yesterday the left side has no sound at all. I tried re-pairing, a factory reset and a different phone, and it is still only the right side.

The invoice shows serial number HP9081. I would like to return them for a refund.

Regards,
{r['R102']['customer_name']}""",
        },
        {
            "ctx": r["R102"], "fmt": "eml", "slug": "follow_up_on_verification_hold", "suffix": "-F",
            "when": datetime(2026, 3, 16, 19, 5),
            "subject": f"Re: Return {r['R102'].return_id} on hold - why?",
            "body": f"""Hi,

I got your email saying my return {r['R102'].return_id} needs additional verification because the serial number does not match. I packed the same headphones that came in the box. I don't understand how the number could be different. I can send a photo of the outer box with the barcode sticker if that helps.

How long will this take? It has been more than a week.

{r['R102']['customer_name']}""",
        },
        {
            "ctx": r["R103"], "fmt": "eml", "slug": "headphones_return_after_two_months",
            "when": _at(r["R103"].requested, 20, 30),
            "subject": f"Want to return headphones - order {r['R103']['order_id']}",
            "body": f"""Dear Customer Care,

I purchased SoundPeak Wireless Headphones Pro (order {r['R103']['order_id']}), delivered on {d(r['R103'].delivery)}. They work fine but I received the same model as a gift, so I don't need a second pair. I know it has been a while since delivery (about 8 weeks) but they are barely used and I still have the box.

Can I still return them? Please let me know.

Thanks,
{r['R103']['customer_name']}""",
        },
        {
            "ctx": r["R104"], "fmt": "eml", "slug": "air_purifier_arrived_damaged",
            "when": datetime(2026, 3, 7, 11, 18),
            "subject": f"Air purifier delivered damaged - order {r['R104']['order_id']} (photos attached)",
            "body": f"""Hello,

My HomeHive Air Purifier 300 (order {r['R104']['order_id']}) was delivered yesterday, {d(r['R104'].delivery)}. The carton was badly crushed at two corners when it arrived, and the delivery person noted it on his device. When I opened it, the front grille was cracked and there is a dent on the left side. When I switch it on, it makes a rattling sound.

I took photos of the carton on all sides, the shipping label, and the damage. I have not used the product beyond switching it on once to check.

Please arrange a replacement or refund.

{r['R104']['customer_name']}""",
        },
        {
            "ctx": r["R105"], "fmt": "txt", "channel": "Live chat transcript", "slug": "hub_not_charging_laptop",
            "when": _at(r["R105"].requested, 15, 2),
            "subject": "USB-C hub stopped charging laptop",
            "body": f"""[15:02] Customer: hi, my flexfit usb c hub from order {r['R105']['order_id']} has stopped passing charge to my laptop
[15:03] Agent (Priya): Sorry to hear that. When did you first notice the issue?
[15:03] Customer: around 10 days after delivery. laptop shows not charging when charger is in the hub. direct to laptop it charges fine
[15:05] Agent (Priya): Thank you. Does anything else misbehave?
[15:05] Customer: hdmi screen also blinks off every few minutes
[15:06] Agent (Priya): Could you read the serial on the underside of the hub?
[15:07] Customer: EL5520
[15:08] Agent (Priya): Thank you. I have raised return {r['R105'].return_id} with reason "defective". A pickup will be scheduled and the hub will be inspected at our warehouse.
[15:08] Customer: ok thanks""",
        },
        {
            "ctx": r["R106"], "fmt": "eml", "slug": "hub_hdmi_not_working",
            "when": _at(r["R106"].requested, 12, 47),
            "subject": f"HDMI port on hub not working - {r['R106']['order_id']}",
            "body": f"""Hi team,

The HDMI port on the FlexFit USB-C Hub 7-in-1 I got on order {r['R106']['order_id']} does not give any display. I tried two monitors and two HDMI cables. The USB ports work. It was delivered on {d(r['R106'].delivery)}.

Please take it back and refund.

Thanks,
{r['R106']['customer_name']}""",
        },
        {
            "ctx": r["R107"], "fmt": "txt", "channel": "Call centre note", "slug": "headphones_wrong_item_received",
            "when": _at(r["R107"].requested, 17, 25),
            "subject": "Customer reports wrong item received",
            "body": f"""Call summary (agent: Farhan, inbound, 9 min)

Customer called about order {r['R107']['order_id']} (SoundPeak Wireless Headphones Pro, delivered {d(r['R107'].delivery)}). The customer says the item received is not what was ordered and wants to return it. When asked, the customer could not find the carry case in the box. The customer agreed to pack the item in its original box for pickup.

Raised return {r['R107'].return_id}, reason "wrong_product". Advised the customer that the warehouse will inspect the item and that we will contact them if we need any more information. Customer was polite and cooperative.""",
        },
        {
            "ctx": r["R108"], "fmt": "eml", "slug": "laptop_keys_cracked",
            "when": _at(r["R108"].requested, 10, 5),
            "subject": f"Ultrabook keyboard damaged - order {r['R108']['order_id']}",
            "body": f"""Dear ShopSphere,

My TechNova Ultrabook 14 (order {r['R108']['order_id']}, serial LT2044) has a damaged keyboard. The J and K keys are cracked and the right Shift key has come off. J and Shift do not type at all. The rest of the laptop works fine.

I would like to return it. Please tell me the next steps.

Regards,
{r['R108']['customer_name']}""",
        },
        {
            "ctx": r["R109"], "fmt": "txt", "channel": "Web return form", "slug": "hub_pouch_missing",
            "when": _at(r["R109"].requested, 8, 50),
            "subject": "Items missing from box",
            "body": f"""Reason selected: Missing accessories

The FlexFit USB-C Hub 7-in-1 (order {r['R109']['order_id']}) came without the travel pouch shown on the product page. The hub works but I want the complete product as advertised, otherwise I want to return it.

- {r['R109']['customer_name']}""",
        },
        {
            "ctx": r["R110"], "fmt": "eml", "slug": "air_purifier_switches_off_e3",
            "when": _at(r["R110"].requested, 21, 14),
            "subject": f"Air purifier turns off by itself - E3 error (order {r['R110']['order_id']})",
            "body": f"""Hello,

The HomeHive Air Purifier 300 I received on {d(r['R110'].delivery)} (order {r['R110']['order_id']}) keeps switching off by itself after a few minutes and shows "E3" on the display. It happens every time. I cleaned the pre-filter and checked the filter is seated properly, as the manual says.

It is not usable like this. Please take it back.

Thank you,
{r['R110']['customer_name']}""",
        },
        {
            "ctx": r["R111"], "fmt": "eml", "slug": "shirt_different_item",
            "when": _at(r["R111"].requested, 13, 33),
            "subject": f"Received different shirt than ordered - {r['R111']['order_id']}",
            "body": f"""Hi,

I ordered the UrbanWeave Classic Cotton Shirt (order {r['R111']['order_id']}) but the shirt in the package is a different item. The tag on it shows a different product code from my order. I have not worn it and all tags are on.

Please arrange an exchange for the correct shirt or a refund.

Thanks,
{r['R111']['customer_name']}""",
        },
        {
            "ctx": r["R112"], "fmt": "eml", "slug": "laptop_random_shutdowns",
            "when": _at(r["R112"].requested, 18, 40),
            "subject": f"Laptop shutting down randomly - warranty (order {r['R112']['order_id']})",
            "body": f"""Dear Support,

My TechNova Ultrabook 14 (serial LT8891, order {r['R112']['order_id']}), delivered on {d(r['R112'].delivery)}, shuts down without warning several times a day, even when the battery is full and only a browser is open. I have updated the BIOS and drivers from the TechNova site and it still happens.

The laptop is under warranty. Please advise how to proceed with a repair or return.

Best regards,
{r['R112']['customer_name']}""",
        },
        {
            "ctx": r["R113"], "fmt": "txt", "channel": "Web return form", "slug": "hub_usb_ports_dead",
            "when": _at(r["R113"].requested, 11, 3),
            "subject": "Hub USB ports stopped working",
            "body": f"""Reason selected: Defective

The FlexFit USB-C Hub 7-in-1 from order {r['R113']['order_id']} (delivered {d(r['R113'].delivery)}) worked for two days and now neither USB-A port detects my mouse or pen drive. HDMI still works. Tried on two laptops.

Requesting refund.
{r['R113']['customer_name']}""",
        },
        {
            "ctx": r["R114"], "fmt": "txt", "channel": "Web return form", "slug": "shirt_wrong_size",
            "when": _at(r["R114"].requested, 16, 20),
            "subject": "Wrong size",
            "body": f"""Reason selected: Size / colour incorrect

The UrbanWeave Classic Cotton Shirt from order {r['R114']['order_id']} doesn't fit. The size is not what I expected. Unworn, tags attached. Please refund.

{r['R114']['customer_name']}""",
        },
        {
            "ctx": r["R115"], "fmt": "eml", "slug": "air_purifier_burning_smell",
            "when": _at(r["R115"].requested, 7, 55),
            "subject": f"URGENT: burning smell from air purifier - order {r['R115']['order_id']}",
            "body": f"""Hello,

Last night my HomeHive Air Purifier 300 (order {r['R115']['order_id']}, serial HA9933) started giving a strong burning smell. When I unplugged it, the area around the power socket at the back was black and the plastic looked melted. I have stopped using it and it is unplugged.

This is a safety issue. I have small children at home. Please collect it as soon as possible and tell me what you will do.

{r['R115']['customer_name']}""",
        },
    ]


# ------------------------------------------------------------------------- bulk

OPENERS = ("Hello ShopSphere team,", "Hi,", "Dear Customer Care,", "Good afternoon,", "To the returns team,", "Namaste,")
CLOSERS = ("Thanks,", "Regards,", "Please help at the earliest.\nThanks,", "Waiting for your reply.\n", "Thank you for your help.", "Kindly do the needful.\nRegards,")
EXTRA = (
    "",
    " This is quite disappointing because I ordered it for a family function.",
    " I have kept all the packaging.",
    " I have been a ShopSphere customer for a long time and this is the first time I've had a problem.",
    " I can share photos if needed.",
    "",
)

DAMAGE = {
    "electronics": "a cracked corner on the casing and scratches on the screen bezel",
    "home_appliances": "a dent on the side panel and a broken knob",
    "accessories": "the outer shell cracked and the cable sheath split near the plug",
    "fashion": "a torn seam near the shoulder",
}
FAULT = {
    "electronics": "It does not turn on even after charging overnight",
    "home_appliances": "The display lights up but the motor does not start at any setting",
    "accessories": "My laptop does not detect it on most ports",
    "fashion": "The stitching came apart along the buttons after the first wear",
}
TROUBLESHOOT = {
    "electronics": "a different charger and a reset",
    "home_appliances": "a different power socket",
    "accessories": "two different laptops",
    "fashion": "following the care label",
}
MISSING = {
    "electronics": "the charging cable and the user manual",
    "home_appliances": "the power cord and the warranty card",
    "accessories": "the packaging insert and the user guide",
    "fashion": "the spare buttons and the garment bag",
}
MISMATCH = {
    "electronics": "the listing said it supports fast charging but it charges very slowly with the recommended adapter",
    "home_appliances": "the listing showed a timer function but this unit does not have one",
    "accessories": "the material feels very different from what the photos show",
    "fashion": "the fabric is much thinner than described and the colour is duller than in the photos",
}
OTHER = (
    "the pickup agent did not come on the scheduled day, so I want to confirm my return is still active",
    "I was charged a return fee that I was not told about",
    "I want to know whether I can get store credit instead of a refund",
)


def _bulk_body(ctx: ReturnContext) -> tuple[str, str]:
    cat = ctx.category
    product = f"the item listed as “{ctx['product_name']}” ({ctx['product_id']})"
    order = ctx["order_id"]
    delivered = d(ctx.delivery)
    reason = ctx["return_reason"]
    if reason == "damaged":
        subject = f"Item received damaged - order {order}"
        text = f"I received {product} on order {order} on {delivered}. When I opened it I found {DAMAGE[cat]}."
    elif reason == "not_functioning":
        subject = f"Product not working - order {order}"
        text = f"{FAULT[cat]}. This is {product} from order {order}, delivered on {delivered}. I tried {TROUBLESHOOT[cat]} but nothing helped."
    elif reason == "wrong_product":
        subject = f"Wrong item delivered - order {order}"
        text = f"The package for order {order} (delivered {delivered}) does not contain {product}; it contains a different item. Please arrange a pickup and send the correct item or refund me."
    elif reason == "size_color_incorrect":
        what = "size" if cat == "fashion" else "colour/variant"
        subject = f"Incorrect {what} received - order {order}"
        text = f"The {what} of {product} that I received on order {order} is not the one I selected when ordering. I would like to return it."
    elif reason == "missing_accessories":
        subject = f"Items missing in box - order {order}"
        text = f"The box for {product} (order {order}, delivered {delivered}) did not have {MISSING[cat]}."
    elif reason == "changed_mind":
        subject = f"Return request - order {order}"
        text = f"I'd like to return {product} from order {order}. It is unused and still in its original packaging. I don't need it any more."
    elif reason == "defective":
        subject = f"Defective product - order {order}"
        text = f"{product[0].upper() + product[1:]} from order {order} worked for a few days and then developed a fault. {FAULT[cat]}."
    elif reason == "not_as_described":
        subject = f"Product not as described - order {order}"
        text = f"{product[0].upper() + product[1:]} (order {order}) is not as described: {MISMATCH[cat]}."
    else:
        subject = f"Question about my return - order {order}"
        text = f"I have a question about the return for order {order}: {OTHER[stable_index(ctx.return_id, len(OTHER))]}."
    # The description is stored in SQLite (customer_description); the complaint echoes it.
    text = f"{ctx['customer_description']} This is about order {order}, delivered on {delivered}."
    return subject, text


def _select_bulk(data: ShopSphereData, count: int) -> list[ReturnContext]:
    """Round-robin across return reasons so every reason is represented."""
    by_reason: dict[str, list[ReturnContext]] = {}
    for ctx in data.bulk():
        by_reason.setdefault(ctx["return_reason"], []).append(ctx)
    reasons = sorted(by_reason)
    chosen: list[ReturnContext] = []
    index = 0
    while len(chosen) < count:
        for reason in reasons:
            pool = by_reason[reason]
            if index < len(pool) and len(chosen) < count:
                chosen.append(pool[index])
        index += 1
    return sorted(chosen, key=lambda c: int(c.return_id[1:]))


def build(corpus: Corpus, data: ShopSphereData) -> None:
    for spec in _scenario_complaints(data):
        ctx: ReturnContext = spec["ctx"]
        ticket = _ticket(ctx.return_id, spec.get("suffix", ""))
        filename = f"complaint_{ctx.return_id}_{spec['slug']}.{spec['fmt']}"
        meta = {"return_id": ctx.return_id, "product_id": ctx["product_id"]}
        if spec["fmt"] == "eml":
            email = Email(
                sender=_customer(ctx),
                to=SUPPORT,
                subject=spec["subject"],
                sent_at=spec["when"],
                body=spec["body"],
                message_id=f"<{ticket.lower()}@customers.shopsphere.invalid>",
                extra_headers={"X-ShopSphere-Ticket": ticket, "X-ShopSphere-Return-ID": ctx.return_id, "X-ShopSphere-Order-ID": ctx["order_id"]},
            )
            corpus.add_email(email, filename, "customer_complaint", **meta)
        else:
            text = _txt(spec["channel"], ticket, ctx, spec["when"], spec["subject"], spec["body"])
            corpus.add_text(text, filename, "customer_complaint", spec["when"].strftime("%Y-%m-%d"), **meta)

    scenario_count = len(_scenario_complaints(data))
    for position, ctx in enumerate(_select_bulk(data, 50 - scenario_count)):
        subject, text = _bulk_body(ctx)
        k = stable_index(f"voice-{ctx.return_id}", len(OPENERS))
        body = f"{OPENERS[k]}\n\n{text}{EXTRA[k]}\n\n{CLOSERS[k]}\n{ctx['customer_name']}"
        when = _at(ctx.requested, 9 + stable_index(ctx.return_id, 11), stable_index(ctx.return_id + "m", 60))
        ticket = _ticket(ctx.return_id)
        filename_base = f"complaint_{ctx.return_id}_{ctx['return_reason']}_{ctx.category}"
        meta = {"return_id": ctx.return_id, "product_id": ctx["product_id"]}
        if position % 5 in (0, 2, 4):  # ~60% email, ~40% web form / chat exports
            email = Email(
                sender=_customer(ctx),
                to=SUPPORT,
                subject=subject,
                sent_at=when,
                body=body,
                message_id=f"<{ticket.lower()}@customers.shopsphere.invalid>",
                extra_headers={"X-ShopSphere-Ticket": ticket, "X-ShopSphere-Return-ID": ctx.return_id, "X-ShopSphere-Order-ID": ctx["order_id"]},
            )
            corpus.add_email(email, f"{filename_base}.eml", "customer_complaint", **meta)
        else:
            channel = "Web return form" if position % 2 else "Mobile app feedback"
            text = _txt(channel, ticket, ctx, when, subject, body)
            corpus.add_text(text, f"{filename_base}.txt", "customer_complaint", when.strftime("%Y-%m-%d"), **meta)
