"""Export synthetic structured data to data/structured/ CSV files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"
PROJECT_ROOT = BACKEND_ROOT.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "structured"


def main() -> int:
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))

    from app.synthetic.generator import generate_synthetic_data
    from app.synthetic.ground_truth import write_ground_truth_files

    bundle = generate_synthetic_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "customers": bundle.customers,
        "suppliers": bundle.suppliers,
        "products": bundle.products,
        "orders": bundle.orders,
        "order_items": bundle.order_items,
        "product_units": bundle.product_units,
        "deliveries": bundle.deliveries,
        "returns": bundle.returns,
        "inspections": bundle.inspections,
        "refunds": bundle.refunds,
        "investigation_cases": bundle.investigation_cases,
        "recovery_options": bundle.recovery_options,
        "recovery_tasks": bundle.recovery_tasks,
    }

    for name, rows in datasets.items():
        frame = pd.DataFrame(rows)
        frame.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    write_ground_truth_files()
    print(f"Exported {len(datasets)} tables to {OUTPUT_DIR}")
    print(f"Ground truth written to {PROJECT_ROOT / 'data' / 'ground_truth'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
