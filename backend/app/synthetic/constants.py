"""Dataset volume targets and generation defaults."""

from dataclasses import dataclass

RANDOM_SEED = 42

RESERVED_RETURN_IDS = tuple(f"R{i}" for i in range(101, 116))


@dataclass(frozen=True)
class DatasetVolumes:
    customers: int = 500
    products: int = 100
    suppliers: int = 30
    orders: int = 2000
    order_items: int = 3000
    deliveries: int = 2000
    returns: int = 500
    inspections: int = 400
    refunds: int = 300
    investigation_cases: int = 100
    recovery_options: int = 600
    recovery_tasks: int = 100


VOLUMES = DatasetVolumes()

CATEGORY_WEIGHTS = {
    "electronics": 0.35,
    "fashion": 0.25,
    "home_appliances": 0.25,
    "accessories": 0.15,
}

BRANDS_BY_CATEGORY = {
    "electronics": ("SoundPeak", "TechNova", "PixelEdge", "Ampere"),
    "fashion": ("UrbanWeave", "LoomLane", "StitchCraft", "NovaWear"),
    "home_appliances": ("HomeHive", "CoolBreeze", "ChefMate", "PureFlow"),
    "accessories": ("CarryAll", "FlexFit", "DailyGear", "SnapCase"),
}

# Electronics return window used for deterministic policy checks (days).
ELECTRONICS_RETURN_WINDOW_DAYS = 30
