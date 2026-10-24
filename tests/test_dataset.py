"""Standard-library tests for the synthetic dataset.

Run from the project root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import csv
import re
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.generate_data import (  # noqa: E402
    FIELDNAMES,
    REQUIRED_COLUMNS,
    build_rows,
)
import random  # noqa: E402

DATA_FILE = PROJECT_ROOT / "data" / "raw" / "sales_data.csv"


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATA_FILE.exists():
            raise unittest.SkipTest(
                "Dataset missing. Run: python3 data/generate_data.py"
            )
        with DATA_FILE.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            cls.header = reader.fieldnames
            cls.rows = list(reader)

    def test_file_exists(self):
        self.assertTrue(DATA_FILE.is_file(), f"Missing file: {DATA_FILE}")

    def test_header_is_exact(self):
        self.assertEqual(self.header, FIELDNAMES)

    def test_required_columns_present(self):
        for column in REQUIRED_COLUMNS:
            self.assertIn(column, self.header)

    def test_at_least_1000_rows(self):
        self.assertGreaterEqual(len(self.rows), 1000)

    def test_dates_cover_12_months(self):
        months = set()
        for row in self.rows:
            parsed = date.fromisoformat(row["order_date"])
            months.add((parsed.year, parsed.month))
        self.assertEqual(len(months), 12)

    def test_required_values_are_filled(self):
        for row in self.rows:
            for column in REQUIRED_COLUMNS:
                # city and discount intentionally contain a few blanks.
                if column in {"city", "discount"}:
                    continue
                self.assertNotEqual(row[column], "", f"Blank {column}: {row}")

    def test_discount_is_percentage(self):
        for row in self.rows:
            if row["discount"] == "":
                continue
            value = float(row["discount"])
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_prices_and_quantities_are_positive(self):
        for row in self.rows:
            self.assertGreater(float(row["unit_price"]), 0)
            self.assertGreater(int(row["quantity"]), 0)

    def test_customer_ids_are_synthetic(self):
        pattern = re.compile(r"^CUST-\d{4}$")
        for row in self.rows:
            self.assertRegex(row["customer_id"], pattern)

    def test_duplicates_exist_for_cleaning_practice(self):
        keys = Counter(tuple(row[column] for column in FIELDNAMES) for row in self.rows)
        duplicates = sum(count - 1 for count in keys.values() if count > 1)
        self.assertGreater(duplicates, 0)

    def test_missing_values_exist_for_cleaning_practice(self):
        self.assertTrue(any(row["city"] == "" for row in self.rows))
        self.assertTrue(any(row["discount"] == "" for row in self.rows))

    def test_variety_of_categories_cities_and_payments(self):
        self.assertGreaterEqual(len({row["category"] for row in self.rows}), 5)
        self.assertGreaterEqual(len({row["city"] for row in self.rows}), 5)
        self.assertGreaterEqual(
            len({row["payment_method"] for row in self.rows}), 3
        )

    def test_generation_is_reproducible(self):
        first = build_rows(random.Random(7), 50)
        second = build_rows(random.Random(7), 50)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
