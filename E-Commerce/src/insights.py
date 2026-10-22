"""Generate a fact-based business insights report from the actual analysis.

Every number in the report is derived from the cleaned dataset via
``src.analysis``. Nothing is hardcoded. The report is plain text and includes
recommendations that are framed as actions to test, not proven causes.

Run:
    python3 -m src.insights
    python3 main.py visualise
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):  # allow: python3 src/insights.py
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import AnalysisResult, analyse_rows  # noqa: E402
from src.data_cleaning import CLEANED_PATH, load_rows  # noqa: E402
from src.visualization import format_inr  # noqa: E402

REPORTS_DIR = PROJECT_ROOT / "output" / "reports"
INSIGHTS_PATH = REPORTS_DIR / "business_insights.txt"
SEPARATOR = "=" * 80


def _number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() in {"na", "n/a", "none", "null"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _integer(value) -> int:
    number = _number(value)
    return int(round(number)) if number is not None else 0


def _month_name(value) -> str:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return text or "Unknown month"


def _sorted_by(rows: list[dict], key: str) -> list[dict]:
    usable = [row for row in rows if _number(row.get(key)) is not None]
    return sorted(usable, key=lambda row: -_number(row.get(key)))


def _named(rows: list[dict], key: str) -> list[dict]:
    return [row for row in rows if str(row.get(key) or "").strip() not in {"", "Unknown"}]


def _finding(number: int, title: str, evidence: str, action: str) -> list[str]:
    return [
        f"{number}. {title}",
        f"   What the data shows: {evidence}",
        f"   Suggested action: {action}",
        "",
    ]


def build_insights(result: AnalysisResult) -> str:
    """Build the plain-text insights report from an analysis result."""
    metrics = result.metrics
    monthly = _sorted_by(
        [row for row in result.tables.get("monthly_revenue", [])], "net_revenue_inr"
    )
    monthly_chronological = sorted(
        [row for row in result.tables.get("monthly_revenue", [])],
        key=lambda row: str(row.get("month", "")),
    )
    categories = _sorted_by(result.tables.get("revenue_by_category", []), "net_revenue_inr")
    products = _sorted_by(result.tables.get("revenue_by_product", []), "net_revenue_inr")
    products_by_units = sorted(
        [
            row
            for row in result.tables.get("revenue_by_product", [])
            if _number(row.get("units_sold")) is not None
        ],
        key=lambda row: -_number(row.get("units_sold")),
    )
    cities = _sorted_by(result.tables.get("revenue_by_city", []), "net_revenue_inr")
    payments = _sorted_by(
        result.tables.get("payment_method_distribution", []), "net_revenue_inr"
    )

    total_revenue = _number(metrics.get("total_net_revenue_inr")) or 0.0
    unique_orders = _integer(metrics.get("unique_orders"))
    units = _integer(metrics.get("total_units_sold"))
    average_order_value = _number(metrics.get("average_order_value_inr")) or 0.0

    lines = [
        "BUSINESS INSIGHTS REPORT",
        "E-commerce Sales Data Analysis Using Python",
        SEPARATOR,
        "Dataset note: ALL figures below come from a SYNTHETIC e-commerce dataset.",
        "It contains no real customers or transactions. Findings demonstrate the",
        "analysis method and must not be treated as real market evidence.",
        "",
        f"Scope: {unique_orders:,} unique orders | {units:,} units | "
        f"{metrics.get('date_range_start', 'n/a')} to {metrics.get('date_range_end', 'n/a')}",
        f"Net revenue after discounts: {format_inr(total_revenue)} (INR)",
        "",
    ]

    if unique_orders == 0 or not monthly:
        lines.extend(
            [
                "No usable sales records were available, so no business findings",
                "could be produced. Run the cleaning and analysis stages first.",
                "",
            ]
        )
        return "\n".join(lines)

    strongest_month = monthly[0]
    strongest_revenue = _number(strongest_month.get("net_revenue_inr")) or 0.0
    strongest_share = (
        strongest_revenue / total_revenue * 100 if total_revenue else 0.0
    )
    average_monthly = total_revenue / len(monthly) if monthly else 0.0
    vs_average = (
        (strongest_revenue / average_monthly - 1) * 100 if average_monthly else 0.0
    )

    top_category = categories[0] if categories else None
    top_city = cities[0] if cities else None
    top_payment = payments[0] if payments else None

    lines.extend(
        [
            "EXECUTIVE SNAPSHOT",
            "-" * 80,
            f"- Total net revenue: {format_inr(total_revenue)}",
            f"- Unique orders: {unique_orders:,}",
            f"- Units sold: {units:,}",
            f"- Average order value: {format_inr(average_order_value)}",
        ]
    )
    if top_category:
        lines.append(
            f"- Leading category: {top_category.get('category')} "
            f"({format_inr(top_category.get('net_revenue_inr'))})"
        )
    lines.append(
        f"- Strongest month: {_month_name(strongest_month.get('month'))} "
        f"({format_inr(strongest_revenue)})"
    )
    if products:
        lines.append(
            f"- Top product by revenue: {products[0].get('product_name')} "
            f"({format_inr(products[0].get('net_revenue_inr'))})"
        )
    if top_city:
        lines.append(
            f"- Leading city: {top_city.get('city')} "
            f"({format_inr(top_city.get('net_revenue_inr'))})"
        )
    lines.extend(["", "FINDINGS", "-" * 80, ""])

    finding_number = 1

    if top_category:
        category_name = str(top_category.get("category") or "Unknown")
        category_revenue = _number(top_category.get("net_revenue_inr")) or 0.0
        category_share = (
            category_revenue / total_revenue * 100 if total_revenue else 0.0
        )
        category_orders = _integer(top_category.get("orders"))
        category_units = _integer(top_category.get("units_sold"))
        runners_up = categories[1:3]
        runner_text = ""
        if runners_up:
            runner_text = (
                " The next two categories were "
                + " and ".join(
                    f"{row.get('category')} "
                    f"({format_inr(row.get('net_revenue_inr'))})"
                    for row in runners_up
                )
                + "."
            )
        lines.extend(
            _finding(
                finding_number,
                f"{category_name} is the highest-revenue product category",
                (
                    f"{category_name} generated {format_inr(category_revenue)}, "
                    f"or {category_share:.2f}% of net revenue, from "
                    f"{category_orders:,} orders and {category_units:,} units."
                    f"{runner_text}"
                ),
                (
                    f"Keep {category_name} well stocked and test focused campaigns "
                    "for it. Also check whether its revenue is accompanied by heavy "
                    "discounting before increasing investment; the data alone does "
                    "not show profitability."
                ),
            )
        )
        finding_number += 1

    month_name = _month_name(strongest_month.get("month"))
    month_orders = _integer(strongest_month.get("orders"))
    month_units = _integer(strongest_month.get("units_sold"))
    lines.extend(
        _finding(
            finding_number,
            f"{month_name} was the strongest month for revenue",
            (
                f"{month_name} produced {format_inr(strongest_revenue)} "
                f"({strongest_share:.2f}% of annual revenue) from "
                f"{month_orders:,} unique orders and {month_units:,} units. "
                f"That is {abs(vs_average):.2f}% "
                f"{'above' if vs_average >= 0 else 'below'} the average month "
                f"of {format_inr(average_monthly)}."
            ),
            (
                "Use this peak period for capacity, inventory and staffing "
                "planning. The dataset shows timing but cannot prove why the peak "
                "occurred, so validate the pattern with real operational data."
            ),
        )
    )
    finding_number += 1

    if products:
        best = products[0]
        best_revenue = _number(best.get("net_revenue_inr")) or 0.0
        best_share = best_revenue / total_revenue * 100 if total_revenue else 0.0
        top_three = products[:3]
        top_three_revenue = sum(
            _number(row.get("net_revenue_inr")) or 0.0 for row in top_three
        )
        top_three_share = (
            top_three_revenue / total_revenue * 100 if total_revenue else 0.0
        )
        by_units = products_by_units[0] if products_by_units else best
        lines.extend(
            _finding(
                finding_number,
                f"{best.get('product_name')} leads product revenue",
                (
                    f"{best.get('product_name')} generated "
                    f"{format_inr(best_revenue)} ({best_share:.2f}% of total) from "
                    f"{_integer(best.get('units_sold')):,} units. The top three "
                    f"products together contributed {format_inr(top_three_revenue)} "
                    f"({top_three_share:.2f}%). By units, "
                    f"{by_units.get('product_name')} led with "
                    f"{_integer(by_units.get('units_sold')):,} units."
                ),
                (
                    "Protect availability and visibility for the leading products, "
                    "and review their discount levels rather than assuming high "
                    "revenue means high profit. High concentration also creates "
                    "stock-out risk."
                ),
            )
        )
        finding_number += 1

    if top_city:
        city_name = str(top_city.get("city") or "Unknown")
        city_revenue = _number(top_city.get("net_revenue_inr")) or 0.0
        city_share = city_revenue / total_revenue * 100 if total_revenue else 0.0
        top_cities = _named(cities, "city")[:3]
        top_city_revenue = sum(
            _number(row.get("net_revenue_inr")) or 0.0 for row in top_cities
        )
        top_city_share = (
            top_city_revenue / total_revenue * 100 if total_revenue else 0.0
        )
        city_text = ", ".join(
            f"{row.get('city')} ({format_inr(row.get('net_revenue_inr'))})"
            for row in top_cities
        )
        unknown_row = next(
            (row for row in cities if str(row.get("city")) == "Unknown"), None
        )
        unknown_text = ""
        if unknown_row:
            unknown_text = (
                f" Orders with an unknown city numbered "
                f"{_integer(unknown_row.get('orders')):,} and contributed "
                f"{format_inr(unknown_row.get('net_revenue_inr'))}; improving "
                "city capture would make geographic reporting more complete."
            )
        lines.extend(
            _finding(
                finding_number,
                f"{city_name} is the leading city by revenue",
                (
                    f"{city_name} contributed {format_inr(city_revenue)} "
                    f"({city_share:.2f}% of total). The top three named cities "
                    f"were {city_text}, together accounting for "
                    f"{top_city_share:.2f}% of revenue.{unknown_text}"
                ),
                (
                    "Prioritise fulfilment and local campaigns in the strongest "
                    "cities, while treating the ranking as descriptive. Improve "
                    "city data capture at checkout so the comparison is complete."
                ),
            )
        )
        finding_number += 1

    changes = [
        row
        for row in monthly_chronological
        if _number(row.get("mom_change_pct")) is not None
    ]
    if changes:
        increases = [row for row in changes if _number(row.get("mom_change_pct")) > 0]
        decreases = [row for row in changes if _number(row.get("mom_change_pct")) < 0]
        largest_rise = max(changes, key=lambda row: _number(row.get("mom_change_pct")))
        largest_fall = min(changes, key=lambda row: _number(row.get("mom_change_pct")))
        rise_pct = _number(largest_rise.get("mom_change_pct"))
        fall_pct = _number(largest_fall.get("mom_change_pct"))
        rise_amount = _number(largest_rise.get("mom_change_inr")) or 0.0
        fall_amount = _number(largest_fall.get("mom_change_inr")) or 0.0
        lines.extend(
            _finding(
                finding_number,
                "Monthly revenue is volatile rather than steadily growing",
                (
                    f"Revenue increased in {len(increases)} of {len(changes)} "
                    f"month-over-month comparisons and decreased in "
                    f"{len(decreases)}. The largest rise was in "
                    f"{_month_name(largest_rise.get('month'))} "
                    f"({format_inr(rise_amount)}, {rise_pct:+.2f}%), while the "
                    f"largest fall was in "
                    f"{_month_name(largest_fall.get('month'))} "
                    f"({format_inr(fall_amount)}, {fall_pct:+.2f}%)."
                ),
                (
                    "Investigate the high-change months by category, product and "
                    "city before repeating any promotion or stock plan. Do not "
                    "assume the changes were caused by seasonality; the dataset "
                    "does not contain marketing spend, competitor or causal data."
                ),
            )
        )
        finding_number += 1

    if top_payment:
        payment_name = str(top_payment.get("payment_method") or "Unknown")
        payment_revenue = _number(top_payment.get("net_revenue_inr")) or 0.0
        payment_share = (
            payment_revenue / total_revenue * 100 if total_revenue else 0.0
        )
        lines.extend(
            _finding(
                finding_number,
                "Average order value and payment mix point to basket opportunities",
                (
                    f"The average order value is "
                    f"{format_inr(average_order_value)} across "
                    f"{unique_orders:,} unique orders. {payment_name} is the "
                    f"largest payment method by revenue, with "
                    f"{format_inr(payment_revenue)} ({payment_share:.2f}% of "
                    f"revenue) and "
                    f"{_number(top_payment.get('order_share_pct')) or 0.0:.2f}% "
                    "of orders."
                ),
                (
                    "Test bundles or order-value thresholds to lift the average "
                    "order value, and monitor checkout reliability for the leading "
                    "payment method. These are hypotheses to test, not proven "
                    "revenue drivers."
                ),
            )
        )
        finding_number += 1

    lines.extend(
        [
            "RECOMMENDATIONS AT A GLANCE",
            "-" * 80,
        ]
    )
    recommendations = []
    if top_category:
        recommendations.append(
            f"Plan inventory and campaigns around {top_category.get('category')}, "
            "while reviewing discount depth and profitability."
        )
    recommendations.extend(
        [
            f"Prepare capacity for the {month_name} peak, then validate it on "
            "real data before treating it as a recurring seasonal pattern.",
            "Keep top-selling products available and reduce concentration risk "
            "by developing a second strong product group.",
            "Improve city capture at checkout and focus local execution on the "
            "highest-revenue cities.",
            "Investigate large month-to-month swings with category, product and "
            "city breakdowns rather than assuming a cause.",
            "Test basket-building offers and monitor the leading payment method.",
        ]
    )
    for index, recommendation in enumerate(recommendations, start=1):
        lines.append(f"{index}. {recommendation}")
    lines.extend(
        [
            "",
            "DATA NOTES AND LIMITATIONS",
            "-" * 80,
            "- This is synthetic data, not a real business dataset.",
            "- Revenue is net of discounts and excludes costs, refunds and returns.",
            "- Missing discounts were treated as 0% by the cleaning rule.",
            "- Average order value = total net revenue / unique order_id count.",
            "- Figures describe associations in this dataset; they do not establish "
            "causation.",
            "- Only one synthetic year is covered, so long-term seasonality cannot "
            "be verified.",
            "",
        ]
    )
    return "\n".join(lines)


def write_insights(
    result: AnalysisResult, output_path: Path = INSIGHTS_PATH
) -> Path:
    """Write the insights report to a UTF-8 text file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_insights(result), encoding="utf-8")
    return output_path


def run_insights(
    input_path: Path = CLEANED_PATH,
    output_path: Path = INSIGHTS_PATH,
    verbose: bool = True,
) -> Path:
    """Load cleaned data, analyse it, and write the insights report."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {input_path}\n"
            "Run: python3 main.py all"
        )

    result = analyse_rows(load_rows(input_path))
    path = write_insights(result, output_path)
    if verbose:
        print(f"Business insights written: {path}")
    return path


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the business insights report from cleaned data."
    )
    parser.add_argument("--input", type=Path, default=CLEANED_PATH)
    parser.add_argument("--output", type=Path, default=INSIGHTS_PATH)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_insights(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
