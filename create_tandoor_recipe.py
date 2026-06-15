import sys
import os
import re
import json
import argparse
import io
import requests
from typing import Optional

# Tandoor credentials — override via env vars or CLI flags


class TandoorClient:
    def __init__(self, url: str, api_token: str):
        self.url = url.rstrip("/")
        clean_token = api_token.replace("Bearer ", "").strip() if api_token.startswith("Bearer ") else api_token
        self.headers = {
            "Authorization": f"Bearer {clean_token}",
        }

    def create_recipe(self, data: dict) -> int:
        cleaned = self._clean_payload(data)
        try:
            r = requests.post(
                f"{self.url}/api/recipe/",
                json=cleaned,
                headers={**self.headers, "Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.json()["id"]
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] API request failed ({r.status_code}): {r.text}", file=sys.stderr)
            raise SystemExit(1)

    def _clean_payload(self, obj, allow_keys=None):
        if isinstance(obj, dict) and 'food' in obj:
            return obj

        result = {}
        for k, v in obj.items():
            if isinstance(v, dict):
                result[k] = self._clean_payload(v, allow_keys=allow_keys)
            elif isinstance(v, list):
                cleaned_list = [self._clean_payload(i, allow_keys=allow_keys) for i in v]
                if k == 'name' or k == 'instruction':
                    result[k] = '[{}]' if not any(x is not None and x != {} for x in cleaned_list) else cleaned_list
                else:
                    result[k] = [x for x in cleaned_list if x is not None]
            else:
                result[k] = v
        return result

    def upload_image(self, recipe_id: int, image_url):
        if not image_url:
            return
        try:
            img = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"})
            r = requests.put(
                f"{self.url}/api/recipe/{recipe_id}/image/",
                files={"image": ("pita.jpg", io.BytesIO(img.content), "image/jpeg")},
                headers=self.headers
            )
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Image upload failed ({e})", file=sys.stderr)
            raise SystemExit(1)



def parse_unit(unit_str: str) -> Optional[str]:
    known = {"g", "kg", "ml", "l", "el", "tl", "stuk", "stuks", "snip", "snippertje", "koppetje", "blik", "kan", "pot", "zak"}
    return unit_str if unit_str.lower() in known else None


def parse_amount(amount_str: str) -> float:
    """Convert amount string like '1/3', '50', '2.5' to float."""
    if '/' in amount_str:
        num, denom = amount_str.split('/')
        return float(num) / float(denom)
    return float(amount_str.replace(',', '.'))


def parse_ingredient(text: str):
    text = text.strip()

    # Skip non-ingredient items
    if text.lower() in ("optioneel", "optionele ingrediënten"):
        return {"food": {"name": text}, "amount": 0.0, "unit": None}

    # Match: optional fraction (e.g. '1/3'), then integer/decimal amount, unit, food name
    pattern = r"^(\d+(?:[.,]\d+)?(?:/\d+)?|(?:\d+/)\d+)\s+(?P<unit>\w+)\s+(?P<food>.+)$"
    match = re.match(pattern, text)
    if match:
        amount_raw = match.group(1)
        unit_str = match.group("unit")
        food_name = match.group("food").strip()

        parsed_amount = parse_amount(amount_raw)
        unit = parse_unit(unit_str)

        result = {
            "food": {"name": food_name},
            "amount": parsed_amount,
            "unit": {"name": unit} if unit else None,
        }
        return result

    # No explicit amount: check for parenthetical notes in the food name
    # e.g. "room (20% vg)" -> food="room", note="(20% vg)"
    note = None
    if "(" in text and ")" in text:
        open_pos = text.rfind("(")
        close_pos = text.rfind(")")
        name_part = text[:open_pos].strip()
        note = text[open_pos:close_pos+1].strip()
        food_name = name_part if name_part else text
    else:
        food_name = text

    result = {
        "food": {"name": food_name},
        "amount": 0.0,
        "unit": None,
        "note": note,
    }
    return result


def extract_image_url(html_text: str) -> Optional[str]:
    for pattern in [r'og:image" content="(https?://[^"]+)"', r'property="og:image"[^>]*content="(https?://[^"]+)"']:
        m = re.search(pattern, html_text)
        if m:
            return m.group(1)
    return None


def scraped_to_tandoor(scraper, html: str):
    # Prefer scraper's decoded S3 URL over HTML meta tags (og:image is rarely SSR-injected)
    image_url = None
    if scraper.image_url:
        image_url = scraper.image_url
    else:
        image_url = extract_image_url(html)

    instructions = scraper.instructions
    ingredients = scraper.ingredients or []

    # Collect all ingredients for the "Ingrediënten" step
    all_ingredients = [parse_ingredient(i) for i in ingredients if i.strip()]

    steps = []

    # Build instruction steps with all ingredients on the first step (matching native Tandoor pattern)
    for i, text in enumerate(instructions):
        step_ingredients = all_ingredients if i == 0 else []
        steps.append({
            "name": "",
            "instruction": text,
            "order": i,
            "time": 0,
            "show_as_header": False,
            "show_ingredients_table": True,
            "ingredients": step_ingredients,
        })

    working_minutes = max(1, scraper.total_time) if scraper.total_time else 1

    parts = []
    if scraper.subtitle:
        parts.append(f"[{scraper.subtitle}]")
    if scraper.description:
        parts.append(scraper.description)
    if scraper.tip:
        parts.append(f"Chef's tip: {scraper.tip}")
    full = (" ".join(parts) if parts else "")
    if len(full) > 512:
        description = full[:512].rsplit(' ', 1)[0]
    else:
        description = full

    recipe_data = {
        "name": scraper.title or "Untitled Recipe",
        "description": description,
        "servings": 4,
        "servings_text": "portions",
        "working_time": working_minutes,
        "waiting_time": 0,
        "source_url": scraper.url,
        "internal": True,
        "show_ingredient_overview": True,
        "keywords": [],
        "steps": steps,
    }

    return recipe_data, image_url


def main():
    parser = argparse.ArgumentParser(description="Create a recipe in Tandoor from foodbag.be")
    parser.add_argument("url", help="URL of the recipe from foodbag.be")
    parser.add_argument("--tandoor-url", default=os.getenv("TANDOOR_URL"), help="Tandoor base URL")
    parser.add_argument("--api-token", default=os.getenv("TANDOOR_API_TOKEN"), help="Tandoor API token")
    args = parser.parse_args()

    # Defaults from tandoor-create-example.py if not set
    tandoor_url = args.tandoor_url or os.getenv("TANDOOR_URL", "https://tandoor.d54.me")
    api_token = args.api_token or os.getenv("TANDOOR_API_TOKEN")

    if not api_token:
        print("[ERROR] API token required. Set TANDOOR_API_TOKEN env var or pass --api-token.", file=sys.stderr)
        raise SystemExit(1)

    from extract_recipe import FoodbagScraper, get_rendered_html

    html = get_rendered_html(args.url)
    scraper = FoodbagScraper(url=args.url, html=html)

    recipe_data, image_url = scraped_to_tandoor(scraper, html)

    client = TandoorClient(tandoor_url, api_token)
    recipe_id = client.create_recipe(recipe_data)
    print(f"Created recipe #{recipe_id}: {recipe_data['name']}", file=sys.stderr)

    if image_url:
        client.upload_image(recipe_id, image_url)
        print(f"Image URL set to {image_url}", file=sys.stderr)

    # Output JSON for confirmation
    recipe_data["id"] = recipe_id
    recipe_data["_image_url"] = image_url
    print(json.dumps(recipe_data, indent=2))


if __name__ == "__main__":
    main()
