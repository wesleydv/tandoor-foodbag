import sys
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

def run():
    with sync_playwright() as p:
        server_url = os.getenv("PLAYWRIGHT_SERVER_URL", "ws://playwright:3000/")
        browser = p.chromium.connect(server_url)
        page = browser.new_page()
        url = "https://www.foodbag.be/nl/recept?dishId=a0MJv00000FGaDNMA1&weekDocId"
        print(f"Navigating to {url}...", file=sys.stderr)
        page.goto(url, wait_until='load')
        
        # Wait for the portion control
        page.wait_for_selector('img[alt*="increase amount"]', timeout=10000)
        plus_btn = page.locator('button:has(img[alt*="increase amount"])')
        print(f"Plus button found. Count: {plus_btn.count()}", file=sys.stderr)
        
        # Find the container
        container = plus_btn.first.locator('xpath=..')
        print("--- Container Inner Text ---", file=sys.stderr)
        print(container.inner_text(), file=sys.stderr)
        print("---------------------------", file=sys.stderr)
        
        # Let's find all elements that are potentially the value
        # Try to look for any element that contains only digits within a reasonable distance
        all_elements = page.locator('*').all()
        for el in all_elements:
            text = el.inner_text().strip()
            if text.isdigit():
                parent = el.locator('xpath=..')
                print(f"Found digit element: <{el.evaluate('el => el.tagName')}> text='{text}' parent_text='{parent.inner_text().strip()}'", file=sys.stderr)

        browser.close()

if __name__ == '__main__':
    run()
