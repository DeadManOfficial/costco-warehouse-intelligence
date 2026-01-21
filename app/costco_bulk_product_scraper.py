#!/usr/bin/env python3
"""
Costco Bulk Product Scraper - Using Sitemap URLs
=================================================
The REAL dirty work: Scrape all product URLs from sitemap for prices/markdowns
"""

import json
import re
import time
from pathlib import Path
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup


def load_product_urls():
    """Load product URLs from sitemap file"""
    sitemap_file = Path(__file__).parent.parent / "Research" / "Costco_Intelligence" / "product_urls_from_sitemap.json"

    with open(sitemap_file, 'r') as f:
        data = json.load(f)
        return data['urls']


def scrape_product_page(url):
    """Scrape a single product page"""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        response = curl_requests.get(
            url,
            headers=headers,
            impersonate="chrome120",
            timeout=30
        )

        if response.status_code != 200:
            return {'url': url, 'status': 'blocked', 'status_code': response.status_code}

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data
        product = {'url': url, 'status': 'success'}

        # Product name from title or h1
        title_elem = soup.find('h1')
        if title_elem:
            product['name'] = title_elem.get_text(strip=True)
        else:
            title_tag = soup.find('title')
            if title_tag:
                product['name'] = title_tag.get_text(strip=True)

        # Price - look for various patterns
        price_patterns = [
            (r'\$[\d,]+\.\d{2}', 'regex'),
            ('data-price', 'attribute'),
            ('price', 'class'),
            ('your-price', 'class'),
        ]

        for pattern, method in price_patterns:
            if method == 'regex':
                price_match = re.search(pattern, response.text)
                if price_match:
                    price = price_match.group()
                    product['price'] = price

                    # Markdown detection
                    if '.97' in price:
                        product['markdown_type'] = 'CLEARANCE'
                        product['savings_potential'] = 'HIGH'
                    elif '.00' in price or '.88' in price:
                        product['markdown_type'] = 'SPECIAL'
                        product['savings_potential'] = 'MEDIUM'
                    else:
                        product['markdown_type'] = 'STANDARD'
                        product['savings_potential'] = 'LOW'
                    break
            elif method == 'attribute':
                price_elem = soup.find(attrs={pattern: True})
                if price_elem:
                    product['price'] = price_elem.get(pattern)
                    break
            elif method == 'class':
                price_elem = soup.find(class_=re.compile(pattern, re.IGNORECASE))
                if price_elem:
                    product['price'] = price_elem.get_text(strip=True)
                    break

        # Product ID from URL
        id_match = re.search(r'\.product\.(\d+)\.html', url)
        if id_match:
            product['id'] = id_match.group(1)

        return product

    except Exception as e:
        return {'url': url, 'status': 'error', 'error': str(e)}


def main():
    """Scrape all product URLs"""

    print("="*80)
    print("COSTCO BULK PRODUCT SCRAPER - SITEMAP URLs")
    print("="*80)

    # Load URLs
    urls = load_product_urls()
    print(f"\nLoaded {len(urls)} product URLs from sitemap")

    # Scrape first 50 (to be respectful)
    print(f"Scraping first 50 products...")

    products = []
    clearance_found = []

    for i, url in enumerate(urls[:50], 1):
        print(f"\n[{i}/50] {url}")

        product = scrape_product_page(url)

        if product['status'] == 'success':
            print(f"  Name: {product.get('name', 'N/A')[:60]}")
            print(f"  Price: {product.get('price', 'N/A')}")
            print(f"  Markdown: {product.get('markdown_type', 'N/A')}")

            products.append(product)

            if product.get('markdown_type') == 'CLEARANCE':
                clearance_found.append(product)
        else:
            print(f"  Status: {product['status']}")

        # Be polite - wait between requests
        time.sleep(2)

    # Save results
    output_dir = Path(__file__).parent.parent / "Research" / "Costco_Intelligence"
    output_file = output_dir / "bulk_product_scrape_results.json"

    results = {
        'total_scraped': len(products),
        'clearance_count': len(clearance_found),
        'clearance_products': clearance_found,
        'all_products': products
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")
    print(f"Products scraped: {len(products)}")
    print(f"Clearance items (.97): {len(clearance_found)}")

    if clearance_found:
        print("\nCLEARANCE DEALS FOUND:")
        for product in clearance_found:
            print(f"  - {product.get('name', 'Unknown')[:60]}")
            print(f"    Price: {product.get('price', 'N/A')} | ID: {product.get('id', 'N/A')}")

    print(f"\nSaved: {output_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
