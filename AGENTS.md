# Agent Guide

## Repository structure
Three Python files form the pipeline:

| File | Purpose |
|------|---------|
| `extract_recipe.py` | FoodbagScraper class + Playwright rendering (`get_rendered_html`). Scrapes foodbag.be recipes into structured data. |
| `create_tandoor_recipe.py` | TandoorClient class + `scraped_to_tandoor()` conversion function. Posts parsed recipes to the Tandoor API and uploads images. Standalone CLI tool (run with `python create_tandoor_recipe.py <url>`). |
| `app.py` | Flask web UI for importing recipes from foodbag.be URLs into Tandoor. Runs on http://0.0.0.0:9615. Supports URL input and in-browser QR code scanning. |

## Configuration
- Credentials are read via a manual `.env` parser (no `python-dotenv` dependency), checking both the current working directory and the script's parent directory for `.env`.
- Required env vars (checked first): `TANDOOR_API_TOKEN`. Fallback source: `TANDOOR_URL` (default: `https://tandoor.d54.me`).

## Running the tools

### Web UI (recommended)
```bash
venv/bin/python app.py
```
Open http://127.0.0.1:9615. Submit a foodbag.be URL or scan a QR code with the camera button. Backend flow: POST `/import` queues a background thread → poll `GET /import/status/<id>` for progress. UI is in Dutch.

### CLI (standalone)
```bash
python create_tandoor_recipe.py <url> --tandoor-url <TANDOOR_URL> --api-token <TOKEN>
# or via env vars: TANDOOR_URL and TANDOOR_API_TOKEN
```

## Scraping details
- Uses Playwright (`ws://192.168.15.166:3000/`) for the remote Chromium browser — fails if this endpoint is unreachable.
- Accepts Onetrust cookie banners automatically. Waits for recipe hydration (Ingredients header or og:image meta tag).
- FoodbagScraper properties: `title`, `total_time` (minutes), `subtitle`, `description`, `tip`, `image_url`, `ingredients`, `instructions`.

## Task Planning
Before starting any multi-step task, ALWAYS use the `todowrite` tool to create a structured todo list.
Update each item with `todowrite` as you complete it (set status to "completed").
Never skip this step, even for short tasks.

## Rules
- Never commit, push, or create PRs unless explicitly requested by the user.
