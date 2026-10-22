"""Create five SVG charts from the Part 2 analysis using only the stdlib.

Charts:
    1. Monthly net revenue (line)
    2. Revenue by product category (vertical bars)
    3. Top 10 products by revenue (horizontal bars)
    4. Monthly order count (vertical bars)
    5. Revenue by city (horizontal bars)

SVG is written directly as XML; no plotting library, JavaScript or external
assets are used. Long labels are wrapped/truncated, empty datasets produce a
valid placeholder chart, and missing/invalid values are skipped safely.

Run:
    python3 -m src.visualization
    python3 main.py visualise
"""

from __future__ import annotations

import argparse
import html
import math
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):  # allow: python3 src/visualization.py
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import AnalysisResult, analyse_rows  # noqa: E402
from src.data_cleaning import CLEANED_PATH, load_rows  # noqa: E402

CHARTS_DIR = PROJECT_ROOT / "output" / "charts"
WIDTH = 960
FONT = "Helvetica, Arial, sans-serif"
TEXT = "#1f2937"
MUTED = "#64748b"
GRID = "#e2e8f0"
AXIS = "#94a3b8"
PALETTE = [
    "#2563eb",
    "#0ea5e9",
    "#14b8a6",
    "#22c55e",
    "#eab308",
    "#f97316",
    "#ef4444",
    "#ec4899",
    "#8b5cf6",
    "#6366f1",
]

CHART_FILES = {
    "monthly_net_revenue": "monthly_net_revenue.svg",
    "revenue_by_category": "revenue_by_category.svg",
    "top_10_products_by_revenue": "top_10_products_by_revenue.svg",
    "monthly_order_count": "monthly_order_count.svg",
    "revenue_by_city": "revenue_by_city.svg",
}


def _group_indian(digits: str) -> str:
    """Group digits Indian-style: 1234567 -> 12,34,567."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    groups.append(tail)
    return ",".join(groups)


def format_inr(value, decimals: int = 2) -> str:
    """Format a number as Indian rupees, e.g. 1845661 -> ₹18,45,661.00."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"

    sign = "-" if number < 0 else ""
    fixed = f"{abs(number):.{decimals}f}"
    integer_text, _, fraction = fixed.partition(".")
    grouped = _group_indian(integer_text)
    suffix = f".{fraction}" if decimals else ""
    return f"{sign}₹{grouped}{suffix}"


def format_compact_inr(value) -> str:
    """Compact INR for axes: ₹8L, ₹1.2Cr, ₹950."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(number):
        return "n/a"

    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1e7:
        text = f"{number / 1e7:.1f}".rstrip("0").rstrip(".") + "Cr"
    elif number >= 1e5:
        text = f"{number / 1e5:.1f}".rstrip("0").rstrip(".") + "L"
    elif number >= 1e3:
        text = f"{number / 1e3:.1f}".rstrip("0").rstrip(".") + "K"
    else:
        text = f"{number:.0f}"
    return f"{sign}₹{text}"


def _to_float(value):
    """Convert table values to floats; blank/invalid/missing -> None."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("₹", "")
    if text == "" or text.lower() in {"na", "n/a", "none", "null", "nan"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _escape(value) -> str:
    return html.escape(str(value), quote=True)


def _shorten(value, max_chars: int) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        return "Unknown"
    if len(text) <= max_chars:
        return text
    return text[: max(1, max_chars - 3)].rstrip() + "..."


def _wrap_label(value, max_chars: int, max_lines: int = 2) -> list[str]:
    text = str(value).strip() if value is not None else ""
    if not text:
        text = "Unknown"

    lines = []
    current = ""
    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _shorten(lines[-1], max_chars)
    return [_shorten(line, max_chars) for line in lines]


def _text(
    x: float,
    y: float,
    value,
    size: float = 12,
    anchor: str = "start",
    fill: str = TEXT,
    weight: str = "normal",
    extra: str = "",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
        f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
        f'font-weight="{weight}"{extra}>{_escape(value)}</text>'
    )


def _svg_document(title: str, height: int, content: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
        f'role="img">\n'
        f"<title>{_escape(title)}</title>\n"
        f'<rect x="0" y="0" width="{WIDTH}" height="{height}" fill="#ffffff"/>\n'
        f"{content}</svg>\n"
    )


def _header(title: str, subtitle: str) -> str:
    return (
        _text(32, 34, title, 21, weight="bold")
        + _text(32, 55, subtitle, 12, fill=MUTED)
        + f'<line x1="32" y1="68" x2="{WIDTH - 32}" y2="68" '
        f'stroke="{GRID}" stroke-width="1"/>'
    )


def _write_svg(path: Path, content: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _placeholder(path: Path, title: str, message: str = "No data available.") -> Path:
    height = 360
    content = _header(title, "Synthetic e-commerce dataset")
    content += _text(
        WIDTH / 2, height / 2, message, 16, anchor="middle", fill=MUTED
    )
    return _write_svg(path, _svg_document(title, height, content))


def _nice_axis(max_value: float, ticks: int = 5) -> tuple[float, float]:
    """Return (axis_max, tick_step) rounded to pleasant numbers."""
    if max_value <= 0 or not math.isfinite(max_value):
        return 1.0, 1.0
    raw_step = max_value / ticks
    exponent = math.floor(math.log10(raw_step))
    magnitude = 10**exponent
    fraction = raw_step / magnitude
    if fraction <= 1:
        nice = 1
    elif fraction <= 2:
        nice = 2
    elif fraction <= 2.5:
        nice = 2.5
    elif fraction <= 5:
        nice = 5
    else:
        nice = 10
    step = nice * magnitude
    return float(math.ceil(max_value / step) * step), float(step)


def _month_label(value) -> str:
    text = str(value or "").strip()
    try:
        return datetime.strptime(text, "%Y-%m").strftime("%b %y")
    except ValueError:
        return _shorten(text, 8)


def _vertical_grid(
    left: float,
    right: float,
    top: float,
    bottom: float,
    axis_max: float,
    step: float,
    ticks: int,
    formatter,
) -> tuple[list[str], str]:
    parts = []
    labels = []
    for index in range(ticks + 1):
        value = step * index
        y = bottom - (value / axis_max) * (bottom - top)
        parts.append(
            f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{right:.1f}" '
            f'y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            _text(left - 10, y + 4, formatter(value), 11, anchor="end", fill=MUTED)
        )
        labels.append(str(index))
    return parts, "".join(labels)


def create_monthly_revenue_chart(rows: list[dict], output_path: Path) -> Path:
    title = "Monthly Net Revenue"
    points = [
        (_month_label(row.get("month")), _to_float(row.get("net_revenue_inr")))
        for row in rows
    ]
    valid = [value for _, value in points if value is not None]
    if not points or not valid:
        return _placeholder(output_path, title)

    height = 520
    left, right, top, bottom = 82, 34, 96, 66
    plot_w = WIDTH - left - right
    plot_h = height - top - bottom
    axis_max, step = _nice_axis(max(valid))
    ticks = max(1, int(round(axis_max / step)))

    content = _header(
        title, "Synthetic e-commerce dataset | Net revenue after discounts (INR)"
    )

    grid, _ = _vertical_grid(
        left, WIDTH - right, top, top + plot_h, axis_max, step, ticks, format_compact_inr
    )
    content += "".join(grid)
    content += (
        f'<line x1="{left}" y1="{top + plot_h}" x2="{WIDTH - right}" '
        f'y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>'
    )

    count = len(points)
    spacing = plot_w / (count - 1) if count > 1 else 0
    positions = [
        left + (spacing * index if count > 1 else plot_w / 2)
        for index in range(count)
    ]
    coordinates = []
    for (label, value), x in zip(points, positions):
        if value is None:
            coordinates.append((label, x, None, None))
        else:
            y = top + plot_h - (value / axis_max) * plot_h
            coordinates.append((label, x, y, value))

    # Draw line segments that do not cross missing values.
    segment = []
    segments = []
    for _, x, y, value in coordinates:
        if value is None:
            if segment:
                segments.append(segment)
                segment = []
        else:
            segment.append((x, y))
    if segment:
        segments.append(segment)

    for points_in_segment in segments:
        if len(points_in_segment) > 1:
            point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points_in_segment)
            content += (
                f'<polyline points="{point_text}" fill="none" stroke="#2563eb" '
                f'stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
            )

    for label, x, y, value in coordinates:
        content += _text(x, top + plot_h + 22, label, 11, anchor="middle", fill=MUTED)
        if value is None:
            content += _text(
                x, top + plot_h - 8, "n/a", 10, anchor="middle", fill=MUTED
            )
            continue
        content += (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#ffffff" '
            f'stroke="#2563eb" stroke-width="2.5">'
            f"<title>{_escape(label)}: {_escape(format_inr(value))}</title></circle>"
        )
        content += _text(
            x, max(top + 12, y - 10), format_compact_inr(value), 10,
            anchor="middle", fill="#1d4ed8"
        )

    content += _text(
        left + plot_w / 2, height - 18, "Month", 12, anchor="middle", fill=MUTED
    )
    content += _text(
        22, top + plot_h / 2, "Net revenue (INR)", 12, anchor="middle",
        fill=MUTED, extra=f' transform="rotate(-90 22 {top + plot_h / 2:.1f})"'
    )
    content += _text(
        WIDTH - right, height - 12, "Source: synthetic dataset", 10,
        anchor="end", fill="#94a3b8"
    )
    return _write_svg(output_path, _svg_document(title, height, content))


def _vertical_bar_chart(
    rows: list[dict],
    label_key: str,
    value_key: str,
    output_path: Path,
    title: str,
    subtitle: str,
    axis_title: str,
    value_formatter,
    color: str = "#2563eb",
    use_palette: bool = False,
) -> Path:
    entries = [
        (
            str(row.get(label_key) or "Unknown"),
            _to_float(row.get(value_key)),
        )
        for row in rows
    ]
    valid = [value for _, value in entries if value is not None]
    if not entries or not valid:
        return _placeholder(output_path, title)

    height = 540
    left, right, top, bottom = 82, 34, 96, 96
    plot_w = WIDTH - left - right
    plot_h = height - top - bottom
    axis_max, step = _nice_axis(max(valid))
    ticks = max(1, int(round(axis_max / step)))

    content = _header(title, subtitle)
    grid, _ = _vertical_grid(
        left, WIDTH - right, top, top + plot_h, axis_max, step, ticks, format_compact_inr
    )
    content += "".join(grid)
    content += (
        f'<line x1="{left}" y1="{top + plot_h}" x2="{WIDTH - right}" '
        f'y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>'
    )

    count = len(entries)
    slot = plot_w / count
    bar_width = min(70.0, slot * 0.62)
    label_chars = max(8, min(18, int(slot / 6.5)))

    for index, (label, value) in enumerate(entries):
        center = left + slot * (index + 0.5)
        lines = _wrap_label(label, label_chars, max_lines=2)
        for line_index, line in enumerate(lines):
            content += _text(
                center,
                top + plot_h + 22 + line_index * 14,
                line,
                10,
                anchor="middle",
                fill=MUTED,
            )

        if value is None:
            content += _text(
                center, top + plot_h - 8, "n/a", 10, anchor="middle", fill=MUTED
            )
            continue

        bar_height = (value / axis_max) * plot_h
        bar_color = PALETTE[index % len(PALETTE)] if use_palette else color
        content += (
            f'<rect x="{center - bar_width / 2:.1f}" '
            f'y="{top + plot_h - bar_height:.1f}" width="{bar_width:.1f}" '
            f'height="{max(bar_height, 0):.1f}" fill="{bar_color}" rx="3">'
            f"<title>{_escape(label)}: {_escape(format_inr(value))}</title></rect>"
        )
        content += _text(
            center,
            max(top + 12, top + plot_h - bar_height - 8),
            value_formatter(value),
            10,
            anchor="middle",
            fill=TEXT,
        )

    content += _text(
        left + plot_w / 2, height - 18, axis_title, 12, anchor="middle", fill=MUTED
    )
    content += _text(
        22, top + plot_h / 2, "Net revenue (INR)", 12, anchor="middle",
        fill=MUTED, extra=f' transform="rotate(-90 22 {top + plot_h / 2:.1f})"'
    )
    content += _text(
        WIDTH - right, height - 12, "Source: synthetic dataset", 10,
        anchor="end", fill="#94a3b8"
    )
    return _write_svg(output_path, _svg_document(title, height, content))


def create_category_revenue_chart(rows: list[dict], output_path: Path) -> Path:
    return _vertical_bar_chart(
        rows=rows,
        label_key="category",
        value_key="net_revenue_inr",
        output_path=output_path,
        title="Revenue by Product Category",
        subtitle="Synthetic e-commerce dataset | Net revenue after discounts (INR)",
        axis_title="Product category",
        value_formatter=format_compact_inr,
        use_palette=True,
    )


def create_monthly_orders_chart(rows: list[dict], output_path: Path) -> Path:
    title = "Monthly Order Count"
    entries = [
        (_month_label(row.get("month")), _to_float(row.get("orders")))
        for row in rows
    ]
    valid = [value for _, value in entries if value is not None]
    if not entries or not valid:
        return _placeholder(output_path, title)

    height = 500
    left, right, top, bottom = 82, 34, 96, 64
    plot_w = WIDTH - left - right
    plot_h = height - top - bottom
    axis_max, step = _nice_axis(max(valid))
    ticks = max(1, int(round(axis_max / step)))

    content = _header(
        title, "Synthetic e-commerce dataset | Unique orders per month"
    )
    grid = []
    for index in range(ticks + 1):
        value = step * index
        y = top + plot_h - (value / axis_max) * plot_h
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{WIDTH - right}" '
            f'y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        grid.append(
            _text(
                left - 10, y + 4, f"{int(round(value))}", 11,
                anchor="end", fill=MUTED
            )
        )
    content += "".join(grid)
    content += (
        f'<line x1="{left}" y1="{top + plot_h}" x2="{WIDTH - right}" '
        f'y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>'
    )

    count = len(entries)
    slot = plot_w / count
    bar_width = min(62.0, slot * 0.58)
    for index, (label, value) in enumerate(entries):
        center = left + slot * (index + 0.5)
        content += _text(
            center, top + plot_h + 22, label, 11, anchor="middle", fill=MUTED
        )
        if value is None:
            content += _text(
                center, top + plot_h - 8, "n/a", 10, anchor="middle", fill=MUTED
            )
            continue
        bar_height = (value / axis_max) * plot_h
        content += (
            f'<rect x="{center - bar_width / 2:.1f}" '
            f'y="{top + plot_h - bar_height:.1f}" width="{bar_width:.1f}" '
            f'height="{max(bar_height, 0):.1f}" fill="#f59e0b" rx="3">'
            f"<title>{_escape(label)}: {int(round(value))} orders</title></rect>"
        )
        content += _text(
            center,
            max(top + 12, top + plot_h - bar_height - 8),
            f"{int(round(value))}",
            10,
            anchor="middle",
            fill=TEXT,
        )

    content += _text(
        left + plot_w / 2, height - 18, "Month", 12, anchor="middle", fill=MUTED
    )
    content += _text(
        22, top + plot_h / 2, "Unique orders", 12, anchor="middle",
        fill=MUTED, extra=f' transform="rotate(-90 22 {top + plot_h / 2:.1f})"'
    )
    content += _text(
        WIDTH - right, height - 12, "Source: synthetic dataset", 10,
        anchor="end", fill="#94a3b8"
    )
    return _write_svg(output_path, _svg_document(title, height, content))


def _horizontal_bar_chart(
    rows: list[dict],
    label_key: str,
    value_key: str,
    output_path: Path,
    title: str,
    subtitle: str,
    axis_title: str,
    max_bars: int | None = None,
    use_palette: bool = False,
    color: str = "#0f766e",
) -> Path:
    entries = [
        (
            str(row.get(label_key) or "Unknown"),
            _to_float(row.get(value_key)),
        )
        for row in rows
    ]
    if max_bars is not None:
        entries = entries[:max_bars]
    valid = [value for _, value in entries if value is not None]
    if not entries or not valid:
        return _placeholder(output_path, title)

    height = max(380, 110 + len(entries) * 38)
    left, right, top, bottom = 280, 108, 96, 56
    plot_w = WIDTH - left - right
    plot_bottom = height - bottom
    plot_h = plot_bottom - top
    axis_max, step = _nice_axis(max(valid))
    ticks = max(1, int(round(axis_max / step)))

    content = _header(title, subtitle)

    for index in range(ticks + 1):
        value = step * index
        x = left + (value / axis_max) * plot_w
        content += (
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
            f'y2="{plot_bottom}" stroke="{GRID}" stroke-width="1"/>'
        )
        content += _text(
            x, plot_bottom + 18, format_compact_inr(value), 10,
            anchor="middle", fill=MUTED
        )
    content += (
        f'<line x1="{left}" y1="{plot_bottom}" x2="{left + plot_w}" '
        f'y2="{plot_bottom}" stroke="{AXIS}" stroke-width="1"/>'
    )

    row_height = plot_h / len(entries)
    bar_height = min(22.0, row_height * 0.62)
    for index, (label, value) in enumerate(entries):
        center = top + row_height * (index + 0.5)
        content += _text(
            left - 12, center + 4, _shorten(label, 34), 11.5,
            anchor="end", fill=TEXT
        )
        if value is None:
            content += _text(
                left + 8, center + 4, "n/a", 10, anchor="start", fill=MUTED
            )
            continue

        bar_width = (value / axis_max) * plot_w
        fill = PALETTE[index % len(PALETTE)] if use_palette else color
        content += (
            f'<rect x="{left}" y="{center - bar_height / 2:.1f}" '
            f'width="{max(bar_width, 0):.1f}" height="{bar_height:.1f}" '
            f'fill="{fill}" rx="3">'
            f"<title>{_escape(label)}: {_escape(format_inr(value))}</title></rect>"
        )
        content += _text(
            left + bar_width + 8, center + 4, format_compact_inr(value),
            10, anchor="start", fill=TEXT
        )

    content += _text(
        left + plot_w / 2, height - 16, axis_title, 12,
        anchor="middle", fill=MUTED
    )
    content += _text(
        WIDTH - right, height - 16, "Source: synthetic dataset", 10,
        anchor="end", fill="#94a3b8"
    )
    return _write_svg(output_path, _svg_document(title, height, content))


def create_top_products_chart(rows: list[dict], output_path: Path) -> Path:
    return _horizontal_bar_chart(
        rows=rows,
        label_key="product_name",
        value_key="net_revenue_inr",
        output_path=output_path,
        title="Top 10 Products by Revenue",
        subtitle="Synthetic e-commerce dataset | Net revenue after discounts | Top 10",
        axis_title="Net revenue (INR)",
        max_bars=10,
        use_palette=True,
    )


def create_city_revenue_chart(rows: list[dict], output_path: Path) -> Path:
    return _horizontal_bar_chart(
        rows=rows,
        label_key="city",
        value_key="net_revenue_inr",
        output_path=output_path,
        title="Revenue by City",
        subtitle="Synthetic e-commerce dataset | Net revenue after discounts (INR)",
        axis_title="Net revenue (INR)",
        color="#0f766e",
    )


def generate_charts(
    result: AnalysisResult, output_dir: Path = CHARTS_DIR
) -> list[Path]:
    """Generate all five charts from an existing analysis result."""
    output_dir = Path(output_dir)
    tables = result.tables
    return [
        create_monthly_revenue_chart(
            tables.get("monthly_revenue", []),
            output_dir / CHART_FILES["monthly_net_revenue"],
        ),
        create_category_revenue_chart(
            tables.get("revenue_by_category", []),
            output_dir / CHART_FILES["revenue_by_category"],
        ),
        create_top_products_chart(
            tables.get("top_products_by_revenue", []),
            output_dir / CHART_FILES["top_10_products_by_revenue"],
        ),
        create_monthly_orders_chart(
            tables.get("monthly_revenue", []),
            output_dir / CHART_FILES["monthly_order_count"],
        ),
        create_city_revenue_chart(
            tables.get("revenue_by_city", []),
            output_dir / CHART_FILES["revenue_by_city"],
        ),
    ]


def run_visualizations(
    input_path: Path = CLEANED_PATH,
    output_dir: Path = CHARTS_DIR,
    verbose: bool = True,
) -> list[Path]:
    """Load cleaned data, analyse it, and write all five SVG charts."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found: {input_path}\n"
            "Run: python3 main.py all"
        )

    result = analyse_rows(load_rows(input_path))
    paths = generate_charts(result, output_dir)
    if verbose:
        print("Charts generated.")
        for path in paths:
            print(f"  {path}")
    return paths


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SVG charts from the cleaned sales data."
    )
    parser.add_argument("--input", type=Path, default=CLEANED_PATH)
    parser.add_argument("--output-dir", type=Path, default=CHARTS_DIR)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_visualizations(args.input, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
