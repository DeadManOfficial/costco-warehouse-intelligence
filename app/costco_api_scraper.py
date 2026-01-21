#!/usr/bin/env python3
"""
Costco API Scraper - Endpoint Discovery & JSON Extraction
===========================================================
Purpose: Bypass HTML scraping by finding and using Costco's internal APIs
Author: DeadMan AI Research Team
Date: 2026-01-10

Strategy:
- Most e-commerce sites use JSON APIs for product listings
- These APIs are often less protected than HTML pages
- Extract clean JSON data instead of parsing messy HTML
- Use realistic browser headers to avoid detection

Based on common e-commerce patterns, Costco likely uses:
- /api/products
- /search/v1/
- /catalog/v2/
- GraphQL endpoints
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from curl_cffi import requests as curl_requests


class CostcoAPIDiscovery:
    """Discovers and uses Costco's internal API endpoints"""

    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "Research" / "Costco_Intelligence"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Realistic Chrome 120 headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.costco.com/',
            'Origin': 'https://www.costco.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }

    def try_api_endpoint(self, url: str) -> Optional[Dict]:
        """Try fetching from a potential API endpoint"""
        try:
            print(f"[API] Trying: {url}")

            response = curl_requests.get(
                url,
                headers=self.headers,
                impersonate="chrome120",
                timeout=30,
                allow_redirects=True
            )

            # Check if response is JSON
            try:
                data = response.json()
                print(f"[SUCCESS] Found JSON API at: {url}")
                print(f"[DATA] Response keys: {list(data.keys())[:10]}")
                return data
            except:
                # Not JSON, might be HTML
                if len(response.text) < 1000:
                    print(f"[INFO] Response too short ({len(response.text)} bytes)")
                else:
                    print(f"[INFO] HTML response ({len(response.text)} bytes), not JSON API")
                return None

        except Exception as e:
            print(f"[ERROR] {url}: {e}")
            return None

    def discover_api_endpoints(self) -> List[str]:
        """Discover Costco's API endpoints"""
        print("\n" + "="*80)
        print("COSTCO API ENDPOINT DISCOVERY")
        print("="*80 + "\n")

        # Common API endpoint patterns
        base_urls = [
            "https://www.costco.com",
            "https://api.costco.com",
            "https://mobileareas.costco.com"
        ]

        api_patterns = [
            "/api/products",
            "/api/v1/products",
            "/api/v2/products",
            "/api/search",
            "/api/catalog",
            "/search/v1/",
            "/catalog/v2/",
            "/rest/v2/",
            "/api/warehouse-savings",
            "/api/clearance",
            "/api/instant-savings",
            "/graphql",
            "/wcs/resources/",
        ]

        discovered = []

        for base in base_urls:
            for pattern in api_patterns:
                url = f"{base}{pattern}"
                result = self.try_api_endpoint(url)
                if result:
                    discovered.append(url)
                time.sleep(0.5)  # Be polite

        return discovered

    def scrape_with_realistic_headers(self, url: str) -> Optional[Dict]:
        """Scrape with extremely realistic browser headers"""
        print(f"\n[REALISTIC] Scraping: {url}")

        try:
            # First, get the main page to establish cookies
            print("[STEP 1] Getting homepage to establish session...")
            session_response = curl_requests.get(
                "https://www.costco.com/",
                headers=self.headers,
                impersonate="chrome120",
                timeout=30
            )

            # Extract any cookies
            cookies = session_response.cookies

            # Now scrape the target with cookies
            print(f"[STEP 2] Scraping target with session cookies...")
            response = curl_requests.get(
                url,
                headers=self.headers,
                cookies=cookies,
                impersonate="chrome120",
                timeout=30
            )

            # Save raw HTML for analysis
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_file = self.output_dir / "debug" / f"realistic_{timestamp}.html"
            debug_file.parent.mkdir(parents=True, exist_ok=True)

            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print(f"[DEBUG] Saved to: {debug_file}")
            print(f"[INFO] Response: {len(response.text)} bytes, Status: {response.status_code}")

            # Try to find embedded JSON in HTML
            json_data = self.extract_json_from_html(response.text)

            return {
                'url': url,
                'html': response.text,
                'status_code': response.status_code,
                'json_data': json_data,
                'cookies': dict(cookies),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[ERROR] {e}")
            return None

    def extract_json_from_html(self, html: str) -> List[Dict]:
        """Extract embedded JSON data from HTML (common in modern websites)"""
        print("[EXTRACT] Looking for embedded JSON in HTML...")

        json_patterns = [
            r'<script type="application/json"[^>]*>(.*?)</script>',
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'var\s+productData\s*=\s*({.*?});',
        ]

        found_json = []

        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    found_json.append(data)
                    print(f"[FOUND] Embedded JSON with keys: {list(data.keys())[:5]}")
                except:
                    continue

        return found_json

    def scrape_all_sections(self) -> Dict:
        """Scrape all Costco sections with realistic approach"""
        targets = [
            ('https://www.costco.com/', 'Homepage'),
            ('https://www.costco.com/warehouse-savings.html', 'Warehouse Savings'),
            ('https://www.costco.com/instant-savings.html', 'Instant Savings'),
            ('https://www.costco.com/clearance.html', 'Clearance'),
            ('https://www.costco.com/hot-buys.html', 'Hot Buys'),
        ]

        results = []

        for url, section in targets:
            print(f"\n{'='*80}")
            print(f"[SECTION] {section}")
            print(f"{'='*80}")

            result = self.scrape_with_realistic_headers(url)
            if result:
                results.append({
                    'section': section,
                    **result
                })

            time.sleep(3)  # Human-like delay

        return {
            'scrape_type': 'realistic_headers',
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'total_sections': len(results)
        }

    def save_results(self, data: Dict):
        """Save results to JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"costco_api_results_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print(f"[SAVED] {filepath}")
        print(f"{'='*80}\n")

        return filepath


def main():
    """Main execution"""
    print("="*80)
    print("COSTCO API SCRAPER - DeadMan AI Research")
    print("="*80)
    print("Strategy: Find & use internal API endpoints")
    print("Fallback: Realistic headers + embedded JSON extraction")
    print("="*80)
    print()

    scraper = CostcoAPIDiscovery()

    # Try to discover API endpoints
    discovered = scraper.discover_api_endpoints()

    if discovered:
        print(f"\n[SUCCESS] Discovered {len(discovered)} API endpoints!")
        for endpoint in discovered:
            print(f"  - {endpoint}")
    else:
        print("\n[INFO] No API endpoints discovered, using HTML + embedded JSON approach")

    # Scrape all sections
    results = scraper.scrape_all_sections()

    # Save results
    filepath = scraper.save_results(results)

    print(f"\n[COMPLETE] Results saved to: {filepath}")
    print(f"[NEXT] Check debug HTML files and extracted JSON data")
    print(f"[LOCATION] {scraper.output_dir / 'debug'}")


if __name__ == "__main__":
    main()
