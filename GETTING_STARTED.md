# Getting started

This repo is a working implementation of the "Living Terminal" GitHub
profile README. Everything has been built and smoke-tested; the
`portrait.svg`, `sysinfo.svg`, and `graph.svg` currently in this repo were
rendered from placeholder/synthetic data so you can see the pipeline run
end to end. Swap in your own before publishing.

## 1. Create the special repo

GitHub only turns a README into your profile page if the repo name
matches your username exactly:

```bash
gh repo create <yourusername> --public --clone
```

Copy everything in this folder into that repo (or just rename this
folder and `git init` it — see the bottom of this file).

## 2. Personalize the info panel

Edit the `HEADER` and `ROWS` constants at the top of
`tools/render_panel.py`, then:

```bash
python tools/render_panel.py
```

## 3. Generate your real portrait

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r tools/requirements-art.txt

python tools/clean_photo.py /path/to/your-photo.jpg   # -> assets/photo-ready.png
python tools/render_portrait.py                        # -> portrait.svg
```

`rembg`'s first run downloads a small background-removal model — that
requires network access once. If you don't have `rembg` available,
`clean_photo.py` will still run (it just skips background cutting and
uses CLAHE + white padding, per the fallback noted in the script).

## 4. Generate your real contribution graph

```bash
python tools/pull_contributions.py <yourusername>   # -> assets/contributions.json
python tools/render_graph.py                          # -> graph.svg
```

## 5. Commit and push

```bash
git add .
git commit -m "Living terminal profile"
git push
```

## 6. Turn on the daily refresh

The workflow in `.github/workflows/refresh-graph.yml` is already wired to
`${{ github.repository_owner }}`, so it needs no secrets or hardcoded
username. Once pushed, go to the **Actions** tab and manually run
"Refresh contribution graph" once (via `workflow_dispatch`) to confirm it
commits a fresh `graph.svg` before leaving it on the daily cron.

## Notes / things worth knowing

- `pull_contributions.py` uses only the Python standard library
  (`urllib` + `html.parser`) instead of `httpx`/`lxml`, so the daily
  workflow has zero extra pip installs beyond what's already in
  `requirements-daily.txt` (which is now just stdlib — kept as a file in
  case you want to swap in a real HTML parser later). GitHub has changed
  the exact contribution-fragment markup before; if `pull_contributions.py`
  ever reports "No day cells parsed", fetch the URL manually and check
  whether `data-date`/`data-count` (or `data-level`) attributes moved.
- All animation lives inside the SVGs (SMIL `<animate>` tags) — no
  external CSS/JS, which is what lets GitHub's markdown renderer allow it.
- If you'd rather turn this into an actual git repo right now instead of
  a plain folder, run `git init` inside this directory.
