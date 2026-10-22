"""Load, validate and clean the synthetic e-commerce sales dataset.

Only the Python standard library is used.

Cleaning rules (also written to data/processed/cleaning_report.csv):

* Exact duplicate records (all 12 columns identical) are removed, keeping the
  first occurrence. This is safe because the generator simulates double
  submissions. Rows that merely share an ``order_id`` but differ in any other
  field are retained, because they may be legitimate separate line items.
* A blank ``discount`` is filled with ``0`` (0%). This is the conservative
  rule: if no discount was recorded, no discount is assumed. The revenue
  formula is ``quantity * unit_price * (1 - discount / 100)``.
* A blank ``city`` is filled with ``Unknown``. Blank product, category,
  payment method or customer values are also filled with ``Unknown``; these
  rows are still useful for revenue totals.
* Blank ``coupon_code`` and ``customer_rating`` values are optional and are
  retained as blanks.
* Rows missing a critical field (order_id, order_date, quantity or
  unit_price) cannot be used safely and are removed.
* Rows with an unparseable date, a non-positive/non-integer quantity, a
  non-positive price, or a discount outside 0-100 are removed. Each removed
  row is counted once, under the first failed check, so the removal counts
  add up to the number of rows removed.

Run:
    python3 -m src.data_cleaning
    python3 main.py clean
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "sales_data.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEANED_PATH = PROCESSED_DIR / "cleaned_sales_data.csv"
REPORT_PATH = PROCESSED_DIR / "cleaning_report.csv"

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

REQUIRED_COLUMNS = FIELDNAMES[:10]
OPTIONAL_COLUMNS = FIELDNAMES[10:]

# These fields are needed to identify an order, place it in time and compute
# its revenue. Without them the row cannot be repaired safely.
CRITICAL_COLUMNS = ["order_id", "order_date", "quantity", "unit_price"]

# Descriptive fields can be replaced with "Unknown" without losing revenue.
DIMENSION_COLUMNS = ["product_name", "category", "payment_method", "city", "customer_id"]

UNKNOWN = "Unknown"
MAX_QUANTITY = 1000
MAX_UNIT_PRICE = 1_000_000.0

ISSUE_REPORT_FIELDS = ["issue", "rows_affected", "action", "explanation"]


@dataclass
class CleaningReport:
    """Counts describing what the cleaning stage detected and did."""

    input_rows: int = 0
    output_rows: int = 0
    rows_with_missing_values: int = 0
    exact_duplicates_removed: int = 0
    missing_critical_removed: int = 0
    invalid_dates_removed: int = 0
    invalid_quantities_removed: int = 0
    invalid_prices_removed: int = 0
    invalid_discounts_removed: int = 0
    missing_discount_filled: int = 0
    missing_city_filled: int = 0
    missing_dimensions_filled: int = 0
    missing_coupon_retained: int = 0
    missing_rating_retained: int = 0
    conflicting_order_ids_retained: int = 0

    @property
    def total_rows_removed(self) -> int:
        return self.input_rows - self.output_rows


def load_rows(path: Path) -> list[dict]:
    """Read a sales CSV and normalise it to the expected 12 columns.

    Extra columns are ignored, missing expected columns raise an error, and
    every value is stripped of surrounding whitespace.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Sales file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        missing = [column for column in FIELDNAMES if column not in header]
        if missing:
            raise ValueError(
                f"{path} is missing columns: {', '.join(missing)}"
            )

        return [
            {column: (row.get(column) or "").strip() for column in FIELDNAMES}
            for row in reader
        ]


def _row_key(row: dict) -> tuple:
    """Identity used for exact-duplicate detection (all columns)."""
    return tuple(row[column] for column in FIELDNAMES)


def _count_conflicting_order_ids(rows: list[dict]) -> int:
    """Count order IDs that have more than one distinct version."""
    details_by_order = defaultdict(set)
    for row in rows:
        if row["order_id"]:
            details = tuple(
                row[column] for column in FIELDNAMES if column != "order_id"
            )
            details_by_order[row["order_id"]].add(details)
    return sum(1 for details in details_by_order.values() if len(details) > 1)


def _parse_quantity(value: str) -> int:
    quantity = int(value)
    if quantity <= 0 or quantity > MAX_QUANTITY:
        raise ValueError("quantity must be between 1 and 1000")
    return quantity


def _parse_price(value: str) -> float:
    price = float(value)
    if not math.isfinite(price) or price <= 0 or price > MAX_UNIT_PRICE:
        raise ValueError("unit_price must be a positive finite number")
    return price


def _parse_discount(value: str) -> float:
    discount = float(value)
    if not math.isfinite(discount) or discount < 0 or discount > 100:
        raise ValueError("discount must be between 0 and 100")
    return discount


def _format_decimal(value: float) -> str:
    return f"{value:.2f}"


def clean_dataset(
    input_path: Path = RAW_PATH,
    output_path: Path = CLEANED_PATH,
    report_path: Path = REPORT_PATH,
) -> CleaningReport:
    """Clean ``input_path`` and write the cleaned CSV plus an issue report."""
    raw_rows = load_rows(input_path)
    report = CleaningReport(input_rows=len(raw_rows))

    # 1. Remove exact duplicate records, keeping the first occurrence.
    seen = set()
    deduplicated = []
    for row in raw_rows:
        key = _row_key(row)
        if key in seen:
            report.exact_duplicates_removed += 1
        else:
            seen.add(key)
            deduplicated.append(row)

    report.rows_with_missing_values = sum(
        1 for row in deduplicated if any(value == "" for value in row.values())
    )
    report.conflicting_order_ids_retained = _count_conflicting_order_ids(
        deduplicated
    )

    cleaned = []
    for row in deduplicated:
        # 2. Critical fields cannot be repaired safely.
        if any(row[column] == "" for column in CRITICAL_COLUMNS):
            report.missing_critical_removed += 1
            continue

        # 3. Validate the date.
        try:
            order_date = date.fromisoformat(row["order_date"])
        except ValueError:
            report.invalid_dates_removed += 1
            continue

        # 4. Validate quantity and price.
        try:
            quantity = _parse_quantity(row["quantity"])
        except (TypeError, ValueError):
            report.invalid_quantities_removed += 1
            continue

        try:
            unit_price = _parse_price(row["unit_price"])
        except (TypeError, ValueError):
            report.invalid_prices_removed += 1
            continue

        # 5. Missing discount -> 0%; invalid discount -> remove the row.
        if row["discount"] == "":
            discount = 0.0
            report.missing_discount_filled += 1
        else:
            try:
                discount = _parse_discount(row["discount"])
            except (TypeError, ValueError):
                report.invalid_discounts_removed += 1
                continue

        # 6. Fill missing descriptive fields rather than dropping sales.
        if row["city"] == "":
            row["city"] = UNKNOWN
            report.missing_city_filled += 1

        missing_other_dimension = False
        for column in DIMENSION_COLUMNS:
            if column == "city":
                continue
            if row[column] == "":
                row[column] = UNKNOWN
                missing_other_dimension = True
        if missing_other_dimension:
            report.missing_dimensions_filled += 1

        # 7. Optional blanks are retained.
        if row["coupon_code"] == "":
            report.missing_coupon_retained += 1
        if row["customer_rating"] == "":
            report.missing_rating_retained += 1

        cleaned.append(
            {
                "order_id": row["order_id"],
                "order_date": order_date.isoformat(),
                "product_name": row["product_name"],
                "category": row["category"],
                "quantity": str(quantity),
                "unit_price": _format_decimal(unit_price),
                "discount": _format_decimal(discount),
                "payment_method": row["payment_method"],
                "city": row["city"],
                "customer_id": row["customer_id"],
                "coupon_code": row["coupon_code"],
                "customer_rating": row["customer_rating"],
            }
        )

    report.output_rows = len(cleaned)
    _write_cleaned_csv(cleaned, output_path)
    _write_issue_report(report, report_path)
    return report


def _write_cleaned_csv(rows: list[dict], output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_issue_rows(report: CleaningReport) -> list[dict]:
    """Return one row per detected issue, for cleaning_report.csv."""
    return [
        {
            "issue": "Exact duplicate records",
            "rows_affected": report.exact_duplicates_removed,
            "action": "Removed (first occurrence kept)",
            "explanation": (
                "All 12 columns were identical, so these were treated as "
                "duplicate submissions, not separate purchases."
            ),
        },
        {
            "issue": "Rows with any missing value",
            "rows_affected": report.rows_with_missing_values,
            "action": "Corrected or retained (see rows below)",
            "explanation": (
                "Missing values were handled per field. This includes blanks "
                "in optional fields such as coupon_code; a row can appear in "
                "more than one missing-value category."
            ),
        },
        {
            "issue": "Missing critical fields",
            "rows_affected": report.missing_critical_removed,
            "action": "Removed",
            "explanation": (
                "order_id, order_date, quantity or unit_price was blank; "
                "date, units and revenue cannot be computed reliably."
            ),
        },
        {
            "issue": "Invalid order_date",
            "rows_affected": report.invalid_dates_removed,
            "action": "Removed",
            "explanation": "Date did not parse as an ISO date (YYYY-MM-DD).",
        },
        {
            "issue": "Invalid quantity",
            "rows_affected": report.invalid_quantities_removed,
            "action": "Removed",
            "explanation": "Quantity was not a whole number between 1 and 1000.",
        },
        {
            "issue": "Invalid unit_price",
            "rows_affected": report.invalid_prices_removed,
            "action": "Removed",
            "explanation": "Price was not a positive finite number.",
        },
        {
            "issue": "Invalid discount",
            "rows_affected": report.invalid_discounts_removed,
            "action": "Removed",
            "explanation": "Discount was not numeric or was outside 0-100.",
        },
        {
            "issue": "Missing discount",
            "rows_affected": report.missing_discount_filled,
            "action": "Corrected to 0 (0%)",
            "explanation": (
                "Conservative rule: a blank discount means no discount was "
                "recorded, so no discount is applied to revenue."
            ),
        },
        {
            "issue": "Missing city",
            "rows_affected": report.missing_city_filled,
            "action": "Corrected to 'Unknown'",
            "explanation": (
                "The row is retained; revenue is still valid, and the city is "
                "reported as Unknown instead of being guessed."
            ),
        },
        {
            "issue": "Missing other descriptive fields",
            "rows_affected": report.missing_dimensions_filled,
            "action": "Corrected to 'Unknown'",
            "explanation": (
                "Blank product, category, payment method or customer values "
                "were filled with Unknown; the sale is retained."
            ),
        },
        {
            "issue": "Missing coupon_code",
            "rows_affected": report.missing_coupon_retained,
            "action": "Retained blank",
            "explanation": (
                "Optional field. Blank means the order had no coupon code."
            ),
        },
        {
            "issue": "Missing customer_rating",
            "rows_affected": report.missing_rating_retained,
            "action": "Retained blank",
            "explanation": (
                "Optional field. Blank means the customer did not rate the "
                "order."
            ),
        },
        {
            "issue": "Conflicting rows sharing an order_id",
            "rows_affected": report.conflicting_order_ids_retained,
            "action": "Retained",
            "explanation": (
                "Rows were not exact duplicates; they may be separate line "
                "items. The order is counted once in unique-order metrics."
            ),
        },
    ]


def _write_issue_report(report: CleaningReport, report_path: Path) -> None:
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ISSUE_REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(build_issue_rows(report))


def format_report(report: CleaningReport) -> str:
    """Human-readable summary of the cleaning run."""
    return "\n".join(
        [
            "Cleaning complete.",
            f"  Input rows:                 {report.input_rows}",
            f"  Exact duplicates removed:   {report.exact_duplicates_removed}",
            f"  Rows removed as invalid:    "
            f"{report.input_rows - report.exact_duplicates_removed - report.output_rows}",
            f"  Rows kept:                  {report.output_rows}",
            f"  Missing discounts -> 0%:    {report.missing_discount_filled}",
            f"  Missing cities -> Unknown:  {report.missing_city_filled}",
            f"  Missing coupon codes kept:  {report.missing_coupon_retained}",
            f"  Missing ratings kept:       {report.missing_rating_retained}",
        ]
    )


def run_cleaning(
    input_path: Path = RAW_PATH,
    output_path: Path = CLEANED_PATH,
    report_path: Path = REPORT_PATH,
    verbose: bool = True,
) -> CleaningReport:
    """Clean the dataset and optionally print a summary."""
    report = clean_dataset(input_path, output_path, report_path)
    if verbose:
        print(format_report(report))
        print(f"\n  Cleaned data:  {Path(output_path)}")
        print(f"  Issue report:  {Path(report_path)}")
    return report


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean the synthetic e-commerce sales dataset."
    )
    parser.add_argument("--input", type=Path, default=RAW_PATH)
    parser.add_argument("--output", type=Path, default=CLEANED_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_cleaning(args.input, args.output, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
