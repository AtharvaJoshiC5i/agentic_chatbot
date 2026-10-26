"""Realistic (fictional) product catalog and text banks for synthetic data.

Everything here feeds the generator through a dedicated RNG stream so the
reserved R101-R115 scenarios stay byte-for-byte stable.
"""

from __future__ import annotations

# (model name, noun used in customer text, min INR, max INR, warranty-month choices)
CATALOG: dict[str, list[tuple[str, str, int, int, tuple[int, ...]]]] = {
    "electronics": [
        ("True Wireless Earbuds", "earbuds", 1499, 6999, (6, 12)),
        ("Bluetooth Speaker", "speaker", 1999, 9999, (12,)),
        ("Fitness Smartwatch", "smartwatch", 2999, 19999, (12,)),
        ("Power Bank 20000mAh", "power bank", 1299, 3499, (6, 12)),
        ("Wireless Mouse", "mouse", 499, 2499, (12,)),
        ("Mechanical Keyboard", "keyboard", 1999, 8999, (12,)),
        ("27-inch Monitor", "monitor", 9999, 29999, (24,)),
        ("10-inch Tablet", "tablet", 12999, 34999, (12, 24)),
        ("Gaming Laptop 15", "laptop", 54999, 89999, (24,)),
        ("Noise Cancelling Headset", "headset", 3999, 17999, (12, 24)),
    ],
    "fashion": [
        ("Slim Fit Denim Jeans", "jeans", 999, 3499, (0,)),
        ("Cotton Polo T-Shirt", "t-shirt", 499, 1799, (0,)),
        ("Running Shoes", "shoes", 1499, 5999, (0, 6)),
        ("Leather Belt", "belt", 599, 1999, (0,)),
        ("Padded Winter Jacket", "jacket", 2499, 7999, (0, 6)),
        ("Cotton Kurta Set", "kurta set", 899, 3299, (0,)),
        ("Casual Sneakers", "sneakers", 1299, 4499, (0, 6)),
    ],
    "home_appliances": [
        ("Mixer Grinder 750W", "mixer grinder", 2499, 6999, (12, 24)),
        ("Digital Air Fryer 4L", "air fryer", 3999, 9999, (12, 24)),
        ("Robot Vacuum Cleaner", "robot vacuum", 9999, 29999, (12, 24)),
        ("RO Water Purifier", "water purifier", 8999, 21999, (12, 24)),
        ("Induction Cooktop", "induction cooktop", 1999, 4999, (12,)),
        ("Ceiling Fan 1200mm", "ceiling fan", 1999, 5499, (24,)),
        ("Room Heater 2000W", "room heater", 1499, 3999, (12,)),
        ("Steam Iron", "steam iron", 1299, 3299, (12,)),
    ],
    "accessories": [
        ("Laptop Backpack 25L", "backpack", 799, 3499, (0, 6)),
        ("Silicone Phone Case", "phone case", 299, 999, (0,)),
        ("USB-C Cable 2m", "cable", 299, 899, (6, 12)),
        ("65W GaN Charger", "charger", 1299, 2999, (6, 12)),
        ("Tempered Glass Screen Guard", "screen guard", 199, 699, (0,)),
        ("Laptop Stand", "laptop stand", 899, 2999, (0, 6)),
        ("Webcam 1080p", "webcam", 1499, 4499, (6, 12)),
    ],
}

VARIANTS = ("", "", " Lite", " Plus", " Pro", " 2", " Max")

DAMAGE_DETAIL = {
    "electronics": ["a cracked casing near the charging port", "scratches and a chipped corner on the screen bezel", "a bent hinge and a dented corner"],
    "home_appliances": ["a cracked front panel", "a dented body and a broken control knob", "a cracked water tank housing"],
    "accessories": ["a cracked outer shell", "a frayed cable sheath near the connector", "a bent connector housing"],
    "fashion": ["a torn seam at the shoulder", "a stain on the front panel", "snagged fabric near the hem"],
}
FAULT_DETAIL = {
    "electronics": ["the unit does not power on after a full charge", "the battery drains within minutes", "the unit shuts down unexpectedly under light load", "one audio channel is dead"],
    "home_appliances": ["the motor does not start at any speed", "the unit switches off after a few minutes", "the display lights up but there is no output"],
    "accessories": ["the host device does not detect it on most ports", "the output is unstable and disconnects", "the connector is loose and drops the connection"],
    "fashion": ["the stitching along the placket has failed", "the colour bled during a test wash", "the zip does not close"],
}
MISSING_ITEMS = {
    "electronics": "the charging cable and the user manual",
    "home_appliances": "the power cord and the warranty card",
    "accessories": "the packaging insert and the user guide",
    "fashion": "the spare buttons and the garment bag",
}
MISMATCH_DETAIL = {
    "electronics": "the listing said it supports fast charging but it charges slowly with the recommended adapter",
    "home_appliances": "the listing showed a timer function that this model does not have",
    "accessories": "the material and finish differ from the listing photos",
    "fashion": "the fabric is thinner and the colour duller than in the listing photos",
}
OTHER_TEXT = (
    "I want to confirm that my return pickup is still active.",
    "I was charged a return fee that I was not told about.",
    "I would like store credit instead of a refund if possible.",
)
UNSAFE_DETAIL = {
    "electronics": ["Battery swelling detected; unit isolated from stock.", "Overheating and discolouration near the charging circuit; unit isolated."],
    "home_appliances": ["Burn marks near the power inlet and a failed insulation test; unit isolated.", "Melted plastic around the motor housing; unit isolated."],
}

DELIVERY_ISSUES_DAMAGE = (
    "Carton crushed at one corner on arrival scan.",
    "Outer packaging found torn at hand-over.",
    "Visible dent on carton recorded by delivery partner.",
)
DELIVERY_ISSUES_OTHER = (
    "Delivery attempted twice; completed on the third attempt.",
    "Delivered 3 days after the promised date due to a hub delay.",
    "Delivered to a neighbour; recipient confirmed by phone.",
)

REASON_WEIGHTS: dict[str, dict[str, float]] = {
    "electronics": {"changed_mind": 0.14, "damaged": 0.12, "defective": 0.18, "not_functioning": 0.20, "missing_accessories": 0.10, "wrong_product": 0.07, "not_as_described": 0.10, "other": 0.09},
    "home_appliances": {"changed_mind": 0.14, "damaged": 0.18, "defective": 0.16, "not_functioning": 0.18, "missing_accessories": 0.10, "wrong_product": 0.06, "not_as_described": 0.10, "other": 0.08},
    "accessories": {"changed_mind": 0.20, "damaged": 0.10, "defective": 0.17, "not_functioning": 0.12, "missing_accessories": 0.10, "wrong_product": 0.08, "size_color_incorrect": 0.08, "not_as_described": 0.10, "other": 0.05},
    "fashion": {"changed_mind": 0.20, "damaged": 0.06, "defective": 0.08, "wrong_product": 0.08, "size_color_incorrect": 0.34, "not_as_described": 0.16, "other": 0.08},
}

# Return window in days from delivery (matches the return policy documents).
RETURN_WINDOW = {"electronics": 30, "fashion": 15, "home_appliances": 30, "accessories": 30}
