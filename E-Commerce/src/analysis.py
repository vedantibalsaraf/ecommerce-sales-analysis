"""Analyse the cleaned e-commerce dataset using only the standard library.

Revenue rule:
    net revenue = quantity * unit_price * (1 - discount / 100)

A blank discount is treated as 0% (the same rule used by the cleaning stage).
Discounts are percentages from 0 to 100, never fractions.

Duplicate records are removed by ``src.data_cleaning`` before this module runs.
The analysis therefore works from data/processed/cleaned_sales_data.csv.
Unique orders are counted as distinct ``order_id`` values, so several rows
belonging to one order count once for order-based metrics but all their
revenue is included.

Run:
    python3 -m src.analysis
    python3 main.py analyse
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):  # allow: python3 src/analysis.py
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaning import (  # noqa: E402
    CLEANED_PATH,
    PROCESSED_DIR,
    load_rows,
)

DEFAULT_TOP_N = 10

TABLE_COLUMNS = {
    "overall_metrics": ["metric", "value"],
    "revenue_by_category": [
        "category",
        "orders",
        "units_sold",
        "net_revenue_inr",
        "revenue_share_pct",
    ],
    "revenue_by_product": [
        "product_name",
        "category",
        "orders",
        "units_sold",
        "net_revenue_inr",
        "revenue_share_pct",
    ],
    "revenue_by_city": [
        "city",
        "orders",
        "units_sold",
        "net_revenue_inr",
        "revenue_share_pct",
    ],
    "top_products_by_quantity": [
        "rank",
        "product_name",
        "category",
        "units_sold",
        "net_revenue_inr",
    ],
    "top_products_by_revenue": [
        "rank",
        "product_name",
        "category",
        "net_revenue_inr",
        "units_sold",
    ],
    "monthly_revenue": [
        "month",
        "orders",
        "units_sold",
        "net_revenue_inr",
        "mom_change_inr",
        "mom_change_pct",
    ],
    "payment_method_distribution": [
        "payment_method",
        "orders",
        "units_sold",
        "net_revenue_inr",
        "revenue_share_pct",
        "order_share_pct",
    ],
}


@dataclass
class AnalysisResult:
    """Key metrics plus all summary tables, ready to write as CSV."""

    metrics: dict
    tables: dict


def calculate_net_revenue(quantity, unit_price, discount) -> float:
    """Return revenue after discount for one line item.

    ``discount`` is a percentage (0-100). A blank/None discount means 0%.
    Invalid values raise ``ValueError`` instead of producing silent nonsense.
    """
    try:
        quantity_value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid quantity: {quantity!r}") from exc

    try:
        price_value = float(unit_price)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid unit_price: {unit_price!r}") from exc

    if quantity_value <= 0:
        raise ValueError(f"Quantity must be positive, got {quantity!r}")
    if not (price_value > 0) or price_value != price_value or price_value == float("inf"):
        raise ValueError(f"unit_price must be positive and finite, got {unit_price!r}")

    if discount is None or str(discount).strip() == "":
        discount_value = 0.0
    else:
        try:
            discount_value = float(discount)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid discount: {discount!r}") from exc

    if not (0 <= discount_value <= 100) or discount_value != discount_value:
        raise ValueError(f"Discount must be between 0 and 100, got {discount!r}")

    return quantity_value * price_value * (1 - discount_value / 100)


def _empty_group() -> dict:
    return {"revenue": 0.0, "units": 0, "orders": set()}


def _product_entry() -> dict:
    return {"revenue": 0.0, "units": 0, "orders": set(), "categories": set()}


def _share(part: float, whole: float) -> float:
    return round((part / whole) * 100, 2) if whole else 0.0


def analyse_rows(rows: list[dict], top_n: int = DEFAULT_TOP_N) -> AnalysisResult:
    """Calculate all Part 2 metrics from cleaned rows."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    categories = defaultdict(_empty_group)
    products = defaultdict(_product_entry)
    cities = defaultdict(_empty_group)
    payments = defaultdict(_empty_group)
    monthly = defaultdict(_empty_group)

    orders = set()
    months = set()
    total_revenue = 0.0
    gross_revenue = 0.0
    total_units = 0
    dates = []

    for row in rows:
        order_id = row["order_id"].strip()
        if not order_id:
            raise ValueError("Found a row without an order_id; clean the data first.")

        try:
            order_date = date.fromisoformat(row["order_date"])
        except ValueError as exc:
            raise ValueError(
                f"Invalid order_date for {order_id}: {row['order_date']!r}"
            ) from exc

        try:
            quantity = int(row["quantity"])
            revenue = calculate_net_revenue(
                quantity, row["unit_price"], row["discount"]
            )
        except ValueError as exc:
            raise ValueError(f"Invalid row for {order_id}: {exc}") from exc

        unit_price = float(row["unit_price"])
        gross_revenue += quantity * unit_price
        total_revenue += revenue
        total_units += quantity

        month = order_date.strftime("%Y-%m")
        category = row["category"] or "Unknown"
        product = row["product_name"] or "Unknown"
        city = row["city"] or "Unknown"
        payment = row["payment_method"] or "Unknown"

        orders.add(order_id)
        months.add(month)
        dates.append(order_date)

        for group in (
            categories[category],
            cities[city],
            payments[payment],
            monthly[month],
        ):
            group["revenue"] += revenue
            group["units"] += quantity
            group["orders"].add(order_id)

        product_group = products[product]
        product_group["revenue"] += revenue
        product_group["units"] += quantity
        product_group["orders"].add(order_id)
        product_group["categories"].add(category)

    unique_orders = len(orders)
    average_order_value = (
        round(total_revenue / unique_orders, 2) if unique_orders else 0.0
    )

    category_rows = [
        {
            "category": name,
            "orders": len(data["orders"]),
            "units_sold": data["units"],
            "net_revenue_inr": round(data["revenue"], 2),
            "revenue_share_pct": _share(data["revenue"], total_revenue),
        }
        for name, data in categories.items()
    ]
    category_rows.sort(key=lambda row: (-row["net_revenue_inr"], row["category"]))

    city_rows = [
        {
            "city": name,
            "orders": len(data["orders"]),
            "units_sold": data["units"],
            "net_revenue_inr": round(data["revenue"], 2),
            "revenue_share_pct": _share(data["revenue"], total_revenue),
        }
        for name, data in cities.items()
    ]
    city_rows.sort(key=lambda row: (-row["net_revenue_inr"], row["city"]))

    product_rows = [
        {
            "product_name": name,
            "category": ", ".join(sorted(data["categories"])),
            "orders": len(data["orders"]),
            "units_sold": data["units"],
            "net_revenue_inr": round(data["revenue"], 2),
            "revenue_share_pct": _share(data["revenue"], total_revenue),
        }
        for name, data in products.items()
    ]
    product_rows.sort(key=lambda row: (-row["net_revenue_inr"], row["product_name"]))

    top_by_quantity = sorted(
        product_rows,
        key=lambda row: (-row["units_sold"], -row["net_revenue_inr"], row["product_name"]),
    )[:top_n]
    top_by_quantity = [
        {
            "rank": rank,
            "product_name": row["product_name"],
            "category": row["category"],
            "units_sold": row["units_sold"],
            "net_revenue_inr": row["net_revenue_inr"],
        }
        for rank, row in enumerate(top_by_quantity, start=1)
    ]

    top_by_revenue = product_rows[:top_n]
    top_by_revenue = [
        {
            "rank": rank,
            "product_name": row["product_name"],
            "category": row["category"],
            "net_revenue_inr": row["net_revenue_inr"],
            "units_sold": row["units_sold"],
        }
        for rank, row in enumerate(top_by_revenue, start=1)
    ]

    monthly_rows = []
    previous_revenue = None
    for month in sorted(monthly):
        data = monthly[month]
        revenue = round(data["revenue"], 2)
        change = ""
        change_pct = ""
        if previous_revenue is not None:
            change = round(revenue - previous_revenue, 2)
            change_pct = (
                round((revenue - previous_revenue) / previous_revenue * 100, 2)
                if previous_revenue
                else ""
            )
        monthly_rows.append(
            {
                "month": month,
                "orders": len(data["orders"]),
                "units_sold": data["units"],
                "net_revenue_inr": revenue,
                "mom_change_inr": change,
                "mom_change_pct": change_pct,
            }
        )
        previous_revenue = revenue

    payment_rows = [
        {
            "payment_method": name,
            "orders": len(data["orders"]),
            "units_sold": data["units"],
            "net_revenue_inr": round(data["revenue"], 2),
            "revenue_share_pct": _share(data["revenue"], total_revenue),
            "order_share_pct": _share(len(data["orders"]), unique_orders),
        }
        for name, data in payments.items()
    ]
    payment_rows.sort(
        key=lambda row: (-row["net_revenue_inr"], row["payment_method"])
    )

    metrics = {
        "total_net_revenue_inr": round(total_revenue, 2),
        "gross_revenue_inr": round(gross_revenue, 2),
        "total_discount_amount_inr": round(gross_revenue - total_revenue, 2),
        "unique_orders": unique_orders,
        "total_units_sold": total_units,
        "average_order_value_inr": average_order_value,
        "cleaned_line_items": len(rows),
        "date_range_start": min(dates).isoformat() if dates else "",
        "date_range_end": max(dates).isoformat() if dates else "",
        "months_covered": len(months),
    }

    tables = {
        "overall_metrics": [
            {"metric": metric, "value": value} for metric, value in metrics.items()
        ],
        "revenue_by_category": category_rows,
        "revenue_by_product": product_rows,
        "revenue_by_city": city_rows,
        "top_products_by_quantity": top_by_quantity,
        "top_products_by_revenue": top_by_revenue,
        "monthly_revenue": monthly_rows,
        "payment_method_distribution": payment_rows,
    }
    return AnalysisResult(metrics=metrics, tables=tables)


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    if value is None:
        return ""
    return str(value)


def write_analysis_tables(
    result: AnalysisResult, output_dir: Path = PROCESSED_DIR
) -> list[Path]:
    """Write every summary table as a CSV in ``output_dir``."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for name, columns in TABLE_COLUMNS.items():
        path = output_dir / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in result.tables.get(name, []):
                writer.writerow(
                    {column: _format_value(row.get(column, "")) for column in columns}
                )
        written.append(path)

    return written


def run_analysis(
    input_path: Path = CLEANED_PATH,
    output_dir: Path = PROCESSED_DIR,
    top_n: int = DEFAULT_TOP_N,
    verbose: bool = True,
) -> AnalysisResult:
    """Load cleaned data, analyse it, and write all summary CSVs."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {input_path}\n"
            "Run: python3 main.py clean"
        )

    rows = load_rows(input_path)
    result = analyse_rows(rows, top_n=top_n)
    written = write_analysis_tables(result, output_dir)

    if verbose:
        metrics = result.metrics
        print("Analysis complete.")
        print(f"  Input:                 {input_path}")
        print(f"  Cleaned line items:    {metrics['cleaned_line_items']}")
        print(f"  Unique orders:         {metrics['unique_orders']}")
        print(f"  Total units sold:      {metrics['total_units_sold']}")
        print(f"  Total net revenue:     INR {metrics['total_net_revenue_inr']:.2f}")
        print(f"  Average order value:   INR {metrics['average_order_value_inr']:.2f}")
        print(f"  Months covered:        {metrics['months_covered']}")
        print(f"  Summary tables:        {len(written)} CSV files in {output_dir}")

    return result


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse the cleaned e-commerce sales data."
    )
    parser.add_argument("--input", type=Path, default=CLEANED_PATH)
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_analysis(args.input, args.output_dir, args.top_n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
