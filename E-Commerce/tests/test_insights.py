"""Tests for the data-driven business insights report."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import analyse_rows  # noqa: E402
from src.data_cleaning import CLEANED_PATH, load_rows  # noqa: E402
from src.insights import (  # noqa: E402
    INSIGHTS_PATH,
    build_insights,
    write_insights,
)
from src.visualization import format_inr  # noqa: E402


def sale(order_id, date, product, category, quantity, price, discount, city):
    return {
        "order_id": order_id,
        "order_date": date,
        "product_name": product,
        "category": category,
        "quantity": quantity,
        "unit_price": price,
        "discount": discount,
        "payment_method": "UPI",
        "city": city,
        "customer_id": "CUST-0001",
        "coupon_code": "",
        "customer_rating": "",
    }


def sample_rows():
    return [
        sale("ORD-1", "2025-01-05", "Widget", "Electronics", "2", "100", "10", "Mumbai"),
        sale("ORD-1", "2025-01-05", "Gadget", "Fashion", "1", "50", "0", "Mumbai"),
        sale("ORD-2", "2025-02-10", "Widget", "Electronics", "1", "200", "", "Delhi"),
        sale("ORD-3", "2025-02-15", "Gadget", "Fashion", "3", "50", "50", "Mumbai"),
    ]


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.result = analyse_rows(sample_rows())
        self.text = build_insights(self.result)

    def test_report_has_at_least_five_findings(self):
        self.assertGreaterEqual(self.text.count("What the data shows:"), 5)
        self.assertIn("FINDINGS", self.text)
        self.assertIn("RECOMMENDATIONS AT A GLANCE", self.text)

    def test_report_states_data_is_synthetic(self):
        self.assertIn("SYNTHETIC", self.text)
        self.assertIn("synthetic data", self.text.lower())
        self.assertIn("do not establish causation", self.text)

    def test_report_uses_actual_metrics(self):
        total = format_inr(self.result.metrics["total_net_revenue_inr"])
        self.assertIn(total, self.text)
        self.assertIn("Electronics", self.text)
        self.assertIn("February 2025", self.text)
        self.assertIn("Widget", self.text)
        self.assertIn("Mumbai", self.text)
        self.assertIn(
            format_inr(self.result.metrics["average_order_value_inr"]), self.text
        )

    def test_report_includes_month_over_month_change(self):
        self.assertIn("month-over-month", self.text)
        self.assertIn("largest rise", self.text)
        self.assertIn("largest fall", self.text)

    def test_empty_dataset_report_is_safe(self):
        text = build_insights(analyse_rows([]))
        self.assertIn("No usable sales records", text)
        self.assertIn("SYNTHETIC", text)

    def test_report_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_insights(self.result, Path(folder) / "insights.txt")
            self.assertTrue(path.is_file())
            written = path.read_text(encoding="utf-8")
            self.assertEqual(written, self.text)

    def test_real_report_matches_actual_analysis(self):
        if not CLEANED_PATH.exists():
            self.skipTest("cleaned dataset missing; run python3 main.py all")

        result = analyse_rows(load_rows(CLEANED_PATH))
        text = build_insights(result)
        self.assertIn(format_inr(result.metrics["total_net_revenue_inr"]), text)
        top_category = result.tables["revenue_by_category"][0]["category"]
        top_product = result.tables["revenue_by_product"][0]["product_name"]
        self.assertIn(top_category, text)
        self.assertIn(top_product, text)
        self.assertGreaterEqual(text.count("What the data shows:"), 5)


class GeneratedReportTests(unittest.TestCase):
    def test_generated_report_exists(self):
        if not INSIGHTS_PATH.exists():
            self.skipTest("report not generated yet; run python3 main.py visualise")
        text = INSIGHTS_PATH.read_text(encoding="utf-8")
        self.assertGreater(len(text), 2000)
        self.assertIn("BUSINESS INSIGHTS REPORT", text)
        self.assertIn("SYNTHETIC", text)
        self.assertGreaterEqual(text.count("What the data shows:"), 5)


if __name__ == "__main__":
    unittest.main()
