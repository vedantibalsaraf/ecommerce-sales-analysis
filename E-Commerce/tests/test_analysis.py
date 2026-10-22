"""Tests for revenue, aggregation and average-order-value calculations."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (  # noqa: E402
    TABLE_COLUMNS,
    analyse_rows,
    calculate_net_revenue,
    write_analysis_tables,
)
from src.data_cleaning import CLEANED_PATH, load_rows  # noqa: E402


def sale(
    order_id,
    order_date,
    product,
    category,
    quantity,
    price,
    discount,
    payment,
    city,
):
    return {
        "order_id": order_id,
        "order_date": order_date,
        "product_name": product,
        "category": category,
        "quantity": quantity,
        "unit_price": price,
        "discount": discount,
        "payment_method": payment,
        "city": city,
        "customer_id": "CUST-0001",
        "coupon_code": "",
        "customer_rating": "",
    }


def sample_rows():
    return [
        sale("ORD-1", "2025-01-05", "Widget", "Electronics", "2", "100", "10", "UPI", "Mumbai"),
        sale("ORD-1", "2025-01-05", "Gadget", "Fashion", "1", "50", "0", "UPI", "Mumbai"),
        sale("ORD-2", "2025-02-10", "Widget", "Electronics", "1", "200", "", "Credit Card", "Delhi"),
        sale("ORD-3", "2025-02-15", "Gadget", "Fashion", "3", "50", "50", "UPI", "Mumbai"),
    ]


class RevenueTests(unittest.TestCase):
    def test_revenue_formula_with_discount(self):
        self.assertAlmostEqual(calculate_net_revenue(2, 100, 10), 180.0)
        self.assertAlmostEqual(calculate_net_revenue("3", "99.50", "25"), 223.875)

    def test_blank_discount_means_zero_percent(self):
        self.assertAlmostEqual(calculate_net_revenue(1, 200, ""), 200.0)
        self.assertAlmostEqual(calculate_net_revenue(1, 200, None), 200.0)

    def test_hundred_percent_discount_gives_zero(self):
        self.assertAlmostEqual(calculate_net_revenue(2, 100, 100), 0.0)

    def test_invalid_values_raise(self):
        for quantity, price, discount in [
            ("0", "100", "0"),
            ("2", "0", "0"),
            ("2", "-10", "0"),
            ("2", "100", "-1"),
            ("2", "100", "101"),
            ("2", "100", "not-a-number"),
            ("two", "100", "0"),
        ]:
            with self.subTest(quantity=quantity, price=price, discount=discount):
                with self.assertRaises(ValueError):
                    calculate_net_revenue(quantity, price, discount)


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.result = analyse_rows(sample_rows())

    def test_overall_metrics_and_aov(self):
        metrics = self.result.metrics
        self.assertAlmostEqual(metrics["total_net_revenue_inr"], 505.0)
        self.assertEqual(metrics["unique_orders"], 3)
        self.assertEqual(metrics["total_units_sold"], 7)
        self.assertEqual(metrics["cleaned_line_items"], 4)
        self.assertAlmostEqual(metrics["average_order_value_inr"], 168.33)
        self.assertAlmostEqual(
            metrics["average_order_value_inr"],
            round(metrics["total_net_revenue_inr"] / metrics["unique_orders"], 2),
        )

    def test_revenue_by_category(self):
        rows = {
            row["category"]: row
            for row in self.result.tables["revenue_by_category"]
        }
        self.assertAlmostEqual(rows["Electronics"]["net_revenue_inr"], 380.0)
        self.assertAlmostEqual(rows["Fashion"]["net_revenue_inr"], 125.0)
        self.assertEqual(rows["Electronics"]["orders"], 2)
        self.assertAlmostEqual(rows["Electronics"]["revenue_share_pct"], 75.25)

    def test_revenue_by_product_and_city(self):
        products = {
            row["product_name"]: row
            for row in self.result.tables["revenue_by_product"]
        }
        self.assertAlmostEqual(products["Widget"]["net_revenue_inr"], 380.0)
        self.assertAlmostEqual(products["Gadget"]["net_revenue_inr"], 125.0)

        cities = {
            row["city"]: row for row in self.result.tables["revenue_by_city"]
        }
        self.assertAlmostEqual(cities["Mumbai"]["net_revenue_inr"], 305.0)
        self.assertAlmostEqual(cities["Delhi"]["net_revenue_inr"], 200.0)

    def test_top_products_by_quantity_and_revenue(self):
        by_quantity = self.result.tables["top_products_by_quantity"]
        self.assertEqual(by_quantity[0]["product_name"], "Gadget")
        self.assertEqual(by_quantity[0]["units_sold"], 4)

        by_revenue = self.result.tables["top_products_by_revenue"]
        self.assertEqual(by_revenue[0]["product_name"], "Widget")
        self.assertAlmostEqual(by_revenue[0]["net_revenue_inr"], 380.0)

    def test_monthly_revenue_orders_and_growth(self):
        monthly = self.result.tables["monthly_revenue"]
        self.assertEqual([row["month"] for row in monthly], ["2025-01", "2025-02"])
        self.assertAlmostEqual(monthly[0]["net_revenue_inr"], 230.0)
        self.assertEqual(monthly[0]["orders"], 1)
        self.assertAlmostEqual(monthly[1]["net_revenue_inr"], 275.0)
        self.assertEqual(monthly[1]["orders"], 2)
        self.assertEqual(monthly[0]["mom_change_inr"], "")
        self.assertAlmostEqual(monthly[1]["mom_change_inr"], 45.0)
        self.assertAlmostEqual(monthly[1]["mom_change_pct"], 19.57)
        self.assertAlmostEqual(
            sum(row["net_revenue_inr"] for row in monthly),
            self.result.metrics["total_net_revenue_inr"],
        )

    def test_payment_distribution(self):
        payments = {
            row["payment_method"]: row
            for row in self.result.tables["payment_method_distribution"]
        }
        self.assertAlmostEqual(payments["UPI"]["net_revenue_inr"], 305.0)
        self.assertEqual(payments["UPI"]["orders"], 2)
        self.assertAlmostEqual(payments["UPI"]["revenue_share_pct"], 60.4)
        self.assertAlmostEqual(payments["Credit Card"]["order_share_pct"], 33.33)

    def test_summary_tables_are_written(self):
        with tempfile.TemporaryDirectory() as folder:
            written = write_analysis_tables(self.result, Path(folder))
            self.assertEqual(len(written), len(TABLE_COLUMNS))
            for name in TABLE_COLUMNS:
                path = Path(folder) / f"{name}.csv"
                self.assertTrue(path.is_file(), f"missing {path}")

            with (Path(folder) / "overall_metrics.csv").open(
                newline="", encoding="utf-8"
            ) as handle:
                metrics = {
                    row["metric"]: row["value"]
                    for row in csv.DictReader(handle)
                }
            self.assertIn("total_net_revenue_inr", metrics)
            self.assertIn("average_order_value_inr", metrics)


class RealDatasetTests(unittest.TestCase):
    def test_cleaned_dataset_aggregates_consistently(self):
        if not CLEANED_PATH.exists():
            self.skipTest("cleaned dataset missing; run python3 main.py all")

        rows = load_rows(CLEANED_PATH)
        result = analyse_rows(rows)
        metrics = result.metrics

        self.assertEqual(metrics["cleaned_line_items"], len(rows))
        self.assertEqual(
            metrics["unique_orders"],
            len({row["order_id"] for row in rows}),
        )
        self.assertAlmostEqual(
            metrics["average_order_value_inr"],
            round(metrics["total_net_revenue_inr"] / metrics["unique_orders"], 2),
        )
        self.assertAlmostEqual(
            sum(row["net_revenue_inr"] for row in result.tables["monthly_revenue"]),
            metrics["total_net_revenue_inr"],
        )
        self.assertAlmostEqual(
            sum(
                row["net_revenue_inr"]
                for row in result.tables["payment_method_distribution"]
            ),
            metrics["total_net_revenue_inr"],
        )

    def test_all_revenue_dimensions_match_overall_total(self):
        if not CLEANED_PATH.exists():
            self.skipTest("cleaned dataset missing; run python3 main.py all")

        result = analyse_rows(load_rows(CLEANED_PATH))
        total = result.metrics["total_net_revenue_inr"]
        for table_name in [
            "revenue_by_category",
            "revenue_by_product",
            "revenue_by_city",
            "monthly_revenue",
        ]:
            with self.subTest(table=table_name):
                table_total = sum(
                    row["net_revenue_inr"] for row in result.tables[table_name]
                )
                self.assertAlmostEqual(table_total, total, places=2)


if __name__ == "__main__":
    unittest.main()
