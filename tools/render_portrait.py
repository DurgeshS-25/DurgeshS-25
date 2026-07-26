#!/usr/bin/env python3
"""
render_portrait.py

Downscales assets/photo-ready.png (see clean_photo.py) to a small character
grid, maps brightness to a glyph ramp, and renders the whole thing as a
single monochrome SVG that draws itself in row-by-row, top to bottom.

Usage:
    python tools/render_portrait.py
    # writes portrait.svg
"""
import argparse
import numpy as np
from PIL import Image

# Left = light/empty, right = dense/dark. Deliberately softer than the
# usual "@%#" block ramp so it reads more like a sketch than a block print.
GLYPHS = " '.,:;~+*xXO#"

ACCENT_COLOR = "#4dabf7"
BG_COLOR = "#0d1117"          # matches GitHub's dark-mode canvas
FONT_FAMILY = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

INPUT_PATH = "assets/photo-ready.png"
OUTPUT_PATH = "portrait.svg"


def image_to_grid(path: str, cols: int, char_aspect: float = 2.0) -> list[str]:
    """Downscale to a `cols`-wide character grid and map brightness -> glyph.

    char_aspect compensates for monospace characters being taller than they
    are wide, so the portrait doesn't come out squashed.
    """
    img = Image.open(path).convert("L")
    w, h = img.size
    rows = max(1, int((h / w) * cols / char_aspect))
    img = img.resize((cols, rows), Image.LANCZOS)

    arr = np.array(img).astype(np.float32) / 255.0  # 0=black .. 1=white
    ramp = GLYPHS
    n = len(ramp) - 1

    lines = []
    for row in arr:
        # Invert: bright pixel (close to 1) -> low-density glyph (index 0)
        idx = ((1.0 - row) * n).round().astype(int)
        idx = np.clip(idx, 0, n)
        lines.append("".join(ramp[i] for i in idx))
    return lines


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_svg(rows: list[str], cell_w: float = 9.0, cell_h: float = 16.0,
                stagger_ms: int = 40, draw_ms: int = 500) -> str:
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows) if rows else 0

    width = n_cols * cell_w + 20
    height = n_rows * cell_h + 20

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>')
    parts.append(
        f'<style>text {{ font-family: {FONT_FAMILY}; font-size: {cell_h * 0.9:.1f}px; '
        f'fill: {ACCENT_COLOR}; white-space: pre; }}</style>'
    )

    total_duration_ms = stagger_ms * n_rows + draw_ms

    for i, row in enumerate(rows):
        y = 15 + i * cell_h
        row_id = f"row{i}"
        clip_id = f"clip{i}"
        delay = i * stagger_ms

        # Clip rect animates its width from 0 -> full text width, revealing
        # the row left-to-right; rows are staggered top-to-bottom.
        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(
            f'  <rect x="10" y="{y - cell_h * 0.8:.1f}" width="0" height="{cell_h:.1f}">'
        )
        parts.append(
            f'    <animate attributeName="width" from="0" to="{n_cols * cell_w:.0f}" '
            f'begin="{delay}ms" dur="{draw_ms}ms" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1" />'
        )
        parts.append("  </rect>")
        parts.append("</clipPath>")

        safe_row = escape_xml(row)
        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(f'  <text x="10" y="{y:.1f}">{safe_row}</text>')
        parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", default=INPUT_PATH)
    parser.add_argument("-o", "--output", default=OUTPUT_PATH)
    parser.add_argument("--cols", type=int, default=90, help="Character columns (default: 90)")
    args = parser.parse_args()

    rows = image_to_grid(args.input, cols=args.cols)
    svg = render_svg(rows)

    with open(args.output, "w") as f:
        f.write(svg)
    print(f"[render_portrait] Wrote {args.output} ({len(rows)} rows x {args.cols} cols)")


if __name__ == "__main__":
    main()
