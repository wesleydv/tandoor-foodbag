import sys
import json
import argparse
from playwright.sync_api import sync_playwright

class FoodbagScraper:
    """Custom scraper for foodbag.be"""
    
    def __init__(self, url, html):
        self.url = url
        from bs4 import BeautifulSoup, Tag
        import re as _re
        self.soup = BeautifulSoup(html, 'html.parser') if html else None

    @property
    def title(self):
        if not self.soup: return None
        tag = self.soup.find('h1')
        return tag.text.strip() if tag else None

    @property
    def total_time(self):
        # Return time in minutes — no seconds conversion needed
        if not self.soup: return None
        
        tag = self.soup.find(lambda t: t.name == 'p' and 'min. kookplezier' in t.text)
        if tag:
            import re as _re
            match = _re.search(r'(\d+)', tag.text)
            return int(match.group(1)) if match else None
        
        # Fallback: sum prep + oven minutes (e.g. "10' min. bereidingstijd")
        import re as _re
        total = 0
        for p_tag in self.soup.find_all('p'):
            text = p_tag.text.strip()
            m = _re.search(r'(\d+)\s*[\u2018\u2019\']?\s*min\.?\s*(voorbereiding|bereidingstijd|oventijd)', text, _re.IGNORECASE)
            if m:
                total += int(m.group(1))
        
        return total if total > 0 else None

    @property
    def subtitle(self):
        """Extract the recipe subtitle (e.g. 'currymayo en paprika')"""
        if not self.soup: return None
        # First try og:description which often contains the subtitle
        og_desc = self.soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            content = og_desc['content'].strip()
            # Filter out long descriptions that are actually body text
            if len(content) < 100:
                return content
        
        # Fall back to finding a distinctive short text near the recipe title
        recipe_keywords = ['paprika', 'reepjes', 'orzo', 'kippenhaas', 'tik']
        for tag in self.soup.find_all(['p', 'span']):
            text = tag.text.replace('\n', ' ').strip()
            if len(text) > 5 and len(text) < 100:
                # Skip ingredient items and recipe names
                if any(kw in text.lower() for kw in recipe_keywords):
                    continue
                # Must appear after the main h1 (subtitle comes after title)
                prev_h1 = tag.find_previous('h1')
                if prev_h1:
                    return text
        
        return None

    @property
    def description(self):
        """Extract the recipe description/intro paragraph"""
        if not self.soup: return None
        import re as _re
        
        body = self.soup.find('body')
        if not body: return None
        
        exclusion_keywords = ['cookiebeleid', 'privacy', 'cookies', 'adverteerders', 
                              'aanbieder', 'analyseer', 'functionaliteit', 'essentieel',
                              'deze cookies', 'cookies stellen']
        
        # Collect candidate paragraphs that appear before ingredients section
        # Key insight: recipe intro is the FIRST long paragraph in body, not anywhere
        candidates = []
        for p in body.find_all('p'):
            text = _re.sub(r'\s+', ' ', p.text.strip())
            if len(text) < 40:
                continue
            # Skip cookie/legal/ad content
            if any(kw in text.lower() for kw in exclusion_keywords):
                continue
            # Stop once we hit the ingredients section (identified by "Ingrediënten" header)
            if _re.search(r'ingredi[eë]\w*', p.text, _re.IGNORECASE):
                break
            
            candidates.append(text)
        
        # Collect paragraphs matching intro keywords, pick the longest among them
        intro_keywords = ['comfy', 'lange werkdag', 'gevoel', 'thuis', 'gerecht', 
                         'eigen versie', 'gewoon', 'snel op tafel', 'mijn advies']
        matched = []
        for kw in intro_keywords:
            for c in candidates:
                if kw.lower() in c.lower():
                    matched.append(c)
        if matched:
            longest = max(matched, key=len)
            return longest[:1200]
        
        # Fallback: take the longest qualifying candidate (recipe intros are typically long)
        if candidates:
            best = max(candidates, key=len)
            return best[:1200]
        
        return None

    @property
    def tip(self):
        """Extract the recipe tip/secret chef text"""
        if not self.soup: return None
        
        # Foodbag uses <p class="text-base font-normal text-green">Tip</p> as heading,
        # with a sibling div following it containing the actual tip text (starts with "Ik begin")
        for tag in self.soup.find_all('p'):
            classes = tag.get('class') or []
            if 'text-green' in classes and 'text-base' in classes:
                raw_text = ''.join(tag.text.split())
                if raw_text == 'Tip':
                    sibling_div = tag.find_next_sibling()
                    if sibling_div and sibling_div.name in ('div', 'p'):
                        tip_text = sibling_div.get_text().strip()
                        # The div starts with the Tip header concatenated: "TipIk begin..."
                        if tip_text.startswith('Tip'):
                            tip_text = tip_text[len('Tip'):]
                        tip_text = tip_text.strip()
                        if len(tip_text) > 10 and 'Leverancier' not in tip_text:
                            return tip_text if tip_text else tag.text.strip().strip('\n \t')
        
        # Fallback to heading-based approach for other recipes
        for tag in self.soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            if 'tip' in tag.text.lower() and len(tag.text.strip()) < 30:
                paragraphs = []
                curr = tag.find_next(['p', 'div'])
                while curr:
                    text = curr.get_text().strip()
                    if not text:
                        curr = curr.find_next(['p', 'div'])
                        continue
                    if len(text) > 500:
                        break
                    paragraphs.append(text)
                    curr = curr.find_next(['p', 'div'])
                return '\n'.join(paragraphs) if paragraphs else tag.text.strip()
        
        return None

    @property
    def image_url(self):
        """Extract the recipe cover image URL"""
        if not self.soup: return None
        
        # og:image is the most reliable source for foodbag.be images
        og_img = self.soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            url = og_img['content'].strip()
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                return url
        
        # Foodbag uses Next.js image proxy: _next/image?url=S3_ORIGINAL_URL&w=...
        # The cover image is typically w=3840 - extract directly without complex regexes
        from urllib.parse import unquote, urlparse, parse_qs
        
        for img in self.soup.find_all('img'):
            src = (img.get('src') or '').strip()
            if '_next/image' in src and 'smartmat-production' in src:
                params = parse_qs(src.split('?')[1])
                url_param = params.get('url', [''])[0] if 'url' in params else ''
                if url_param:
                    decoded = unquote(url_param)
                    if any(ext in decoded.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        return decoded
        
        # Check link tags for foodbag images
        recipe_section = self.soup.find(id=lambda x: x and ('recipe' in x.lower() or 'dish' in x.lower())) or self.soup.find('main')
        if recipe_section:
            for img in recipe_section.find_all('img'):
                src = (img.get('src') or '').strip()
                if 'foodbag-cdn' in str(src).lower() and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    return src
            for link in recipe_section.find_all('link'):
                href = (link.get('href') or '').strip()
                if 'storage.googleapis.com/foodbag' in href:
                    return href
        
        return None

    @property
    def ingredients(self):
        if not self.soup: return []
        ingredients = []

        # Main ingredients: <h6> names with text-[#A8A8A8] quantity markers
        for h6 in self.soup.find_all('h6'):
            name = h6.get_text().strip()
            if not name or len(name) < 2:
                continue

            # Skip non-ingredient h6 (labels, times, allergen text)
            if any(skip in name for skip in ['Chef', 'NL']):
                continue
            # Skip standalone times like "30'"
            clean = name.replace("'", "").replace('"', '').replace('\u2018', '').replace('\u2019', '').replace('\u2032', '')
            if clean.strip().isdigit():
                continue
            # Skip allergen info
            if 'raadpleeg' in name.lower():
                continue

            # Search in parent chain for quantity
            parent = h6.parent
            while parent:
                qty_div = parent.find(class_='text-[#A8A8A8]')
                if qty_div:
                    txt = qty_div.get_text().strip()
                    if txt and any(c.isdigit() or c in '/mlgc' for c in txt[:3]):
                        ingredients.append(f"{txt} {name}")
                        break
                parent = parent.parent

        # "Uit jouw keuken": first <details> accordion (item 0 in both recipes)
        details_list = self.soup.find_all('details')
        if details_list:
            first = details_list[0]
            # Find comma-separated content in child divs
            for div in first.find_all('div'):
                text = div.get_text().strip()
                if ',' in text and 'raadpleeg' not in text.lower():
                    items = [item.strip() for item in text.split(',') if item.strip()]
                    ingredients.extend(items)
                    break

        return ingredients

    @property
    def instructions(self):
        if not self.soup: return []
        instructions = []
        header = self.soup.find(lambda t: t.name == 'p' and 'Bereiding' in t.text)
        if not header: return []

        curr = header
        while curr:
            curr = curr.find_next()
            if not curr: break
            if curr.name == 'p' and 'text-sm' in curr.get('class', []) and 'w-full' in curr.get('class', []):
                instructions.append(curr.text.strip())
        return instructions


def get_rendered_html(url):
    with sync_playwright() as p:
        browser = p.chromium.connect('ws://192.168.15.166:3000/')
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"Navigating to {url}...", file=sys.stderr)
            page.goto(url, wait_until='load')

            # Handle Cookie Banner
            cookie_btn = page.locator('#onetrust-accept-btn-handler')
            if cookie_btn.is_visible():
                cookie_btn.click()
                print("Cookie banner accepted.", file=sys.stderr)

            # Wait for full recipe hydration including body text and images
            ready = False
            for _ in range(120):
                try:
                    page.evaluate("""() => {
                        var txt = document.body.innerText;
                        var hasIngredients = txt.includes('Ingrediënten');
                        var hasBereiding = txt.includes('Bereiding') || txt.includes('comfy gives');
                        var metaImg = !!document.querySelector('meta[property="og:image"]');
                        return hasIngredients && (hasBereiding || metaImg);
                    }""") and True
                except:
                    pass
                if ready or page.evaluate("() => !!document.body"):
                    ready = True
                if ready:
                    break
                page.wait_for_timeout(500)
            
            try:
                page.wait_for_selector('.recipe-title, h1', timeout=20000)
            except:
                pass  # Some recipes may not have a separate title element
            
            page.wait_for_timeout(3000)
            content = page.content()
            return content
        finally:
            page.close()
            context.close()
            browser.close()

def main():
    parser = argparse.ArgumentParser(description='Extract recipe from foodbag.be for Tandoor import')
    parser.add_argument('url', help='URL of the recipe')
    args = parser.parse_args()

    try:
        html = get_rendered_html(args.url)
        
        scraper = FoodbagScraper(url=args.url, html=html)
        
        output = {
            "name": scraper.title,
            "url": args.url,
            "subtitle": scraper.subtitle,
            "description": scraper.description or "",
            "image_url": scraper.image_url,
            "tip": scraper.tip,
            "ingredients": scraper.ingredients,
            "instructions": [
                {"step": i, "text": text} for i, text in enumerate(scraper.instructions, 1)
            ],
            "total_time": scraper.total_time,
        }
        
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
