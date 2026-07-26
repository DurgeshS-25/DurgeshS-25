#!/usr/bin/env python3
"""
render_panel.py

Renders a small terminal "system info" panel as an SVG: a header bar plus
a handful of labeled rows, each fading/typing in with a short stagger so
the panel appears to type itself out next to the portrait.

Edit ROWS below to change the content.

Usage:
    PREVIEW=1 python tools/render_panel.py   # writes a static preview frame
    python tools/render_panel.py             # writes sysinfo.svg
"""
import os
import argparse

# --- Content: edit this to describe yourself ---
HEADER = "durgesh@profile"
ROWS = [
    ("role", "Backend Engineer"),
    ("focus", "APIs, Services & Databases"),
    ("stack", "Java · Spring Boot · C# · Python"),
    ("frontend", "Angular · JavaScript"),
    ("data", "SQL · PostgreSQL · MySQL"),
    ("now", "Building scalable backend systems"),
]
# ------------------------------------------------

BG_COLOR = "#0d1117"
PANEL_COLOR = "#161b22"
BORDER_COLOR = "#30363d"
HEADER_COLOR = "#4dabf7"
LABEL_COLOR = "#7d8590"
VALUE_COLOR = "#e6edf3"
DOT_COLORS = ["#ff5f56", "#ffbd2e", "#27c93f"]  # traffic-light window dots

FONT_FAMILY = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

OUTPUT_PATH = "sysinfo.svg"


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(rows, header: str, width: int = 460, row_h: int = 34,
                stagger_ms: int = 220, fade_ms: int = 300, preview: bool = False) -> str:
    top_bar_h = 40
    pad = 20
    height = top_bar_h + pad + len(rows) * row_h + pad

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    parts.append(
        f'<style>'
        f'.lbl {{ font-family: {FONT_FAMILY}; font-size: 13px; fill: {LABEL_COLOR}; }}'
        f'.val {{ font-family: {FONT_FAMILY}; font-size: 13.5px; fill: {VALUE_COLOR}; font-weight: 600; }}'
        f'.hdr {{ font-family: {FONT_FAMILY}; font-size: 13px; fill: {HEADER_COLOR}; }}'
        f'</style>'
    )

    # Outer panel + title bar
    parts.append(
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" '
        f'fill="{PANEL_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1"/>'
    )
    parts.append(
        f'<rect x="1" y="1" width="{width - 2}" height="{top_bar_h}" rx="8" fill="{BORDER_COLOR}" opacity="0.4"/>'
    )
    for i, c in enumerate(DOT_COLORS):
        parts.append(f'<circle cx="{18 + i * 16}" cy="{top_bar_h / 2 + 1}" r="5" fill="{c}"/>')
    parts.append(f'<text x="{width / 2}" y="{top_bar_h / 2 + 5}" text-anchor="middle" class="hdr">{escape_xml(header)}</text>')

    y = top_bar_h + pad + 14
    for i, (label, value) in enumerate(rows):
        label_txt = f"{label}:".ljust(8)
        group_attrs = ""
        if not preview:
            delay = i * stagger_ms
            group_attrs = f' opacity="0"'
        parts.append(f'<g{group_attrs}>')
        if not preview:
            parts.append(
                f'  <animate attributeName="opacity" from="0" to="1" '
                f'begin="{delay}ms" dur="{fade_ms}ms" fill="freeze" />'
            )
        parts.append(f'  <text x="20" y="{y}" class="lbl">{escape_xml(label_txt)}</text>')
        parts.append(f'  <text x="100" y="{y}" class="val">{escape_xml(value)}</text>')
        parts.append("</g>")
        y += row_h

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default=OUTPUT_PATH)
    args = parser.parse_args()

    preview = os.environ.get("PREVIEW") == "1"
    svg = render_svg(ROWS, HEADER, preview=preview)

    out_path = args.output if not preview else "sysinfo.preview.svg"
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"[render_panel] Wrote {out_path}{' (preview, no animation)' if preview else ''}")


if __name__ == "__main__":
    main()
