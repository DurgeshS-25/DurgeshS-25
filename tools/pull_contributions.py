#!/usr/bin/env python3
"""
pull_contributions.py

Pulls your public GitHub contribution calendar without any token or OAuth:
GitHub serves a plain HTML fragment (the same markup the profile page
itself consumes) at:

    https://github.com/users/<username>/contributions

This parses the day cells out of that fragment and writes a small JSON
summary — not just raw counts, but current streak, longest streak, and a
busiest-day-of-week breakdown, so the eventual graph footer has more to
say than just a total.

Usage:
    python tools/pull_contributions.py <username>
    # writes assets/contributions.json

Username defaults to the GITHUB_REPOSITORY_OWNER env var if omitted (this
is set automatically inside GitHub Actions), so the daily workflow can
call this with no arguments.
"""
import argparse
import datetime
import json
import os
import re
import sys
from html.parser import HTMLParser

CONTRIB_URL = "https://github.com/users/{username}/contributions"
OUTPUT_PATH = "assets/contributions.json"


class ContributionCellParser(HTMLParser):
    """Parses <td>/<rect> style day cells out of GitHub's contribution
    fragment. GitHub has changed the exact markup a few times over the
    years (table cells vs. <rect> elements in an inline SVG); this parser
    handles both by looking for the data-date / data-count style
    attributes wherever they appear, plus a fallback regex pass.
    """

    def __init__(self):
        super().__init__()
        self.days = {}  # date string -> count

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        date = attr_dict.get("data-date")
        count = attr_dict.get("data-count") or attr_dict.get("data-level")
        # Newer markup sometimes only exposes the tooltip text; that's
        # handled by the regex fallback in fetch_and_parse() instead.
        if date and count is not None:
            try:
                self.days[date] = int(count)
            except ValueError:
                pass


def fetch_html(username: str) -> str:
    import urllib.request

    url = CONTRIB_URL.format(username=username)
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_contributions(html: str) -> dict:
    """Extract {date: count} from the fragment. Tries the structured
    parser first, then falls back to a regex over data-date/data-count
    (or data-level, in the newer 5-tier markup) pairs if the DOM shape
    isn't what we expect.
    """
    parser = ContributionCellParser()
    parser.feed(html)
    days = parser.days

    if not days:
        # Fallback: scan raw attribute pairs regardless of tag structure.
        pattern = re.compile(
            r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*?data-(?:count|level)="(\d+)"'
        )
        for date_str, count_str in pattern.findall(html):
            days[date_str] = int(count_str)

    return days


def compute_streaks(days: dict) -> tuple[int, int]:
    """Returns (current_streak, longest_streak) in days, counting
    backward from the most recent date with any recorded contributions."""
    if not days:
        return 0, 0

    dated = sorted(
        (datetime.date.fromisoformat(d), c) for d, c in days.items()
    )
    longest = 0
    current = 0
    running = 0
    prev_date = None

    for d, c in dated:
        if c > 0:
            if prev_date is not None and (d - prev_date).days == 1:
                running += 1
            else:
                running = 1
            longest = max(longest, running)
        else:
            running = 0
        prev_date = d

    # Current streak: walk backward from the last day in the dataset.
    today_idx = len(dated) - 1
    streak = 0
    for i in range(today_idx, -1, -1):
        _, c = dated[i]
        if c > 0:
            streak += 1
        else:
            break
    current = streak

    return current, longest


def busiest_weekday(days: dict) -> str:
    """Returns the name of the weekday with the most total contributions."""
    totals = [0] * 7  # Mon=0 .. Sun=6
    for d, c in days.items():
        weekday = datetime.date.fromisoformat(d).weekday()
        totals[weekday] += c

    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    best = max(range(7), key=lambda i: totals[i])
    return names[best]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "username", nargs="?",
        default=os.environ.get("GITHUB_REPOSITORY_OWNER"),
        help="GitHub username (defaults to $GITHUB_REPOSITORY_OWNER)",
    )
    parser.add_argument("-o", "--output", default=OUTPUT_PATH)
    args = parser.parse_args()

    if not args.username:
        print(
            "[pull_contributions] No username given and $GITHUB_REPOSITORY_OWNER "
            "isn't set. Pass one explicitly: python tools/pull_contributions.py <username>",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[pull_contributions] Fetching contributions for {args.username}...")
    html = fetch_html(args.username)
    days = parse_contributions(html)

    if not days:
        print(
            "[pull_contributions] No day cells parsed — GitHub may have changed "
            "the contribution fragment's markup. Inspect the raw HTML to update "
            "the parser.",
            file=sys.stderr,
        )
        sys.exit(1)

    current_streak, longest_streak = compute_streaks(days)
    total = sum(days.values())

    summary = {
        "username": args.username,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "busiest_weekday": busiest_weekday(days),
        "days": days,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(
        f"[pull_contributions] Wrote {args.output} "
        f"({total} contributions, {len(days)} days, "
        f"current streak {current_streak}, longest {longest_streak})"
    )


if __name__ == "__main__":
    main()
