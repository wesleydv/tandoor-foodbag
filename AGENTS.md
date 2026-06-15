# Agent Guide

## Execution
- **Scraper**: Run `node extract_dish.js` to scrape recipe data.
- **Remote Browser**: The scraper requires a remote Playwright browser at `ws://192.168.15.166:3000/`. It will fail if this endpoint is unreachable.

## Infrastructure
- This repo contains a specialized scraping script targeting `foodbag.be`.
- Output files (`rendered_dish.html`, `rendered_dish.txt`) are written to the root directory.

## Web Import Tool (`app.py`)
- Single-page Flask app for importing recipes from URLs into Tandoor via a web UI.
- **Run**: `venv/bin/python app.py` (must use venv, starts on http://127.0.0.1:9615)
- **Backend flow**: POST `/import` accepts JSON `{url}` → queues background thread → polls `GET /import/status/<id>` for progress.
- Uses `extract_recipe.py` (FoodbagScraper/Playwright) and `create_tandoor_recipe.py` (TandoorClient).
- Uses manual `.env` parser (no python-dotenv dependency); checks both current dir and script directory for `.env`.
- UI language is Dutch.

## Rules
- Never commit, push, or create PRs unless explicitly requested by the user.

## Known Issues
- `'FoodbagScraper' object has no attribute 'total_time'`: runtime error in `app.py`, likely caused by kwarg misalignment with the positional `__init__(self, url, html)` or a missing/renamed property in `extract_recipe.py`. Needs investigation before the import tool is reliable.
