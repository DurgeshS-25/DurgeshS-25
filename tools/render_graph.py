#!/usr/bin/env python3
"""
render_graph.py

Reads assets/contributions.json (see pull_contributions.py) and draws the
~52 weeks x 7 days as rounded squares in a custom color ramp — matching the
portrait's accent color rather than GitHub's usual greens. Squares animate
in column-by-column (by week) rather than the more common row-by-row wipe,
plus a small legend and one-line stats summary underneath.

Usage:
    python tools/render_graph.py
    # writes graph.svg
"""
import argparse
import datetime
import json

INPUT_PATH = "assets/contributions.json"
OUTPUT_PATH = "graph.svg"

# index 0 = no activity, index 4 = top activity tier
LEVELS = ["#1a1a2e", "#16537e", "#1c7ed6", "#4dabf7", "#a5d8ff"]
BG_COLOR = "#0d1117"
TEXT_COLOR = "#7d8590"
STRONG_TEXT_COLOR = "#e6edf3"
FONT_FAMILY = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

CELL = 11
GAP = 3
MARGIN = 20
LEGEND_H = 20
STATS_H = 24


def level_for_count(count: int, thresholds=(0, 2, 5, 9)) -> int:
    """Bucket a raw count into one of 5 tiers (0..4)."""
    if count <= thresholds[0]:
        return 0
    if count <= thresholds[1]:
        return 1
    if count <= thresholds[2]:
        return 2
    if count <= thresholds[3]:
        return 3
    return 4


def build_week_columns(days: dict) -> list[list[tuple[datetime.date, int]]]:
    """Groups {date: count} into a list of weeks (Sun-start columns), each
    a list of up to 7 (date, count) tuples, oldest week first."""
    dated = sorted(
        (datetime.date.fromisoformat(d), c) for d, c in days.items()
    )
    if not dated:
        return []

    first_date = dated[0][0]
    # Back up to the preceding Sunday so every column has a fixed Sun..Sat shape.
    first_sunday = first_date - datetime.timedelta(days=(first_date.weekday() + 1) % 7)

    lookup = dict(dated)
    last_date = dated[-1][0]

    weeks = []
    cur = first_sunday
    week: list[tuple[datetime.date, int]] = []
    while cur <= last_date:
        count = lookup.get(cur, 0)
        week.append((cur, count))
        if len(week) == 7:
            weeks.append(week)
            week = []
        cur += datetime.timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append((cur, 0))
            cur += datetime.timedelta(days=1)
        weeks.append(week)

    return weeks


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(weeks: list[list[tuple[datetime.date, int]]], summary: dict,
                stagger_ms: int = 25, fade_ms: int = 220) -> str:
    n_weeks = len(weeks)
    grid_w = n_weeks * (CELL + GAP)
    grid_h = 7 * (CELL + GAP)

    width = grid_w + MARGIN * 2
    height = grid_h + MARGIN * 2 + LEGEND_H + STATS_H

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>')
    parts.append(
        f'<style>'
        f'text {{ font-family: {FONT_FAMILY}; }}'
        f'.stat {{ font-size: 12px; fill: {TEXT_COLOR}; }}'
        f'.stat-strong {{ font-size: 12px; fill: {STRONG_TEXT_COLOR}; font-weight: 600; }}'
        f'</style>'
    )

    # Grid, animated column by column (by week)
    for wi, week in enumerate(weeks):
        x = MARGIN + wi * (CELL + GAP)
        delay = wi * stagger_ms
        for di, (date, count) in enumerate(week):
            y = MARGIN + di * (CELL + GAP)
            level = level_for_count(count)
            color = LEVELS[level]
            title = f"{date.isoformat()}: {count} contribution{'s' if count != 1 else ''}"
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{color}" opacity="0">'
                f'<title>{escape_xml(title)}</title>'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{delay}ms" dur="{fade_ms}ms" fill="freeze" />'
                f'</rect>'
            )

    # Legend, bottom-left, appears after the grid finishes drawing
    legend_delay = n_weeks * stagger_ms + fade_ms
    legend_y = MARGIN + grid_h + 14
    lx = MARGIN
    parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" '
                  f'begin="{legend_delay}ms" dur="300ms" fill="freeze" />')
    parts.append(f'<text x="{lx}" y="{legend_y + 9}" class="stat">Less</text>')
    lx += 38
    for color in LEVELS:
        parts.append(f'<rect x="{lx}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')
        lx += CELL + GAP
    parts.append(f'<text x="{lx + 4}" y="{legend_y + 9}" class="stat">More</text>')
    parts.append("</g>")

    # Stats line, bottom, appears just after the legend
    stats_delay = legend_delay + 200
    stats_y = legend_y + LEGEND_H
    stats_text = (
        f"{summary.get('total_contributions', 0)} contributions in the last year  ·  "
        f"current streak {summary.get('current_streak', 0)}d  ·  "
        f"longest streak {summary.get('longest_streak', 0)}d  ·  "
        f"busiest on {summary.get('busiest_weekday', 'n/a')}"
    )
    parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" '
                  f'begin="{stats_delay}ms" dur="300ms" fill="freeze" />')
    parts.append(f'<text x="{MARGIN}" y="{stats_y}" class="stat-strong">{escape_xml(stats_text)}</text>')
    parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", default=INPUT_PATH)
    parser.add_argument("-o", "--output", default=OUTPUT_PATH)
    args = parser.parse_args()

    with open(args.input) as f:
        summary = json.load(f)

    weeks = build_week_columns(summary.get("days", {}))
    svg = render_svg(weeks, summary)

    with open(args.output, "w") as f:
        f.write(svg)
    print(f"[render_graph] Wrote {args.output} ({len(weeks)} weeks)")


if __name__ == "__main__":
    main()
