"""Tests for loading, validating and cleaning the sales data."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaning import (  # noqa: E402
    FIELDNAMES,
    RAW_PATH,
    clean_dataset,
)


def make_row(**overrides):
    """A valid row that individual tests can adjust."""
    row = {
        "order_id": "ORD-1",
        "order_date": "2025-01-05",
        "product_name": "Widget",
        "category": "Electronics",
        "quantity": "2",
        "unit_price": "100",
        "discount": "10",
        "payment_method": "UPI",
        "city": "Mumbai",
        "customer_id": "CUST-0001",
        "coupon_code": "",
        "customer_rating": "5",
    }
    row.update(overrides)
    return row


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.folder = Path(self.temp_dir.name)
        self.input_path = self.folder / "raw.csv"
        self.output_path = self.folder / "cleaned.csv"
        self.report_path = self.folder / "report.csv"

    def run_cleaner(self, rows):
        write_rows(self.input_path, rows)
        return clean_dataset(self.input_path, self.output_path, self.report_path)

    def read_cleaned(self):
        with self.output_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_duplicates_missing_values_and_invalid_rows(self):
        valid = make_row()
        rows = [
            valid,
            dict(valid),  # exact duplicate
            make_row(
                order_id="ORD-2",
                order_date="2025-01-10",
                product_name="Gadget",
                quantity="1",
                unit_price="50",
                discount="",
                city="",
                customer_rating="",
            ),
            make_row(order_id="ORD-3", order_date="2025-13-01"),  # bad date
            make_row(order_id="ORD-4", quantity="0"),  # bad quantity
            make_row(order_id="ORD-5", unit_price="-10"),  # bad price
            make_row(order_id="ORD-6", discount="150"),  # bad discount
            make_row(
                order_id="ORD-1",
                order_date="2025-02-01",
                quantity="1",
                discount="0",
            ),  # same order_id, different details
            make_row(
                order_id="ORD-7",
                product_name="",
                category="",
                quantity="1",
                unit_price="10",
                discount="0",
                payment_method="",
                city="",
                customer_id="",
                customer_rating="",
            ),
        ]

        report = self.run_cleaner(rows)

        self.assertEqual(report.input_rows, 9)
        self.assertEqual(report.exact_duplicates_removed, 1)
        self.assertEqual(report.invalid_dates_removed, 1)
        self.assertEqual(report.invalid_quantities_removed, 1)
        self.assertEqual(report.invalid_prices_removed, 1)
        self.assertEqual(report.invalid_discounts_removed, 1)
        self.assertEqual(report.missing_discount_filled, 1)
        self.assertEqual(report.missing_city_filled, 2)
        self.assertEqual(report.missing_dimensions_filled, 1)
        self.assertEqual(report.conflicting_order_ids_retained, 1)
        self.assertEqual(report.output_rows, 4)
        self.assertEqual(report.total_rows_removed, 5)

        cleaned = self.read_cleaned()
        self.assertEqual(len(cleaned), 4)
        self.assertEqual(
            {row["order_id"] for row in cleaned}, {"ORD-1", "ORD-2", "ORD-7"}
        )
        self.assertEqual(len({row["order_id"] for row in cleaned}), 3)

        invalid_ids = {"ORD-3", "ORD-4", "ORD-5", "ORD-6"}
        self.assertTrue(invalid_ids.isdisjoint({row["order_id"] for row in cleaned}))

        blank_discount_row = next(
            row for row in cleaned if row["order_id"] == "ORD-2"
        )
        self.assertEqual(blank_discount_row["discount"], "0.00")
        self.assertEqual(blank_discount_row["city"], "Unknown")

        unknown_row = next(row for row in cleaned if row["order_id"] == "ORD-7")
        self.assertEqual(unknown_row["payment_method"], "Unknown")
        self.assertEqual(unknown_row["category"], "Unknown")
        self.assertEqual(unknown_row["product_name"], "Unknown")
        self.assertEqual(unknown_row["city"], "Unknown")

        with self.report_path.open(newline="", encoding="utf-8") as handle:
            issues = list(csv.DictReader(handle))
        duplicate_issue = next(
            row for row in issues if row["issue"] == "Exact duplicate records"
        )
        self.assertEqual(duplicate_issue["rows_affected"], "1")

    def test_cleaned_file_has_expected_header(self):
        self.run_cleaner([make_row()])
        with self.output_path.open(newline="", encoding="utf-8") as handle:
            self.assertEqual(csv.DictReader(handle).fieldnames, FIELDNAMES)

    def test_real_raw_dataset_is_deduplicated(self):
        if not RAW_PATH.exists():
            self.skipTest("raw dataset missing")

        report = clean_dataset(RAW_PATH, self.output_path, self.report_path)
        cleaned = self.read_cleaned()

        self.assertEqual(report.input_rows, 1525)
        self.assertEqual(report.exact_duplicates_removed, 25)
        self.assertEqual(report.output_rows, 1500)
        self.assertEqual(len(cleaned), 1500)
        self.assertEqual(len({row["order_id"] for row in cleaned}), 1500)
        self.assertTrue(all(row["discount"] != "" for row in cleaned))
        self.assertTrue(all(row["city"] != "" for row in cleaned))


if __name__ == "__main__":
    unittest.main()
