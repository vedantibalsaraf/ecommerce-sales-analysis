"""Tests for the standard-library SVG chart generation."""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import analyse_rows  # noqa: E402
from src.visualization import (  # noqa: E402
    CHARTS_DIR,
    CHART_FILES,
    format_compact_inr,
    format_inr,
    generate_charts,
)

SVG_NS = "{http://www.w3.org/2000/svg}"


def sale(product, category, quantity, price, discount, city="Mumbai", month="2025-01"):
    return {
        "order_id": f"ORD-{product[:3]}-{month}",
        "order_date": f"{month}-05",
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
        sale("Widget", "Electronics", "2", "100", "10"),
        sale("Gadget", "Fashion", "1", "50", "0"),
        sale("Widget", "Electronics", "1", "200", "", city="Delhi", month="2025-02"),
        sale("Gadget", "Fashion", "3", "50", "50", month="2025-02"),
    ]


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.folder = Path(self.temp_dir.name)

    def assert_valid_svg(self, path: Path):
        self.assertTrue(path.is_file(), f"missing {path}")
        self.assertGreater(path.stat().st_size, 500, f"too small: {path}")
        root = ET.parse(path).getroot()
        self.assertEqual(root.tag, f"{SVG_NS}svg")
        self.assertGreater(int(root.get("width")), 0)
        self.assertGreater(int(root.get("height")), 0)
        self.assertTrue(root.get("viewBox"))
        texts = [
            node.text
            for node in root.iter(f"{SVG_NS}text")
            if node.text and node.text.strip()
        ]
        self.assertTrue(texts, f"no text labels in {path}")
        titles = [node.text for node in root.iter(f"{SVG_NS}title")]
        self.assertTrue(titles and titles[0], f"no title in {path}")
        return texts

    def test_all_five_charts_are_valid_svg(self):
        result = analyse_rows(sample_rows())
        paths = generate_charts(result, self.folder)

        self.assertEqual(len(paths), 5)
        self.assertEqual(
            {path.name for path in paths}, set(CHART_FILES.values())
        )
        text_by_chart = {
            path.name: self.assert_valid_svg(path) for path in paths
        }

        monthly = " ".join(text_by_chart["monthly_net_revenue.svg"])
        self.assertIn("Monthly Net Revenue", monthly)
        self.assertIn("Jan 25", monthly)
        self.assertIn("Feb 25", monthly)
        self.assertIn("₹230", monthly)

        category = " ".join(text_by_chart["revenue_by_category.svg"])
        self.assertIn("Revenue by Product Category", category)
        self.assertIn("Electronics", category)
        self.assertIn("Fashion", category)

        products = " ".join(text_by_chart["top_10_products_by_revenue.svg"])
        self.assertIn("Top 10 Products by Revenue", products)
        self.assertIn("Widget", products)

        orders = " ".join(text_by_chart["monthly_order_count.svg"])
        self.assertIn("Monthly Order Count", orders)
        self.assertIn("Jan 25", orders)

        cities = " ".join(text_by_chart["revenue_by_city.svg"])
        self.assertIn("Revenue by City", cities)
        self.assertIn("Mumbai", cities)

    def test_empty_dataset_still_produces_valid_svgs(self):
        result = analyse_rows([])
        paths = generate_charts(result, self.folder)
        self.assertEqual(len(paths), 5)

        for path in paths:
            texts = self.assert_valid_svg(path)
            self.assertTrue(
                any("No data available" in text for text in texts),
                f"missing empty-state message in {path.name}",
            )

    def test_missing_and_invalid_values_are_handled(self):
        result = analyse_rows(sample_rows())
        result.tables["monthly_revenue"][0]["net_revenue_inr"] = ""
        result.tables["monthly_revenue"][1]["orders"] = None
        result.tables["revenue_by_category"][0]["net_revenue_inr"] = "n/a"
        result.tables["revenue_by_city"][0]["net_revenue_inr"] = None
        result.tables["top_products_by_revenue"][0]["net_revenue_inr"] = ""

        paths = generate_charts(result, self.folder)
        self.assertEqual(len(paths), 5)
        for path in paths:
            self.assert_valid_svg(path)

        all_text = " ".join(
            text
            for path in paths
            for text in self.assert_valid_svg(path)
        )
        self.assertIn("n/a", all_text)

    def test_long_labels_are_truncated_or_wrapped(self):
        result = analyse_rows(
            [
                sale(
                    "Extraordinarily Long Product Name That Must Fit",
                    "A Very Long Category Name For Testing Layout",
                    "1",
                    "100",
                    "0",
                )
            ]
        )
        paths = generate_charts(result, self.folder)
        for path in paths:
            self.assert_valid_svg(path)

        product_text = " ".join(
            node.text
            for path in paths
            if path.name == "top_10_products_by_revenue.svg"
            for node in ET.parse(path).getroot().iter(f"{SVG_NS}text")
            if node.text
        )
        self.assertIn("...", product_text)

    def test_currency_formatters(self):
        self.assertEqual(format_inr(4711999.65), "₹47,11,999.65")
        self.assertEqual(format_compact_inr(653958.8), "₹6.5L")
        self.assertEqual(format_compact_inr(12600000), "₹1.3Cr")
        self.assertEqual(format_compact_inr("not-a-number"), "n/a")


class GeneratedOutputTests(unittest.TestCase):
    def test_actual_chart_files_exist_and_parse(self):
        missing = [
            name for name in CHART_FILES.values() if not (CHARTS_DIR / name).is_file()
        ]
        if missing:
            self.skipTest(
                "charts not generated yet; run python3 main.py visualise"
            )

        for name in CHART_FILES.values():
            path = CHARTS_DIR / name
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, f"{SVG_NS}svg")
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
