"""Generate a reproducible synthetic e-commerce sales dataset.

This script uses only the Python standard library. The data is entirely
fictional: customer IDs are sequential labels and no real personal
information is used.

Usage (from the project root):
    python3 data/generate_data.py
    python3 data/generate_data.py --rows 1500 --seed 42
    python3 data/generate_data.py --output data/raw/sales_data.csv

Conventions:
    * discount is a percentage between 0 and 100 (0 means no discount).
    * unit_price is in Indian rupees (INR).
    * blank coupon_code / customer_rating means "not recorded".
    * A small number of city and discount values are intentionally blank,
      and a few duplicate orders are intentionally included, so that data
      cleaning can be practised later.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import random
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "sales_data.csv"

DEFAULT_SEED = 42
DEFAULT_ROWS = 1500
DATASET_YEAR = 2025

FIELDNAMES = [
    "order_id",
    "order_date",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "payment_method",
    "city",
    "customer_id",
    "coupon_code",
    "customer_rating",
]

# The first ten columns are required by the project brief. The last two are
# optional extras that make missing-value cleaning more realistic.
REQUIRED_COLUMNS = FIELDNAMES[:10]

# Product catalogue: category -> [(product_name, min_price, max_price), ...]
PRODUCTS = {
    "Electronics": [
        ("Wireless Earbuds", 1499, 4999),
        ("Bluetooth Speaker", 999, 3999),
        ("Smartwatch", 1999, 8999),
        ("USB-C Fast Charger", 499, 1999),
        ("Power Bank 20000mAh", 999, 2499),
    ],
    "Fashion": [
        ("Cotton T-Shirt", 399, 999),
        ("Denim Jeans", 999, 2499),
        ("Running Shoes", 1499, 4999),
        ("Ethnic Kurta", 699, 1999),
        ("Leather Wallet", 499, 1499),
    ],
    "Home & Kitchen": [
        ("Stainless Steel Cookware Set", 1499, 5999),
        ("Ceramic Dinner Set", 999, 3499),
        ("Air Fryer", 2999, 8999),
        ("Cotton Bedsheet Set", 699, 1999),
        ("Storage Container Set", 399, 999),
    ],
    "Beauty & Personal Care": [
        ("Vitamin C Face Serum", 399, 1299),
        ("Herbal Shampoo", 199, 599),
        ("Sunscreen SPF 50", 299, 899),
        ("Body Lotion", 249, 699),
    ],
    "Books & Stationery": [
        ("Paperback Novel", 149, 599),
        ("Notebook Set", 199, 499),
        ("Fountain Pen", 299, 1499),
        ("Self-Help Book", 249, 699),
    ],
    "Sports & Fitness": [
        ("Yoga Mat", 499, 1499),
        ("Dumbbell Set", 999, 3999),
        ("Cricket Bat", 899, 4999),
        ("Resistance Bands", 299, 999),
    ],
    "Grocery & Gourmet": [
        ("Organic Honey", 249, 699),
        ("Arabica Coffee", 349, 899),
        ("Dry Fruits Gift Pack", 499, 1499),
        ("Green Tea", 199, 599),
    ],
    "Toys & Games": [
        ("Building Blocks", 499, 1999),
        ("Board Game", 599, 1999),
        ("Remote Control Car", 899, 2999),
    ],
}

CATEGORY_WEIGHTS = [22, 18, 15, 12, 9, 10, 8, 6]
PRODUCTS_LIST = list(PRODUCTS)
CATEGORY_WEIGHTS_LOOKUP = dict(zip(PRODUCTS_LIST, CATEGORY_WEIGHTS))

CITIES = [
    "Mumbai",
    "Delhi",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Pune",
    "Ahmedabad",
    "Jaipur",
    "Lucknow",
    "Surat",
    "Indore",
    "Chandigarh",
    "Kochi",
    "Guwahati",
]
CITY_WEIGHTS = [16, 15, 14, 10, 8, 8, 7, 5, 4, 4, 3, 2, 2, 2, 1]

PAYMENT_METHODS = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Net Banking",
    "Cash on Delivery",
    "Wallet",
]
PAYMENT_WEIGHTS = [40, 18, 12, 8, 15, 7]

MONTH_WEIGHTS = [6, 6, 7, 6, 7, 6, 7, 8, 9, 12, 13, 11]

REGULAR_DISCOUNTS = {
    0: 55,
    5: 12,
    10: 15,
    15: 8,
    20: 6,
    25: 2,
    30: 2,
}
FESTIVE_DISCOUNTS = {
    0: 35,
    5: 8,
    10: 15,
    15: 12,
    20: 12,
    25: 8,
    30: 6,
    40: 3,
    50: 1,
}

QUANTITY_WEIGHTS = {1: 55, 2: 22, 3: 12, 4: 7, 5: 4}

COUPONS = ["WELCOME10", "FESTIVE15", "SAVE20", "NEWUSER", "WEEKEND5"]

# Intentional data-quality issues (same seed => same rows affected).
MISSING_CITY_ROWS = 12
MISSING_DISCOUNT_ROWS = 15
MISSING_RATING_ROWS = 18
DUPLICATE_ROWS = 25

CUSTOMER_POOL_SIZE = 500


def _weighted_choice(rng: random.Random, values, weights):
    """Return one value using the given integer weights."""
    return rng.choices(values, weights=weights, k=1)[0]


def _random_order_date(rng: random.Random, year: int) -> date:
    """Pick a date in `year`, with more orders during the festive season."""
    month = _weighted_choice(rng, list(range(1, 13)), MONTH_WEIGHTS)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, rng.randint(1, last_day))


def _choose_unit_price(rng: random.Random, low: int, high: int) -> int:
    """Pick a realistic INR price ending in 9 (e.g. 1499, 2999)."""
    steps = range(low // 10, (high // 10) + 1)
    return rng.choice(list(steps)) * 10 - 1


def _choose_discount(rng: random.Random, month: int) -> int:
    """Choose a discount percentage between 0 and 100."""
    weights = FESTIVE_DISCOUNTS if month in (10, 11, 12) else REGULAR_DISCOUNTS
    return _weighted_choice(rng, list(weights), list(weights.values()))


def _choose_rating(rng: random.Random) -> str:
    """Ratings are mostly positive, as in a typical store."""
    return str(_weighted_choice(rng, [1, 2, 3, 4, 5], [3, 4, 12, 36, 45]))


def build_rows(rng: random.Random, n_rows: int) -> list[dict]:
    """Create clean synthetic rows before quality issues are injected."""
    customers = [f"CUST-{i:04d}" for i in range(1, CUSTOMER_POOL_SIZE + 1)]
    rows = []

    for index in range(1, n_rows + 1):
        order_date = _random_order_date(rng, DATASET_YEAR)
        category = _weighted_choice(rng, PRODUCTS_LIST, CATEGORY_WEIGHTS)
        product_name, low_price, high_price = rng.choice(PRODUCTS[category])
        quantity = _weighted_choice(
            rng,
            list(QUANTITY_WEIGHTS),
            list(QUANTITY_WEIGHTS.values()),
        )
        unit_price = _choose_unit_price(rng, low_price, high_price)
        discount = _choose_discount(rng, order_date.month)

        coupon = ""
        if discount > 0 and rng.random() < 0.60:
            coupon = rng.choice(COUPONS)

        rows.append(
            {
                "order_id": f"ORD-{DATASET_YEAR}-{index:05d}",
                "order_date": order_date.isoformat(),
                "product_name": product_name,
                "category": category,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount,
                "payment_method": _weighted_choice(
                    rng, PAYMENT_METHODS, PAYMENT_WEIGHTS
                ),
                "city": _weighted_choice(rng, CITIES, CITY_WEIGHTS),
                "customer_id": rng.choice(customers),
                "coupon_code": coupon,
                "customer_rating": _choose_rating(rng),
            }
        )

    return rows


def inject_quality_issues(rows: list[dict], rng: random.Random) -> None:
    """Add missing values and duplicate orders in place (reproducibly)."""
    for index in rng.sample(range(len(rows)), MISSING_CITY_ROWS):
        rows[index]["city"] = ""

    for index in rng.sample(range(len(rows)), MISSING_DISCOUNT_ROWS):
        rows[index]["discount"] = ""

    for index in rng.sample(range(len(rows)), MISSING_RATING_ROWS):
        rows[index]["customer_rating"] = ""

    duplicate_indexes = rng.sample(range(len(rows)), DUPLICATE_ROWS)
    duplicates = [dict(rows[index]) for index in duplicate_indexes]
    rows.extend(duplicates)
    rng.shuffle(rows)


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def validate_csv(output_path: Path, minimum_rows: int = 1000) -> dict:
    """Read the file back and verify its structure and contents."""
    if not output_path.exists():
        raise FileNotFoundError(f"Dataset was not created: {output_path}")

    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(
                f"Unexpected header: {reader.fieldnames}\nExpected: {FIELDNAMES}"
            )

        rows = list(reader)

    if len(rows) < minimum_rows:
        raise ValueError(
            f"Only {len(rows)} data rows found; expected at least {minimum_rows}."
        )

    missing_required = 0
    months = set()
    categories = set()
    duplicate_keys = Counter()

    for row in rows:
        for column in REQUIRED_COLUMNS:
            if row[column] == "" and column not in {"city", "discount"}:
                missing_required += 1

        try:
            parsed_date = date.fromisoformat(row["order_date"])
        except ValueError as exc:
            raise ValueError(f"Invalid order_date: {row['order_date']!r}") from exc

        months.add(parsed_date.strftime("%Y-%m"))
        categories.add(row["category"])

        discount = row["discount"]
        if discount != "":
            discount_value = float(discount)
            if not 0 <= discount_value <= 100:
                raise ValueError(f"Discount out of range: {discount!r}")

        if float(row["unit_price"]) <= 0 or int(row["quantity"]) <= 0:
            raise ValueError(f"Invalid price/quantity in order {row['order_id']}")

        duplicate_keys[tuple(row[column] for column in FIELDNAMES)] += 1

    if missing_required:
        raise ValueError(f"{missing_required} required values are missing.")

    if len(months) != 12:
        raise ValueError(f"Expected 12 distinct months, found {len(months)}.")

    return {
        "rows": len(rows),
        "months": len(months),
        "categories": len(categories),
        "duplicates": sum(count - 1 for count in duplicate_keys.values() if count > 1),
        "missing_city": sum(1 for row in rows if row["city"] == ""),
        "missing_discount": sum(1 for row in rows if row["discount"] == ""),
        "missing_rating": sum(1 for row in rows if row["customer_rating"] == ""),
    }


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible synthetic e-commerce sales CSV."
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_ROWS,
        help=f"Number of clean orders before duplicates (default: {DEFAULT_ROWS}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output CSV path (default: data/raw/sales_data.csv).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.rows < 1000:
        raise SystemExit("--rows must be at least 1000 (project requirement).")

    rng = random.Random(args.seed)
    rows = build_rows(rng, args.rows)
    inject_quality_issues(rows, rng)

    output_path = args.output
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    write_csv(rows, output_path)
    summary = validate_csv(output_path)

    print("Synthetic dataset created successfully.")
    print(f"  File:            {output_path}")
    print(f"  Total rows:      {summary['rows']}")
    print(f"  Months covered:  {summary['months']}")
    print(f"  Categories:      {summary['categories']}")
    print(f"  Duplicate rows:  {summary['duplicates']} (intentional)")
    print(f"  Missing city:    {summary['missing_city']} (intentional)")
    print(f"  Missing discount:{summary['missing_discount']} (intentional)")
    print(f"  Missing rating:  {summary['missing_rating']} (intentional)")
    print(f"  Seed:            {args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
