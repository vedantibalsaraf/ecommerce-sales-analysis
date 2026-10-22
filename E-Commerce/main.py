"""Entry point for the E-commerce Sales Data Analysis project.

All stages are implemented: synthetic data generation, cleaning and
validation, sales analysis, five SVG charts, and a business insights report.

Usage (from the project root):
    python3 main.py              # project status and instructions
    python3 main.py generate     # create data/raw/sales_data.csv
    python3 main.py check        # validate the raw dataset
    python3 main.py clean        # write data/processed/cleaned_sales_data.csv
    python3 main.py analyse      # calculate and write summary tables
    python3 main.py visualise    # create SVG charts + business insights
    python3 main.py all          # complete pipeline (generates data if needed)
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = PROJECT_ROOT / "data" / "raw" / "sales_data.csv"
GENERATOR = PROJECT_ROOT / "data" / "generate_data.py"
CLEANED_FILE = PROJECT_ROOT / "data" / "processed" / "cleaned_sales_data.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHARTS_DIR = PROJECT_ROOT / "output" / "charts"
INSIGHTS_FILE = PROJECT_ROOT / "output" / "reports" / "business_insights.txt"

REQUIRED_COLUMNS = [
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
]


def generate() -> int:
    if not GENERATOR.exists():
        print(f"Generator not found: {GENERATOR}")
        return 1
    print(f"Running generator with: {sys.executable}")
    return subprocess.run([sys.executable, str(GENERATOR)], check=False).returncode


def check() -> int:
    if not DATA_FILE.exists():
        print(f"Dataset not found: {DATA_FILE}")
        print("Run: python3 main.py generate")
        return 1

    with DATA_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = list(reader)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing_columns:
        print(f"Missing required columns: {', '.join(missing_columns)}")
        return 1

    if len(rows) < 1000:
        print(f"Only {len(rows)} data rows found; at least 1,000 are required.")
        return 1

    months = {row["order_date"][:7] for row in rows if row["order_date"]}
    print("Dataset check passed.")
    print(f"  File:        {DATA_FILE}")
    print(f"  Data rows:   {len(rows)}")
    print(f"  Columns:     {len(header)} ({', '.join(header)})")
    print(f"  Months:      {len(months)}")
    return 0


def ensure_raw_dataset() -> int:
    """Create the synthetic dataset only when the raw CSV is missing."""
    if DATA_FILE.exists():
        return 0
    print(f"Raw dataset not found: {DATA_FILE}")
    print("Generating the synthetic dataset first...")
    return generate()


def clean() -> int:
    from src.data_cleaning import run_cleaning

    run_cleaning()
    return 0


def analyse() -> int:
    from src.analysis import run_analysis

    run_analysis()
    return 0


def _generate_part3(result):
    from src.insights import write_insights
    from src.visualization import generate_charts

    charts = generate_charts(result, CHARTS_DIR)
    report = write_insights(result, INSIGHTS_FILE)
    print(f"Charts generated: {len(charts)} SVG files in {CHARTS_DIR}")
    for path in charts:
        print(f"  {path.name}")
    print(f"Business insights: {report}")
    return charts, report


def visualise() -> int:
    from src.analysis import analyse_rows
    from src.data_cleaning import load_rows

    if not CLEANED_FILE.exists():
        print(f"Cleaned data not found: {CLEANED_FILE}")
        print("Run: python3 main.py all")
        return 1

    result = analyse_rows(load_rows(CLEANED_FILE))
    _generate_part3(result)
    return 0


def run_all() -> int:
    from src.analysis import run_analysis
    from src.data_cleaning import run_cleaning

    generation_status = ensure_raw_dataset()
    if generation_status != 0:
        print("Dataset generation failed; pipeline stopped.")
        return generation_status
    if not DATA_FILE.exists():
        print(f"Dataset still missing after generation: {DATA_FILE}")
        return 1

    report = run_cleaning()
    if report.output_rows == 0:
        print("Cleaning produced no usable rows; analysis skipped.")
        return 1
    print()
    result = run_analysis()
    print()
    _generate_part3(result)
    return 0


def show_status() -> int:
    print("E-commerce Sales Data Analysis Using Python")
    print("Part 1: synthetic data generation")
    print("Part 2: data cleaning and analysis")
    print("Part 3: SVG charts and business insights")
    print("Part 4: final pipeline and documentation\n")

    if DATA_FILE.exists():
        with DATA_FILE.open(newline="", encoding="utf-8-sig") as handle:
            row_count = sum(1 for _ in handle) - 1
        print(f"Raw dataset:  {DATA_FILE} ({row_count} data rows)")
    else:
        print("Raw dataset:  not generated yet")

    if CLEANED_FILE.exists():
        with CLEANED_FILE.open(newline="", encoding="utf-8-sig") as handle:
            cleaned_count = sum(1 for _ in handle) - 1
        processed_csvs = len(list(PROCESSED_DIR.glob("*.csv")))
        print(f"Cleaned data: {CLEANED_FILE} ({cleaned_count} data rows)")
        print(f"Processed CSV files: {processed_csvs}")
    else:
        print("Cleaned data: not created yet")

    chart_count = len(list(CHARTS_DIR.glob("*.svg")))
    print(f"SVG charts:   {chart_count}")
    print(f"Insights:     {'yes' if INSIGHTS_FILE.exists() else 'not generated yet'}")

    print("\nCommands:")
    print("  python3 main.py generate   Generate data/raw/sales_data.csv")
    print("  python3 main.py check      Validate the raw dataset")
    print("  python3 main.py clean      Clean the raw dataset")
    print("  python3 main.py analyse    Calculate summary tables")
    print("  python3 main.py visualise  Generate charts + insights report")
    print("  python3 main.py all        Run the complete pipeline")
    print("  python3 -m unittest discover -s tests -v")
    print("\nAll four project stages are complete.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "status",
            "generate",
            "check",
            "clean",
            "analyse",
            "analyze",
            "visualise",
            "visualize",
            "all",
        ],
        default="status",
        help="Action to perform (default: status).",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            return generate()
        if args.command == "check":
            return check()
        if args.command == "clean":
            return clean()
        if args.command in {"analyse", "analyze"}:
            return analyse()
        if args.command in {"visualise", "visualize"}:
            return visualise()
        if args.command == "all":
            return run_all()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    return show_status()


if __name__ == "__main__":
    raise SystemExit(main())
