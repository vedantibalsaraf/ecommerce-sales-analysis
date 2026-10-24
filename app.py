"""Streamlit dashboard for the E-commerce Sales Data Analysis project.

This is the web entry point used by Streamlit Community Cloud. It reuses the
existing analysis, chart and insights modules in ``src/`` — no calculations
are duplicated here. The command-line pipeline (``main.py``) still works
exactly as before.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import csv
import re
import tempfile
from pathlib import Path

import streamlit as st

from src.analysis import DEFAULT_TOP_N, AnalysisResult, analyse_rows
from src.data_cleaning import CLEANED_PATH, RAW_PATH, load_rows, run_cleaning
from src.insights import build_insights
from src.visualization import format_inr, generate_charts

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLEANING_REPORT_PATH = PROCESSED_DIR / "cleaning_report.csv"
CHARTS_DIR = PROJECT_ROOT / "output" / "charts"
INSIGHTS_PATH = PROJECT_ROOT / "output" / "reports" / "business_insights.txt"

st.set_page_config(
    page_title="E-commerce Sales Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

MONEY_COLUMNS = {
    "net_revenue_inr",
    "gross_revenue_inr",
    "total_discount_amount_inr",
    "average_order_value_inr",
    "mom_change_inr",
}
PERCENT_COLUMNS = {"revenue_share_pct", "order_share_pct", "mom_change_pct"}


# --------------------------------------------------------------------------- #
# Data loading and caching
# --------------------------------------------------------------------------- #
def ensure_cleaned_data() -> None:
    """Create the cleaned CSV from the raw CSV if it is missing."""
    if CLEANED_PATH.exists():
        return
    if not RAW_PATH.exists():
        st.error(
            "No dataset found. Expected `data/raw/sales_data.csv` or "
            "`data/processed/cleaned_sales_data.csv` in the repository."
        )
        st.stop()
    with st.spinner("Preparing the cleaned dataset…"):
        run_cleaning(verbose=False)


@st.cache_data(show_spinner=False)
def load_sales_rows(path: str) -> list[dict]:
    return load_rows(Path(path))


@st.cache_data(show_spinner=False)
def build_analysis(rows: list[dict], top_n: int) -> AnalysisResult:
    return analyse_rows(rows, top_n=top_n)


@st.cache_data(show_spinner=False)
def build_charts(tables: dict) -> dict[str, str]:
    """Render the project's SVG charts into a temporary folder."""
    output_dir = Path(tempfile.mkdtemp(prefix="ecommerce_charts_"))
    result = AnalysisResult(metrics={}, tables=tables)
    paths = generate_charts(result, output_dir)
    return {path.stem: path.read_text(encoding="utf-8") for path in paths}


# --------------------------------------------------------------------------- #
# Small display helpers
# --------------------------------------------------------------------------- #
def responsive_svg(svg: str) -> str:
    """Make a fixed-width SVG scale to its container."""
    svg = re.sub(r"^\s*<\?xml[^>]*\?>", "", svg).strip()
    match = re.search(r"<svg\b[^>]*>", svg)
    if not match:
        return svg
    opening = match.group(0)
    cleaned = re.sub(r'\s(?:width|height)="[^"]*"', "", opening)
    cleaned = cleaned.replace("<svg", '<svg style="width:100%;height:auto"', 1)
    return svg[: match.start()] + cleaned + svg[match.end() :]


def show_chart(chart_name: str, charts: dict[str, str], caption: str = "") -> None:
    svg = charts.get(chart_name)
    if not svg:
        st.info("This chart could not be generated.")
        return
    st.markdown(responsive_svg(svg), unsafe_allow_html=True)
    if caption:
        st.caption(caption)


def show_table(rows: list[dict], money: set[str] = MONEY_COLUMNS,
               percent: set[str] = PERCENT_COLUMNS) -> None:
    if not rows:
        st.info("No rows match the current selection.")
        return

    # Blank strings (e.g. the first month's month-over-month change) become
    # empty cells so Streamlit can keep the column numeric.
    display_rows = [
        {key: (None if value == "" else value) for key, value in row.items()}
        for row in rows
    ]

    def first_value(column: str):
        return next(
            (value for value in (row.get(column) for row in display_rows)
             if value is not None),
            None,
        )

    config = {}
    for column in display_rows[0]:
        label = column.replace("_", " ").title().replace("Inr", "INR")
        numeric = isinstance(first_value(column), (int, float))
        if not numeric:
            continue
        if column in money:
            config[column] = st.column_config.NumberColumn(f"{label} (₹)", format="%.2f")
        elif column in percent:
            config[column] = st.column_config.NumberColumn(f"{label} (%)", format="%.2f")
        else:
            config[column] = st.column_config.NumberColumn(label)

    st.dataframe(display_rows, column_config=config or None, hide_index=True)


def read_cleaning_report() -> list[dict]:
    if not CLEANING_REPORT_PATH.exists():
        return []
    with CLEANING_REPORT_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        count = (row.get("rows_affected") or "").strip()
        row["rows_affected"] = int(count) if count.isdigit() else count
    return rows


def download_row(label: str, path: Path, mime: str, key: str) -> None:
    if path.exists():
        st.download_button(label, path.read_bytes(), file_name=path.name, mime=mime, key=key)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
ensure_cleaned_data()
all_rows = load_sales_rows(str(CLEANED_PATH))
categories = sorted({row["category"] for row in all_rows if row["category"]})

with st.sidebar:
    st.header("Dashboard controls")
    selected_categories = st.multiselect(
        "Categories",
        options=categories,
        default=categories,
        help="Filter every chart and table by product category.",
    )
    top_n = st.slider(
        "Products in the product tables",
        min_value=5,
        max_value=25,
        value=DEFAULT_TOP_N,
        step=5,
    )
    st.divider()
    st.caption(
        f"**{len(all_rows):,}** cleaned line items · "
        f"**{len(categories)}** categories\n\n"
        "Source: `data/processed/cleaned_sales_data.csv`"
    )
    st.caption(
        "This dataset is synthetic. It contains no real customers, "
        "transactions or market evidence."
    )
    st.divider()
    download_row("⬇ Cleaned dataset (CSV)", CLEANED_PATH, "text/csv", "dl-cleaned")
    download_row("⬇ Insights report (TXT)", INSIGHTS_PATH, "text/plain", "dl-insights")

if not selected_categories:
    st.warning("Select at least one category in the sidebar to see results.")
    st.stop()

filtered_rows = [row for row in all_rows if row["category"] in selected_categories]
result = build_analysis(filtered_rows, top_n)
metrics = result.metrics
tables = result.tables
charts = build_charts(tables)

# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("🛒 E-commerce Sales Dashboard")
st.markdown(
    "Net revenue, orders, products, categories, cities and payment methods — "
    "calculated with the project's standard-library analysis pipeline."
)

first, second, third, fourth = st.columns(4)
first.metric("Net revenue", format_inr(metrics["total_net_revenue_inr"], 0))
second.metric("Unique orders", f"{metrics['unique_orders']:,}")
third.metric("Units sold", f"{metrics['total_units_sold']:,}")
fourth.metric("Average order value", format_inr(metrics["average_order_value_inr"], 0))

with st.expander("How these numbers are calculated"):
    st.markdown(
        "- **Net revenue** = `quantity × unit_price × (1 − discount / 100)`.\n"
        "- A blank discount is treated as 0%.\n"
        "- Exact duplicate rows were removed during cleaning; rows sharing an "
        "`order_id` are kept as separate line items but the order is counted "
        "once in order-based metrics.\n"
        "- Figures are in Indian rupees (INR) and cover "
        f"{metrics['date_range_start']} to {metrics['date_range_end']}."
    )

# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
overview_tab, category_tab, product_tab, city_tab, payment_tab, quality_tab, \
    insights_tab, data_tab = st.tabs(
        [
            "Overview",
            "Categories",
            "Products",
            "Cities",
            "Payments",
            "Data quality",
            "Insights",
            "Data",
        ]
    )

with overview_tab:
    st.subheader("Monthly performance")
    show_chart(
        "monthly_net_revenue",
        charts,
        "Net revenue after discounts, January–December.",
    )
    show_chart("monthly_order_count", charts, "Number of unique orders per month.")
    st.subheader("Month-by-month table")
    show_table(tables["monthly_revenue"])

with category_tab:
    st.subheader("Revenue by category")
    show_chart("revenue_by_category", charts)
    show_table(tables["revenue_by_category"])

with product_tab:
    st.subheader("Product performance")
    show_chart(
        "top_10_products_by_revenue",
        charts,
        "The chart always shows the top 10; the tables below show the number "
        "chosen in the sidebar.",
    )
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Top {top_n} products by revenue**")
        show_table(tables["top_products_by_revenue"])
    with right:
        st.markdown(f"**Top {top_n} products by quantity**")
        show_table(tables["top_products_by_quantity"])
    with st.expander("All products"):
        show_table(tables["revenue_by_product"])

with city_tab:
    st.subheader("Revenue by city")
    show_chart("revenue_by_city", charts)
    show_table(tables["revenue_by_city"])

with payment_tab:
    st.subheader("Payment methods")
    show_table(tables["payment_method_distribution"])
    st.caption(
        "Payment methods are ranked by net revenue. Shares are calculated "
        "from unique orders and total net revenue."
    )

with quality_tab:
    st.subheader("Data quality report")
    report_rows = read_cleaning_report()
    raw_count = len(load_sales_rows(str(RAW_PATH))) if RAW_PATH.exists() else None
    inputs, kept = st.columns(2)
    inputs.metric("Raw rows", f"{raw_count:,}" if raw_count is not None else "n/a")
    kept.metric("Rows kept after cleaning", f"{len(all_rows):,}")
    st.caption(
        "Cleaning rules are documented in `src/data_cleaning.py` and in the "
        "report below. Invalid rows are removed only when a critical field is "
        "missing or malformed."
    )
    if report_rows:
        st.dataframe(report_rows, hide_index=True)
        download_row(
            "⬇ Cleaning report (CSV)",
            CLEANING_REPORT_PATH,
            "text/csv",
            "dl-cleaning-report",
        )
    else:
        st.info("Run `python3 main.py clean` to create `cleaning_report.csv`.")

with insights_tab:
    st.subheader("Business insights")
    st.caption(
        "Generated from the current filtered data, so the numbers follow the "
        "category filter in the sidebar."
    )
    st.text(build_insights(result))

with data_tab:
    st.subheader("Cleaned data")
    st.caption(
        f"Showing {len(filtered_rows):,} of {len(all_rows):,} rows. "
        "Use the sidebar to filter by category."
    )
    st.dataframe(filtered_rows, hide_index=True)

st.divider()
st.caption(
    "E-commerce Sales Data Analysis Using Python · synthetic dataset · "
    "built with the Python standard library and Streamlit."
)
