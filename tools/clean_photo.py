#!/usr/bin/env python3
"""
clean_photo.py

Prepares a source photo for ASCII-portrait conversion:
  1. Cuts the background out (rembg) so only the subject remains.
  2. Evens out lighting with CLAHE (adaptive histogram equalization).
  3. Composites the result onto a plain white canvas so the background
     falls at the *light* end of the character ramp instead of the dark end.

Usage:
    python tools/clean_photo.py my-photo.jpg
    # writes assets/photo-ready.png

If rembg isn't installed (it's a heavy optional dependency), the script
falls back to skipping background removal and just runs CLAHE + white
padding, so you can still iterate without the full art requirements
installed.
"""
import sys
import os
import argparse

import numpy as np
import cv2
from PIL import Image

OUTPUT_PATH = "assets/photo-ready.png"


def remove_background(pil_img: Image.Image) -> Image.Image:
    """Try to cut the background with rembg. Falls back to a no-op with a
    warning if rembg isn't available in this environment."""
    try:
        from rembg import remove
    except ImportError:
        print(
            "[clean_photo] rembg not installed — skipping background removal. "
            "Install tools/requirements-art.txt for full quality.",
            file=sys.stderr,
        )
        return pil_img.convert("RGBA")

    result = remove(pil_img)
    return result.convert("RGBA")


def apply_clahe(pil_img: Image.Image) -> Image.Image:
    """Even out lighting so shadow/highlight detail survives the
    downscale-to-ASCII step later. Operates on the L channel in LAB space
    so color isn't distorted."""
    rgba = np.array(pil_img)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3] if rgba.shape[2] == 4 else None

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_eq = clahe.apply(l_channel)

    lab_eq = cv2.merge((l_eq, a_channel, b_channel))
    rgb_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2RGB)

    if alpha is not None:
        rgba_eq = np.dstack([rgb_eq, alpha])
        return Image.fromarray(rgba_eq, mode="RGBA")
    return Image.fromarray(rgb_eq, mode="RGB")


def composite_on_white(pil_img: Image.Image) -> Image.Image:
    """Flatten onto a solid white canvas so transparent/cut background
    pixels read as 'empty' (light) rather than 'dense' (dark) once they
    get mapped to ASCII glyphs."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    white_bg = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, pil_img)
    return composited.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo", help="Path to the source photo")
    parser.add_argument(
        "-o", "--output", default=OUTPUT_PATH, help=f"Output path (default: {OUTPUT_PATH})"
    )
    parser.add_argument(
        "--max-dim", type=int, default=900,
        help="Longest edge to downscale to before processing (default: 900)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.photo):
        print(f"[clean_photo] Input photo not found: {args.photo}", file=sys.stderr)
        sys.exit(1)

    img = Image.open(args.photo).convert("RGB")

    # Keep things fast — we don't need a huge source image for an ASCII grid.
    img.thumbnail((args.max_dim, args.max_dim), Image.LANCZOS)

    print("[clean_photo] Removing background...")
    img = remove_background(img)

    print("[clean_photo] Evening out lighting (CLAHE)...")
    img = apply_clahe(img)

    print("[clean_photo] Compositing onto white canvas...")
    img = composite_on_white(img)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    img.save(args.output)
    print(f"[clean_photo] Wrote {args.output}")


if __name__ == "__main__":
    main()
