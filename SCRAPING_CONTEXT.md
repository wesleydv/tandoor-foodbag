# Foodbag Scraping Documentation

## How it Works
The `foodbag.be` site uses a client-side hydration model where most content is fetched asynchronously via Firestore gRPC-Web streams after the initial HTML shell is loaded. 

Because the actual recipe data (ingredients, directions) is not in the source HTML, a standard HTTP request or simple DOM snapshot will fail to capture the dish details. To successfully scrape this site:
1. **Remote Browser Connection**: Connect via Playwright's `wsEndpoint` to a remote browser instance.
2. **Cookie Acceptance**: The cookie banner (`#onetrust-accept-btn-handler`) must be accepted to ensure hydration scripts execute without interruption.
3. **Hydration Wait**: Instead of waiting for network idle, the script waits for specific dish keywords (e.g., "Ingrediënten", "Bereiding") to appear in the DOM. This confirms that the Firestore streams have resolved and the React components have rendered.
4. **Text Extraction**: Once hydrated, the `innerText` of the body provides a clean, readable version of the recipe without needing complex CSS selector logic for every dish.

## Technical Requirements
- **Playwright**: Used for remote browser orchestration.
- **Remote Endpoint**: `ws://192.168.15.166:3000/` (or equivalent Playwright server).

## Example Script
The file `extract_dish.js` provides a complete implementation of this workflow.
