# E-commerce Sales Data Analysis Using Python

A complete, beginner-friendly data analytics project built **only with the
Python standard library**. It generates a reproducible synthetic e-commerce
dataset, cleans and validates it, calculates sales metrics, writes five SVG
charts, and produces a fact-based business insights report.

> **Status: complete.** All four stages are implemented and tested on macOS
> with Python 3.13.15.

## Overview

The project demonstrates a full, local analytics workflow without pandas,
numpy, matplotlib, SQL, notebooks, APIs or any external service:

1. Generate 1,525 synthetic order rows with realistic Indian products,
   cities, prices, discounts and payment methods.
2. Clean the data and document every data-quality decision.
3. Analyse revenue, orders, products, categories, cities, months and payments.
4. Draw five SVG charts directly as XML and write a plain-text insights report.

The dataset is **synthetic**. It contains no real customers, names, emails,
addresses or transactions, and the findings are not real market evidence.

## Problem statement

A raw e-commerce sales file often contains duplicate submissions, missing
optional values, and inconsistent numeric fields. Before anyone can answer
basic commercial questions, the data must be validated and cleaned.

This project answers:

- How much net revenue was earned after discounts?
- Which categories, products and cities generate the most revenue?
- How do revenue and order counts change month to month?
- Which payment methods are used most?
- What is the average order value?
- What practical actions are supported by the data?

## Objectives

- Build a reproducible synthetic dataset using only the standard library.
- Load and validate the raw CSV without silently dropping useful rows.
- Remove only exact duplicates and clearly unusable records.
- Calculate revenue with an explicit, documented formula.
- Produce reusable CSV summary tables.
- Generate accessible SVG charts with sensible INR formatting.
- Write a business report that separates evidence from recommendations.
- Test the calculations, cleaning rules and outputs with `unittest`.
- Keep the entire project installable with zero third-party packages.

## Tools used and Python-only constraint

- **Python 3.10+**, tested with **Python 3.13.15** on macOS.
- Standard-library modules used include `argparse`, `calendar`, `csv`,
  `random`, `datetime`, `pathlib`, `collections`, `dataclasses`, `math`,
  `html`, `unittest` and `xml.etree.ElementTree`.
- No third-party dependencies.
- No pandas, numpy, matplotlib, seaborn, plotly, JavaScript, SQL, databases,
  Jupyter Notebook, APIs or web frameworks.
- SVG charts are written as XML strings by `src/visualization.py`.

**Do not run `pip install`.** `requirements.txt` intentionally lists no
packages. The project does not modify the system Python environment.

## Project structure

```
E-Commerce/
├── main.py                     # Status and all pipeline commands
├── README.md
├── requirements.txt            # Explicitly no external dependencies
├── .gitignore
├── data/
│   ├── __init__.py
│   ├── generate_data.py        # Reproducible synthetic data generator
│   ├── raw/
│   │   └── sales_data.csv      # 1,525 raw rows (generated)
│   └── processed/
│       ├── cleaned_sales_data.csv
│       ├── cleaning_report.csv
│       ├── overall_metrics.csv
│       ├── revenue_by_category.csv
│       ├── revenue_by_product.csv
│       ├── revenue_by_city.csv
│       ├── top_products_by_quantity.csv
│       ├── top_products_by_revenue.csv
│       ├── monthly_revenue.csv
│       └── payment_method_distribution.csv
├── src/
│   ├── __init__.py
│   ├── data_cleaning.py        # Load, validate, clean and report
│   ├── analysis.py             # Revenue and aggregation logic
│   ├── visualization.py        # Five standard-library SVG charts
│   └── insights.py             # Business insights report
├── tests/
│   ├── test_dataset.py
│   ├── test_cleaning.py
│   ├── test_analysis.py
│   ├── test_visualization.py
│   ├── test_insights.py
│   ├── test_pipeline.py
│   └── test_standard_library.py
└── output/
    ├── charts/
    │   ├── monthly_net_revenue.svg
    │   ├── revenue_by_category.svg
    │   ├── top_10_products_by_revenue.svg
    │   ├── monthly_order_count.svg
    │   └── revenue_by_city.svg
    └── reports/
        └── business_insights.txt
```

## Setup and execution on macOS

No environment setup or installation is required. Open Terminal, change to
the project root, and run the pipeline:

```bash
cd /Users/vedantibalsaraf/Desktop/E-Commerce
python3 --version          # expected: Python 3.10 or newer
python3 main.py all
```

`python3 main.py all` runs the complete pipeline in this order:

1. Generate `data/raw/sales_data.csv` **only if it does not already exist**.
2. Clean and validate the raw data.
3. Calculate all sales metrics and summary tables.
4. Generate all five SVG charts.
5. Generate the business insights report.

If the raw dataset already exists, it is **not** regenerated. Re-running the
pipeline only refreshes the processed tables, charts and report.

### Individual commands

All commands work from the project root:

```bash
python3 main.py                 # Show status and available commands
python3 main.py generate        # Explicitly (re)generate the raw dataset
python3 main.py check           # Validate the raw dataset
python3 main.py clean           # Clean and validate the raw data
python3 main.py analyse         # Calculate summary tables (alias: analyze)
python3 main.py visualise       # Charts + insights (alias: visualize)
python3 main.py all             # Complete pipeline
```

The stages can also be run as modules:

```bash
python3 -m src.data_cleaning
python3 -m src.analysis
python3 -m src.visualization
python3 -m src.insights
```

### Run the tests

```bash
python3 main.py check
python3 -m unittest discover -s tests -v
```

### View the outputs

```bash
open output/reports/business_insights.txt
open output/charts/monthly_net_revenue.svg
open output/charts/revenue_by_category.svg
open output/charts/top_10_products_by_revenue.svg
open output/charts/monthly_order_count.svg
open output/charts/revenue_by_city.svg
```

You can also open `output/charts/` in Finder or any browser.

## Dataset schema

Raw file: `data/raw/sales_data.csv` (UTF-8 CSV, comma-separated).

| Column | Type | Notes |
|---|---|---|
| `order_id` | text | Synthetic ID such as `ORD-2025-00001` |
| `order_date` | date | `YYYY-MM-DD`, covering 12 months of 2025 |
| `product_name` | text | 34 fictional products |
| `category` | text | 8 categories |
| `quantity` | integer | 1–5 in the generated data |
| `unit_price` | number | Indian rupees (INR) |
| `discount` | number | **Percentage from 0 to 100** |
| `payment_method` | text | UPI, Credit Card, Debit Card, Net Banking, COD or Wallet |
| `city` | text | 15 Indian cities |
| `customer_id` | text | Synthetic ID such as `CUST-0421` |
| `coupon_code` | text | Optional; blank when unused |
| `customer_rating` | integer | Optional; 1–5, blank when not rated |

The raw file has **1,525 rows**: 1,500 unique orders plus 25 intentional exact
duplicates. The generator uses `random.Random(42)`, so regenerating it with
the default settings produces the same data.

### Synthetic-data disclaimer

All rows are generated programmatically. No names, phone numbers, emails,
postal addresses or real people are present. Customer IDs are sequential
labels only. Any resemblance to a real business or customer is coincidental.

## Data-cleaning rules

The raw file deliberately contains realistic data-quality issues. Cleaning
is handled by `src/data_cleaning.py`, and every decision is written to
`data/processed/cleaning_report.csv`.

| Issue | Treatment | Rows affected |
|---|---|---|
| Exact duplicate record (all 12 columns identical) | Remove duplicate, keep first | 25 removed |
| Blank `discount` | Fill with **0%** (no discount recorded) | 15 corrected |
| Blank `city` | Fill with `Unknown`; keep the sale | 12 corrected |
| Blank product/category/payment/customer | Fill with `Unknown`; keep the sale | 0 |
| Blank `coupon_code` | Keep blank; optional field | 1,009 retained |
| Blank `customer_rating` | Keep blank; optional field | 18 retained |
| Missing critical field | Remove; date/units/revenue cannot be trusted | 0 |
| Invalid date | Remove; must parse as `YYYY-MM-DD` | 0 |
| Invalid quantity | Remove; must be a whole number from 1 to 1000 | 0 |
| Invalid price | Remove; must be positive and finite | 0 |
| Invalid discount | Remove; must be numeric and 0–100 | 0 |
| Same `order_id`, different details | Keep; may be separate line items | 0 |

**Duplicate policy:** only records where every column is identical are
removed. Rows that share an `order_id` but differ in any other field are kept,
because they may represent legitimate separate line items. Unique orders are
always counted as distinct `order_id` values, so such an order is counted once.

**Missing-discount rule:** a blank discount is treated as 0%. This avoids
inventing a discount that was never recorded. It is applied consistently in
cleaning and analysis.

Result: **1,525 raw rows → 1,500 cleaned rows**, with **1,500 unique orders**.

## Revenue and average-order-value formulas

Revenue is calculated per cleaned line item:

```
net revenue = quantity × unit_price × (1 − discount / 100)
```

- `discount` is a percentage from 0 to 100, not a fraction.
  A discount of `20` means 20% off.
- A blank discount is treated as 0%.
- All monetary values are in **INR**.

Average order value:

```
average order value = total net revenue ÷ number of unique orders
```

The denominator is distinct `order_id` count, not row count or units sold.

## Analysis produced

`src/analysis.py` calculates:

- Total net revenue after discounts.
- Gross revenue and total discount amount.
- Unique order count and total units sold.
- Average order value.
- Revenue by category, product and city.
- Top products by quantity and by revenue.
- Monthly revenue and unique order counts.
- Month-over-month revenue change in INR and percent.
- Payment-method distribution and revenue/order shares.

## Output files explained

All summary files are written under `data/processed/`.

| File | Contents |
|---|---|
| `cleaned_sales_data.csv` | Validated, deduplicated data used by all analysis |
| `cleaning_report.csv` | Every issue, count, action and rationale |
| `overall_metrics.csv` | Revenue, orders, units, AOV and date range |
| `revenue_by_category.csv` | Revenue, orders, units and share per category |
| `revenue_by_product.csv` | Revenue, orders, units and share per product |
| `revenue_by_city.csv` | Revenue per city, including `Unknown` |
| `top_products_by_quantity.csv` | Top 10 products by units sold |
| `top_products_by_revenue.csv` | Top 10 products by net revenue |
| `monthly_revenue.csv` | Monthly orders, units, revenue and MoM change |
| `payment_method_distribution.csv` | Revenue and order share by payment method |

The category, product, city, monthly and payment tables each sum to the
overall net revenue. Payment revenue and order shares each sum to 100%
(category shares may differ by 0.01% due to rounding).

### Charts

`src/visualization.py` writes five SVG charts directly, without libraries:

| File | Chart |
|---|---|
| `monthly_net_revenue.svg` | Monthly net revenue line chart |
| `revenue_by_category.svg` | Revenue by product category bar chart |
| `top_10_products_by_revenue.svg` | Top 10 products by revenue (horizontal bars) |
| `monthly_order_count.svg` | Monthly unique order count bar chart |
| `revenue_by_city.svg` | Revenue by city (horizontal bars) |

Charts include titles, labelled axes, Indian-format INR values, compact axis
labels such as `₹6.5L`, hover titles with full values, and safe handling of
empty data, missing values and long labels.

### Business report

`src/insights.py` writes `output/reports/business_insights.txt`. Every figure
comes from the current cleaned dataset. The report includes an executive
snapshot, six findings, recommendations, and data limitations. Recommendations
are framed as actions to test, not proven causes.

## Current results

Based on the generated seed-42 dataset (1,500 cleaned orders):

| Metric | Value |
|---|---|
| Total net revenue | **₹47,11,999.65** |
| Gross revenue | ₹50,94,705.00 |
| Total discount amount | ₹3,82,705.35 |
| Unique orders | **1,500** |
| Units sold | **2,825** |
| Average order value | **₹3,141.33** |
| Date range | 2025-01-01 to 2025-12-31 |

### Five key findings from the generated report

1. **Electronics was the top category** with **₹18,45,661.00** (39.17% of net
   revenue) from 352 orders and 670 units. Home & Kitchen followed at
   ₹11,09,118.15 and Fashion at ₹6,24,122.10.
2. **November 2025 was the strongest month** with **₹6,53,958.80** (13.88% of
   annual revenue), 66.54% above the average month of ₹3,92,666.64.
3. **Smartwatch led product revenue** with **₹8,01,556.80** (17.01%) from
   163 units. The top three products together contributed ₹16,34,792.75
   (34.69%).
4. **Mumbai was the leading city** with **₹6,47,269.95** (13.74%). Mumbai,
   Delhi and Bengaluru together produced 38.70% of revenue. Twelve orders had
   an unknown city (₹19,123.90), highlighting a data-capture gap.
5. **Revenue was volatile.** It rose in 7 of 11 month-over-month comparisons
   and fell in 4. The largest rise was October (+₹1,69,653.90, +44.95%); the
   largest fall was December (−₹2,19,052.10, −33.50%).

The report also notes that UPI was the largest payment method by revenue
(37.38% of revenue and 39.40% of orders).

## Testing and verification

The full standard-library test suite covers:

- Dataset generation and reproducibility.
- Exact-duplicate removal and missing-value handling.
- Invalid date, quantity, price and discount cases.
- Revenue formula, blank discounts and 100% discounts.
- Unique-order counting and average-order-value calculation.
- Monthly aggregation and month-over-month changes.
- CSV summary writing.
- SVG validity, empty data, missing values and long labels.
- Insights content and synthetic-data disclaimer.
- Pipeline stage order and generate-only-if-missing behaviour.
- Standard-library-only imports.

Run:

```bash
python3 -m unittest discover -s tests -v
```

Actual final result: **47 tests passed, 0 failures**.

Additional checks performed:

- `python3 main.py all` completed all stages successfully.
- All 10 processed CSV files exist and are non-empty.
- All five SVG files parse as valid XML and render correctly.
- The business report exists and contains six findings.
- Category, product, city and monthly revenue totals match overall revenue.
- Average order value equals net revenue divided by 1,500 unique orders.
- The raw dataset remains unchanged (MD5 `7eceff9959aa1d1ddab813b7147ba51c`)
  after running the pipeline with the raw file present.

## Limitations

- **Synthetic data:** results demonstrate method, not real market behaviour.
- **Revenue is not profit:** costs, marketing spend, refunds and returns are
  not included.
- **One year only:** long-term seasonality cannot be established from 2025
  alone.
- **Missing discounts:** treating them as 0% is a documented assumption, not
  observed truth.
- **Unknown cities:** 12 cleaned orders lack a city and are grouped as
  `Unknown`.
- **No causal analysis:** monthly and category patterns are associations.
  The dataset does not explain why changes occurred.
- **Payment mix is descriptive:** it does not prove payment preferences in a
  real population.
- No customer-level segmentation or lifetime-value analysis is implemented.

## Possible future improvements

- Add cost, refund and return fields so profitability can be analysed.
- Extend the synthetic generator to multiple years for stronger seasonality.
- Add customer repeat-purchase and cohort analysis.
- Add automated accessibility checks for the SVG charts.
- Add continuous-integration checks for tests and the full pipeline.
- Compare the workflow with a real, properly anonymised dataset if one is
  available.

## No dashboard, no dependencies

This is a command-line analytics project. It deliberately does not include a
dashboard and does not require any software beyond Python itself.
