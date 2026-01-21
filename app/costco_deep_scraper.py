#!/usr/bin/env python3
"""
Costco Deep Scraper - DeadMan AI Research
==========================================
Purpose: Deep scraping for Costco markdown prices, clearance, and upcoming deals
Author: DeadMan AI Research Team
Date: 2026-01-10

Targets:
- Markdown prices (.97, .00, .88)
- Discontinued items (asterisk indicator)
- Warehouse savings/instant savings
- Upcoming coupon book deals

Capabilities:
- Multi-layer scraping (browser, curl-cffi, TOR fallback)
- Anti-bot detection bypass
- Intelligent price pattern recognition
- Product availability tracking
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

# Import our ultimate scraper
from ULTIMATE_UNIFIED_SCRAPER_FIXED import UltimateScraperEngine, BehavioralSimulator


class CostcoMarkdownDetector:
    """Detects and classifies Costco price markdowns"""

    # Markdown price patterns
    CLEARANCE_MARKDOWN = r'\.97$'      # .97 = Manager markdown
    SPECIAL_MARKDOWN = r'\.(00|88)$'   # .00/.88 = Special markdown
    STANDARD_PRICE = r'\.99$'          # .99 = No discount

    # Product indicators
    DISCONTINUED_MARKER = '*'  # Asterisk on price tag

    @staticmethod
    def classify_price(price_str: str) -> Dict[str, any]:
        """
        Classify a Costco price and return markdown information

        Returns:
            {
                'price': float,
                'type': 'clearance' | 'special' | 'standard',
                'is_markdown': bool,
                'markdown_type': str,
                'savings_potential': str
            }
        """
        # Extract numeric price
        price_match = re.search(r'\$?(\d+\.\d{2})', price_str)
        if not price_match:
            return None

        price = float(price_match.group(1))
        price_str_clean = f"{price:.2f}"

        result = {
            'price': price,
            'price_str': f"${price_str_clean}"
        }

        # Check for clearance (.97)
        if re.search(CostcoMarkdownDetector.CLEARANCE_MARKDOWN, price_str_clean):
            result.update({
                'type': 'clearance',
                'is_markdown': True,
                'markdown_type': 'Manager Clearance',
                'savings_potential': 'HIGH - Store-specific markdown',
                'indicator': '.97'
            })

        # Check for special markdown (.00/.88)
        elif re.search(CostcoMarkdownDetector.SPECIAL_MARKDOWN, price_str_clean):
            result.update({
                'type': 'special',
                'is_markdown': True,
                'markdown_type': 'Special In-Store Markdown',
                'savings_potential': 'MEDIUM - Location-specific deal',
                'indicator': '.00/.88'
            })

        # Standard price (.99)
        elif re.search(CostcoMarkdownDetector.STANDARD_PRICE, price_str_clean):
            result.update({
                'type': 'standard',
                'is_markdown': False,
                'markdown_type': 'Standard Pricing',
                'savings_potential': 'LOW - No further discounts expected',
                'indicator': '.99'
            })

        else:
            result.update({
                'type': 'unknown',
                'is_markdown': False,
                'markdown_type': 'Unknown',
                'savings_potential': 'UNKNOWN',
                'indicator': 'N/A'
            })

        return result


class CostcoProductExtractor:
    """Extracts product data from Costco HTML"""

    def __init__(self):
        self.markdown_detector = CostcoMarkdownDetector()

    def extract_products(self, html: str) -> List[Dict]:
        """Extract all products from Costco page HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []

        # Find product containers (Costco uses various selectors)
        product_selectors = [
            'div.product',
            'div[class*="product"]',
            'div.product-tile',
            'div[class*="item"]',
            'article.product',
            'div[data-automation="productTile"]'
        ]

        for selector in product_selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    product = self._extract_product_data(item)
                    if product:
                        products.append(product)
                break

        return products

    def _extract_product_data(self, item) -> Optional[Dict]:
        """Extract data from a single product element"""
        try:
            # Extract product name
            name_selectors = ['h2', 'h3', '.description', '[class*="title"]', '[class*="name"]']
            name = None
            for sel in name_selectors:
                elem = item.select_one(sel)
                if elem:
                    name = elem.get_text(strip=True)
                    break

            if not name:
                return None

            # Extract price
            price_selectors = [
                '.price',
                '[class*="price"]',
                'span[class*="value"]',
                '.your-price',
                '[data-automation="itemPrice"]'
            ]
            price_text = None
            for sel in price_selectors:
                elem = item.select_one(sel)
                if elem:
                    price_text = elem.get_text(strip=True)
                    break

            if not price_text:
                return None

            # Classify price
            price_info = self.markdown_detector.classify_price(price_text)
            if not price_info:
                return None

            # Check for discontinued marker (asterisk)
            html_str = str(item)
            is_discontinued = '*' in html_str or 'discontinued' in html_str.lower() or 'limited' in html_str.lower()

            # Extract item number if available
            item_num_match = re.search(r'item[#\s]?(\d+)', str(item), re.IGNORECASE)
            item_number = item_num_match.group(1) if item_num_match else None

            # Extract availability
            availability = 'In Stock'
            if 'out of stock' in html_str.lower():
                availability = 'Out of Stock'
            elif 'low stock' in html_str.lower():
                availability = 'Low Stock'

            return {
                'name': name,
                'item_number': item_number,
                'price_info': price_info,
                'is_discontinued': is_discontinued,
                'availability': availability,
                'extracted_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[ERROR] Failed to extract product: {e}")
            return None


class CostcoDeepScraper:
    """Main Costco scraping orchestrator"""

    def __init__(self):
        self.scraper = UltimateScraperEngine(
            use_proxy=True,
            proxy_type='residential',
            use_tor=False,
            captcha_solving=True,
            behavioral_simulation=True
        )
        self.extractor = CostcoProductExtractor()
        self.output_dir = Path(__file__).parent.parent / "Research" / "Costco_Intelligence"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def scrape_costco_section(self, url: str, section_name: str) -> Dict:
        """Scrape a specific Costco section"""
        print(f"\n{'='*80}")
        print(f"[COSTCO] Scraping section: {section_name}")
        print(f"[URL] {url}")
        print(f"{'='*80}\n")

        # Scrape with adaptive method
        result = self.scraper.adaptive_scrape(url)

        if not result:
            print(f"[ERROR] Failed to scrape {section_name}")
            return None

        # Extract products
        products = self.extractor.extract_products(result.get('html', ''))

        # Analyze markdowns
        markdown_summary = self._analyze_markdowns(products)

        return {
            'section': section_name,
            'url': url,
            'products': products,
            'markdown_summary': markdown_summary,
            'total_products': len(products),
            'scraped_at': datetime.now().isoformat()
        }

    def _analyze_markdowns(self, products: List[Dict]) -> Dict:
        """Analyze markdown distribution"""
        summary = {
            'clearance_count': 0,
            'special_markdown_count': 0,
            'discontinued_count': 0,
            'best_deals': []
        }

        for product in products:
            price_info = product.get('price_info', {})

            if price_info.get('type') == 'clearance':
                summary['clearance_count'] += 1
                summary['best_deals'].append({
                    'name': product['name'],
                    'price': price_info['price_str'],
                    'type': 'Clearance (.97)',
                    'savings_potential': 'HIGH'
                })

            elif price_info.get('type') == 'special':
                summary['special_markdown_count'] += 1
                summary['best_deals'].append({
                    'name': product['name'],
                    'price': price_info['price_str'],
                    'type': 'Special Markdown (.00/.88)',
                    'savings_potential': 'MEDIUM'
                })

            if product.get('is_discontinued'):
                summary['discontinued_count'] += 1

        # Sort best deals by savings potential
        summary['best_deals'] = sorted(
            summary['best_deals'],
            key=lambda x: 0 if x['savings_potential'] == 'HIGH' else 1
        )[:20]  # Top 20 deals

        return summary

    def scrape_all_sections(self) -> Dict:
        """Scrape all target Costco sections"""

        # Define target sections
        targets = [
            ('https://www.costco.com/warehouse-savings.html', 'Warehouse Savings'),
            ('https://www.costco.com/instant-savings.html', 'Instant Savings'),
            ('https://www.costco.com/clearance.html', 'Clearance'),
            ('https://www.costco.com/', 'Homepage - Featured Deals'),
            ('https://www.costco.com/hot-buys.html', 'Hot Buys'),
        ]

        all_results = []

        for url, section in targets:
            try:
                result = self.scrape_costco_section(url, section)
                if result:
                    all_results.append(result)

                # Human-like delay between sections
                BehavioralSimulator.human_delay(5.0, 10.0)

            except Exception as e:
                print(f"[ERROR] Failed to scrape {section}: {e}")
                continue

        # Aggregate results
        final_report = self._generate_final_report(all_results)

        return final_report

    def _generate_final_report(self, results: List[Dict]) -> Dict:
        """Generate comprehensive final report"""

        total_products = sum(r['total_products'] for r in results)
        total_clearance = sum(r['markdown_summary']['clearance_count'] for r in results)
        total_special = sum(r['markdown_summary']['special_markdown_count'] for r in results)
        total_discontinued = sum(r['markdown_summary']['discontinued_count'] for r in results)

        # Collect all best deals across sections
        all_best_deals = []
        for r in results:
            for deal in r['markdown_summary']['best_deals']:
                deal['section'] = r['section']
                all_best_deals.append(deal)

        # Sort by savings potential
        all_best_deals = sorted(
            all_best_deals,
            key=lambda x: 0 if x['savings_potential'] == 'HIGH' else 1
        )[:50]  # Top 50 deals overall

        report = {
            'report_type': 'Costco Deep Intelligence Report',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_sections_scraped': len(results),
                'total_products_found': total_products,
                'clearance_items': total_clearance,
                'special_markdowns': total_special,
                'discontinued_items': total_discontinued,
                'markdown_rate': f"{((total_clearance + total_special) / total_products * 100):.1f}%" if total_products > 0 else "0%"
            },
            'top_deals': all_best_deals,
            'section_results': results
        }

        return report

    def save_report(self, report: Dict):
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"costco_deep_intelligence_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print(f"[REPORT SAVED] {filepath}")
        print(f"{'='*80}\n")

        return filepath

    def print_summary(self, report: Dict):
        """Print human-readable summary"""
        summary = report['summary']

        print(f"\n{'='*80}")
        print(f"COSTCO DEEP INTELLIGENCE SUMMARY")
        print(f"{'='*80}")
        print(f"Generated: {report['generated_at']}")
        print(f"\nOverall Statistics:")
        print(f"  Total Sections Scraped:  {summary['total_sections_scraped']}")
        print(f"  Total Products Found:    {summary['total_products_found']}")
        print(f"  Clearance Items (.97):   {summary['clearance_items']}")
        print(f"  Special Markdowns:       {summary['special_markdowns']}")
        print(f"  Discontinued Items:      {summary['discontinued_items']}")
        print(f"  Markdown Rate:           {summary['markdown_rate']}")

        print(f"\nTop 10 Deals:")
        for i, deal in enumerate(report['top_deals'][:10], 1):
            print(f"  {i}. {deal['name']}")
            print(f"     Price: {deal['price']} | Type: {deal['type']} | Section: {deal['section']}")

        print(f"{'='*80}\n")

    def close(self):
        """Cleanup resources"""
        self.scraper.close()


def main():
    """Main execution"""
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║     COSTCO DEEP SCRAPER - DeadMan AI Research            ║
    ║                                                          ║
    ║  Target: Costco Markdown Intelligence                    ║
    ║  Focus: .97, .00, .88 prices + Discontinued items        ║
    ║  Method: Multi-layer adaptive scraping                   ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    scraper = CostcoDeepScraper()

    try:
        # Execute deep scrape
        report = scraper.scrape_all_sections()

        # Save report
        filepath = scraper.save_report(report)

        # Print summary
        scraper.print_summary(report)

        print(f"[SUCCESS] Full report saved to: {filepath}")

        return report

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Scraping stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
