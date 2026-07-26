#!/usr/bin/env python3
"""
render_stats.py

Replaces the github-readme-stats.vercel.app badges (stats + top languages)
with a self-hosted equivalent, rendered the same way as graph.svg /
portrait.svg / sysinfo.svg: pull public data from GitHub's REST API (no
token needed for public repos), then draw a terminal-styled SVG.

GitHub's unauthenticated API allows 60 requests/hour per IP, which is
plenty for a once-a-day refresh (this script makes ~1 + N calls, where N
is your public repo count).

Usage:
    python tools/render_stats.py <username>
    # writes assets/stats.json and stats.svg
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BG_COLOR = "#0d1117"
PANEL_COLOR = "#161b22"
BORDER_COLOR = "#30363d"
HEADER_COLOR = "#4dabf7"
LABEL_COLOR = "#7d8590"
VALUE_COLOR = "#e6edf3"
BAR_COLORS = ["#4dabf7", "#1c7ed6", "#16537e", "#a5d8ff", "#7d8590", "#30363d"]
FONT_FAMILY = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

API_ROOT = "https://api.github.com"
OUTPUT_JSON = "assets/stats.json"
OUTPUT_SVG = "stats.svg"


def api_get(path: str):
    url = f"{API_ROOT}{path}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "profile-readme-bot",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[render_stats] GitHub API error for {path}: {e.code}", file=sys.stderr)
        raise


def gather_stats(username: str) -> dict:
    repos = []
    page = 1
    while True:
        batch = api_get(f"/users/{username}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)
    public_repos = len(repos)

    lang_bytes: dict[str, int] = {}
    for r in repos:
        if r.get("fork"):
            continue  # skip forked repos, only count your own work
        owner = r["owner"]["login"]
        name = r["name"]
        try:
            langs = api_get(f"/repos/{owner}/{name}/languages")
        except Exception:
            continue
        for lang, n_bytes in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + n_bytes

    total_bytes = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:6]
    top_langs_pct = [(lang, round(100 * n / total_bytes, 1)) for lang, n in top_langs]

    return {
        "username": username,
        "public_repos": public_repos,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "top_languages": top_langs_pct,
    }


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(stats: dict, width: int = 460) -> str:
    langs = stats["top_languages"]
    row_h = 26
    header_h = 40
    stat_row_h = 30
    pad = 20

    height = header_h + pad + stat_row_h + pad + len(langs) * row_h + pad

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    parts.append(
        f'<style>'
        f'text {{ font-family: {FONT_FAMILY}; }}'
        f'.hdr {{ font-size: 13px; fill: {HEADER_COLOR}; }}'
        f'.lbl {{ font-size: 12.5px; fill: {LABEL_COLOR}; }}'
        f'.val {{ font-size: 12.5px; fill: {VALUE_COLOR}; font-weight: 600; }}'
        f'</style>'
    )
    parts.append(
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" '
        f'fill="{PANEL_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1"/>'
    )
    parts.append(
        f'<rect x="1" y="1" width="{width - 2}" height="{header_h}" rx="8" fill="{BORDER_COLOR}" opacity="0.4"/>'
    )
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{18 + i * 16}" cy="{header_h / 2 + 1}" r="5" fill="{c}"/>')
    parts.append(
        f'<text x="{width / 2}" y="{header_h / 2 + 5}" text-anchor="middle" class="hdr">'
        f'{escape_xml(stats["username"])}@github --stats</text>'
    )

    y = header_h + pad + 14
    stat_line = (
        f"repos {stats['public_repos']}   stars {stats['total_stars']}   forks {stats['total_forks']}"
    )
    parts.append(f'<text x="20" y="{y}" class="val">{escape_xml(stat_line)}</text>')

    y += stat_row_h
    bar_x = 100
    bar_max_w = width - bar_x - 30
    for i, (lang, pct) in enumerate(langs):
        row_y = y + i * row_h
        bar_w = bar_max_w * (pct / 100.0)
        color = BAR_COLORS[i % len(BAR_COLORS)]
        parts.append(f'<text x="20" y="{row_y + 5}" class="lbl">{escape_xml(lang[:10])}</text>')
        parts.append(
            f'<rect x="{bar_x}" y="{row_y - 8}" width="0" height="12" rx="2" fill="{color}">'
            f'<animate attributeName="width" from="0" to="{bar_w:.1f}" '
            f'begin="{i * 120}ms" dur="500ms" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1" />'
            f'</rect>'
        )
        parts.append(f'<text x="{bar_x + bar_max_w + 8}" y="{row_y + 5}" class="lbl">{pct}%</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "username", nargs="?",
        default=os.environ.get("GITHUB_REPOSITORY_OWNER"),
        help="GitHub username (defaults to $GITHUB_REPOSITORY_OWNER)",
    )
    parser.add_argument("-o", "--output", default=OUTPUT_SVG)
    parser.add_argument("--json-output", default=OUTPUT_JSON)
    args = parser.parse_args()

    if not args.username:
        print(
            "[render_stats] No username given and $GITHUB_REPOSITORY_OWNER isn't set. "
            "Pass one explicitly: python tools/render_stats.py <username>",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[render_stats] Gathering stats for {args.username}...")
    stats = gather_stats(args.username)

    os.makedirs(os.path.dirname(args.json_output) or ".", exist_ok=True)
    with open(args.json_output, "w") as f:
        json.dump(stats, f, indent=2)

    svg = render_svg(stats)
    with open(args.output, "w") as f:
        f.write(svg)

    print(
        f"[render_stats] Wrote {args.output} and {args.json_output} "
        f"({stats['public_repos']} repos, {stats['total_stars']} stars, "
        f"{len(stats['top_languages'])} languages)"
    )


if __name__ == "__main__":
    main()
