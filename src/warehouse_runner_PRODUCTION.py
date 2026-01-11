#!/usr/bin/env python3
"""
PRODUCTION - Warehouse Runner Scraper
======================================
50 workers, FIXED regex patterns, 33-35 min runtime
Combines FIXED extraction + optimized performance
"""

import sys
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep, time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import cloudscraper
    from bs4 import BeautifulSoup
except ImportError:
    print("Install: pip install cloudscraper beautifulsoup4 lxml")
    sys.exit(1)

# Food filter keywords
FOOD_KEYWORDS = ['milk', 'cheese', 'butter', 'yogurt', 'cream', 'egg', 'chicken', 'beef', 'pork', 'turkey', 'bacon', 'sausage', 'ham', 'meat', 'fish', 'salmon', 'tuna', 'shrimp', 'seafood', 'frozen', 'ice cream', 'lettuce', 'tomato', 'onion', 'potato', 'carrot', 'apple', 'banana', 'orange', 'grape', 'berry', 'bread', 'bagel', 'muffin', 'cake', 'cookie', 'pizza', 'sandwich', 'salad', 'juice', 'smoothie', 'soda', 'cola', 'pepsi', 'coke', 'sprite', 'mountain dew', 'gatorade', 'coffee', 'tea', 'mayonnaise', 'mayo', 'ketchup', 'mustard', 'sauce', 'dressing', 'soup', 'broth', 'chips', 'crackers', 'pretzels', 'popcorn', 'nuts', 'candy', 'chocolate']

def is_food(name, brand=''):
    """Quick food check"""
    text = (name + ' ' + brand).lower()
    if any(x in text for x in ['ice scraper', 'ice brush', 'motor oil', 'synthetic oil']):
        return False
    return any(kw in text for kw in FOOD_KEYWORDS)

# Global scraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)

# Paths
DATA_DIR = Path('D:/DeadMan_AI_Research/Data/costco_markdowns')
DATA_DIR.mkdir(exist_ok=True)
ITEMS_FILE = Path('D:/DeadMan_AI_Research/Data/warehouse_runner_all_items.txt')
PROGRESS_FILE = DATA_DIR / 'production_progress.json'
MARKDOWNS_FILE = DATA_DIR / 'production_markdowns.json'


def extract_fast(item_id):
    """FIXED extraction with escaped regex patterns"""
    url = f'https://app.warehouserunner.com/costco/{item_id}'

    try:
        response = scraper.get(url, timeout=8)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'lxml')
        html = response.text

        # Get Schema.org data
        product_name = ''
        product_brand = ''
        low_price = 0
        high_price = 0

        scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for script in scripts:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Product':
                    product_name = data.get('name', '')
                    brand_data = data.get('brand', {})
                    product_brand = brand_data.get('name', '') if isinstance(brand_data, dict) else str(brand_data)
                    offers = data.get('offers', {})
                    if offers.get('@type') == 'AggregateOffer':
                        low_price = float(offers.get('lowPrice', 0))
                        high_price = float(offers.get('highPrice', 0))
                    break
            except:
                continue

        if not product_name:
            return None

        # Food filter
        if is_food(product_name, product_brand):
            return {'is_food': True}

        # FIXED: Extract markdown data with escaped quotes
        sale_info_match = re.search(r'\\"saleInfo\\":(null|\{[^}]+\})', html)
        has_instant_savings = sale_info_match and sale_info_match.group(1) != 'null'

        discount_count_match = re.search(r'\\"discount_count\\":\s*(\d+)', html)
        discount_count = int(discount_count_match.group(1)) if discount_count_match else 0

        manager_special_match = re.search(r'\\"manager_special_count\\":\s*(\d+)', html)
        manager_special_count = int(manager_special_match.group(1)) if manager_special_match else 0

        sale_info = None
        if has_instant_savings:
            original_price_match = re.search(r'\\"original_price\\":\s*([0-9.]+)', html)
            sale_price_match = re.search(r'\\"sale_price\\":\s*([0-9.]+)', html)
            discount_match = re.search(r'\\"discount\\":\s*([0-9.]+)', html)
            discount_pct_match = re.search(r'\\"discount_percentage\\":\s*([0-9.]+)', html)
            days_remaining_match = re.search(r'\\"days_remaining\\":\s*(\d+)', html)
            store_count_match = re.search(r'\\"store_count\\":\s*(\d+)', html)

            if original_price_match and sale_price_match:
                sale_info = {
                    'original_price': float(original_price_match.group(1)),
                    'sale_price': float(sale_price_match.group(1)),
                    'discount_amount': float(discount_match.group(1)) if discount_match else 0,
                    'discount_percentage': float(discount_pct_match.group(1)) if discount_pct_match else 0,
                    'days_remaining': int(days_remaining_match.group(1)) if days_remaining_match else 0,
                    'store_count': int(store_count_match.group(1)) if store_count_match else 0
                }

        is_markdown = sale_info is not None or discount_count > 0 or manager_special_count > 0

        if is_markdown:
            states = []
            state_pattern = r'\\"state\\":\\"([A-Z]{2})\\"[^}]*?\\"avgPrice\\":\s*([0-9.]+)[^}]*?\\"storeCount\\":\s*(\d+)'
            state_matches = re.findall(state_pattern, html)

            for state, avg_price, store_count in state_matches[:20]:
                states.append({
                    'state': state,
                    'stores': int(store_count),
                    'avg_price': float(avg_price)
                })

            markdown_result = {
                'item_id': item_id,
                'name': product_name,
                'brand': product_brand,
                'low_price': low_price,
                'high_price': high_price,
                'url': url,
                'is_markdown': True,
                'is_food': False,
                'markdown_type': [],
                'states': states
            }

            if sale_info:
                markdown_result['markdown_type'].append('instant_savings')
                markdown_result['instant_savings'] = sale_info

            if discount_count > 0:
                markdown_result['markdown_type'].append('regional_discount')
                markdown_result['discount_count'] = discount_count

            if manager_special_count > 0:
                markdown_result['markdown_type'].append('manager_special')
                markdown_result['manager_special_count'] = manager_special_count

            return markdown_result

        return {'is_food': False, 'is_markdown': False}

    except:
        return None


def load_item_ids():
    with open(ITEMS_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {'processed_ids': [], 'total': 0, 'food_excluded': 0, 'markdowns': 0}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def load_markdowns():
    if MARKDOWNS_FILE.exists():
        with open(MARKDOWNS_FILE, encoding='utf-8') as f:
            return json.load(f).get('products', [])
    return []


def save_markdowns(markdowns):
    with open(MARKDOWNS_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'source': 'Warehouse Runner PRODUCTION (50 workers, FIXED regex)',
            'total': len(markdowns),
            'products': sorted(markdowns, key=lambda x: x.get('low_price', 0))
        }, f, indent=2, ensure_ascii=False)


def format_time(seconds):
    return str(timedelta(seconds=int(seconds)))


def main():
    print("="*70)
    print("WAREHOUSE RUNNER - PRODUCTION SCRAPER")
    print("50 workers, 0.1s delay, FIXED regex patterns")
    print("="*70)

    # Load
    print("\n[*] Loading...")
    all_ids = load_item_ids()
    progress = load_progress()
    processed = set(progress['processed_ids'])
    remaining = [id for id in all_ids if id not in processed]

    print(f"  Total: {len(all_ids)}")
    print(f"  Done: {len(processed)}")
    print(f"  Remaining: {len(remaining)}")

    if not remaining:
        print("\n✅ All done!")
        return

    markdowns = load_markdowns()
    print(f"  Current markdowns: {len(markdowns)}")
    print(f"  Food excluded: {progress.get('food_excluded', 0)}")

    # Estimate
    rate = 22.35  # items/sec with 50 workers
    eta = len(remaining) / rate
    print(f"\n[*] Config: 50 workers, 0.1s delay, 8s timeout")
    print(f"  ETA: {format_time(eta)}")

    print(f"\n{'='*70}")
    print("STARTING PRODUCTION SCRAPE")
    print('='*70)

    start_time = time()
    save_counter = 0

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(extract_fast, id): id for id in remaining}

        for i, future in enumerate(as_completed(futures), 1):
            item_id = futures[future]

            try:
                result = future.result()

                if result:
                    if result.get('is_food'):
                        progress['food_excluded'] += 1
                    elif result.get('is_markdown'):
                        markdowns.append(result)
                        progress['markdowns'] += 1
                        types = ', '.join(result.get('markdown_type', []))
                        print(f"  [{len(processed)+i}/{len(all_ids)}] 🎯 {result['name'][:40]} ${result['low_price']:.2f} ({types})")

                processed.add(item_id)
                progress['processed_ids'] = list(processed)
                progress['total'] = len(processed)
                save_counter += 1

                if save_counter >= 500:
                    save_progress(progress)
                    save_markdowns(markdowns)
                    save_counter = 0
                    elapsed = time() - start_time
                    rate_now = i / elapsed if elapsed > 0 else 0
                    eta_sec = (len(remaining) - i) / rate_now if rate_now > 0 else 0
                    print(f"  💾 {len(markdowns)} markdowns | {rate_now:.1f}/s | ETA: {format_time(eta_sec)} | Food: {progress['food_excluded']}")

            except:
                pass

            sleep(0.1)

    save_progress(progress)
    save_markdowns(markdowns)

    total_time = time() - start_time

    print(f"\n{'='*70}")
    print("PRODUCTION SCRAPE COMPLETE")
    print('='*70)
    print(f"\n  Total: {len(all_ids)} | Food: {progress['food_excluded']} | Markdowns: {len(markdowns)}")
    print(f"  Time: {format_time(total_time)} | Rate: {len(all_ids)/total_time:.1f}/s")

    if markdowns:
        instant = sum(1 for m in markdowns if 'instant_savings' in m)
        regional = sum(1 for m in markdowns if 'regional_discount' in m.get('markdown_type', []))
        manager = sum(1 for m in markdowns if 'manager_special' in m.get('markdown_type', []))
        print(f"\n  Instant Savings: {instant} | Regional: {regional} | Manager: {manager}")
        print(f"\n  Saved: {MARKDOWNS_FILE}")


if __name__ == '__main__':
    main()
