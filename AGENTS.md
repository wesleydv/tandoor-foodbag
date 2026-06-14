# Agent Guide

## Execution
- **Scraper**: Run `node extract_dish.js` to scrape recipe data.
- **Remote Browser**: The scraper requires a remote Playwright browser at `ws://192.168.15.166:3000/`. It will fail if this endpoint is unreachable.

## Infrastructure
- This repo contains a specialized scraping script targeting `foodbag.be`.
- Output files (`rendered_dish.html`, `rendered_dish.txt`) are written to the root directory.
