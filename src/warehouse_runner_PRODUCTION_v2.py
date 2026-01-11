#!/usr/bin/env python3
"""
Warehouse Runner Production Scraper v2 - With Location Intelligence
Integrated with CostcoGeocoder for complete warehouse location enrichment

This is a REFERENCE IMPLEMENTATION showing how to integrate the geocoder
with any Costco markdown scraper.

Part of Agent Taskforce TF-2026-001-LOCATION
"""

import json
from typing import Dict, List
from pathlib import Path

# Import the geocoder
from costco_geocoder import CostcoGeocoder


class WarehouseRunnerV2:
    """
    Production markdown scraper with integrated location intelligence.

    Enhancement over v1:
    - State-level data enriched with full warehouse locations
    - Warehouse number arrays expanded to include addresses, ZIPs, cities
    - Geographic distribution analysis
    - Distance calculations for regional pricing patterns
    """

    def __init__(self, geocoder_db_path: str = "D:/Data/costco_warehouses.json"):
        """Initialize scraper with geocoder"""
        self.geocoder = CostcoGeocoder(geocoder_db_path)
        print(f"Initialized with {self.geocoder.get_statistics()['total_warehouses']} warehouses")

    def scrape_product(self, product_id: str) -> dict:
        """
        Scrape product markdown data (placeholder for actual scraping logic)

        In production, this would:
        1. Fetch from Warehouse Runner API/website
        2. Extract markdown data
        3. Parse state pricing and warehouse numbers

        Returns:
            Product data dictionary with markdown information
        """
        # PLACEHOLDER - Replace with actual scraping logic
        # This simulates what the scraper would return
        return {
            "product_id": product_id,
            "name": "Example Product",
            "markdown_type": "regional_discount",
            "state_pricing": {
                "CA": {"count": 28, "price_min": 4.97, "price_max": 5.97},
                "TX": {"count": 12, "price_min": 6.47, "price_max": 6.47},
                "WA": {"count": 5, "price_min": 5.47, "price_max": 5.47}
            },
            "warehouse_numbers": [428, 401, 469, 578, 148, 692, 731],
            "insights": {
                "days_remaining": 14,
                "discount_amount": 3.00,
                "original_price": 8.97
            }
        }

    def enrich_product_data(self, product_data: dict) -> dict:
        """
        Enrich product data with full warehouse location intelligence

        Transformations:
        1. state_pricing: Add 'warehouses' array with full location data
        2. warehouse_numbers: Expand to full warehouse objects
        3. Add geographic_analysis section
        """
        enriched = product_data.copy()

        # Enrich state pricing
        if "state_pricing" in product_data:
            enriched["state_pricing_enriched"] = self.geocoder.enrich_state_pricing(
                product_data["state_pricing"]
            )

        # Enrich warehouse numbers
        if "warehouse_numbers" in product_data:
            enriched["warehouse_locations"] = self.geocoder.enrich_warehouse_numbers(
                product_data["warehouse_numbers"]
            )

        # Add geographic analysis
        enriched["geographic_analysis"] = self._analyze_geographic_distribution(
            enriched.get("warehouse_locations", [])
        )

        return enriched

    def _analyze_geographic_distribution(self, warehouse_locations: List[dict]) -> dict:
        """
        Analyze geographic distribution of warehouses

        Returns:
            Analysis with state breakdown, city counts, coordinate bounds
        """
        if not warehouse_locations:
            return {}

        states = {}
        cities = set()
        lats = []
        lons = []

        for wh in warehouse_locations:
            if wh.get('state'):
                states[wh['state']] = states.get(wh['state'], 0) + 1
            if wh.get('city'):
                cities.add(wh['city'])
            if wh.get('latitude'):
                lats.append(wh['latitude'])
            if wh.get('longitude'):
                lons.append(wh['longitude'])

        analysis = {
            "total_warehouses": len(warehouse_locations),
            "states": dict(sorted(states.items())),
            "unique_cities": len(cities),
            "city_list": sorted(list(cities))
        }

        if lats and lons:
            analysis["geographic_bounds"] = {
                "north": max(lats),
                "south": min(lats),
                "east": max(lons),
                "west": min(lons)
            }
            analysis["center_point"] = {
                "latitude": sum(lats) / len(lats),
                "longitude": sum(lons) / len(lons)
            }

        return analysis

    def export_to_markdown(self, enriched_data: dict, output_path: str):
        """
        Export enriched data to markdown format

        Format:
        - Product header
        - Markdown details
        - Warehouse locations table
        - Geographic distribution map
        """
        lines = []

        # Header
        lines.append(f"# {enriched_data.get('name', 'Product')} - Markdown Report")
        lines.append(f"**Product ID:** {enriched_data.get('product_id', 'N/A')}")
        lines.append(f"**Markdown Type:** {enriched_data.get('markdown_type', 'N/A')}")
        lines.append("")

        # Insights
        if "insights" in enriched_data:
            insights = enriched_data["insights"]
            lines.append("## Markdown Details")
            lines.append(f"- **Days Remaining:** {insights.get('days_remaining', 'N/A')}")
            lines.append(f"- **Discount Amount:** ${insights.get('discount_amount', 0):.2f}")
            lines.append(f"- **Original Price:** ${insights.get('original_price', 0):.2f}")
            lines.append("")

        # Warehouse Locations
        if "warehouse_locations" in enriched_data:
            lines.append("## Warehouse Locations")
            lines.append("")
            lines.append("| # | Name | Address | City | State | ZIP | Coordinates |")
            lines.append("|---|------|---------|------|-------|-----|-------------|")

            for wh in enriched_data["warehouse_locations"]:
                lines.append(
                    f"| {wh['warehouse_number']} "
                    f"| {wh['name']} "
                    f"| {wh['address']} "
                    f"| {wh['city']} "
                    f"| {wh['state']} "
                    f"| {wh['zip']} "
                    f"| {wh.get('latitude', 'N/A')}, {wh.get('longitude', 'N/A')} |"
                )
            lines.append("")

        # Geographic Analysis
        if "geographic_analysis" in enriched_data:
            geo = enriched_data["geographic_analysis"]
            lines.append("## Geographic Distribution")
            lines.append(f"- **Total Warehouses:** {geo.get('total_warehouses', 0)}")
            lines.append(f"- **States Covered:** {len(geo.get('states', {}))}")
            lines.append(f"- **Unique Cities:** {geo.get('unique_cities', 0)}")

            if "states" in geo:
                lines.append("")
                lines.append("**Warehouses by State:**")
                for state, count in geo["states"].items():
                    lines.append(f"- {state}: {count} warehouses")

            if "center_point" in geo:
                center = geo["center_point"]
                lines.append("")
                lines.append(f"**Geographic Center:** {center['latitude']:.4f}, {center['longitude']:.4f}")

            lines.append("")

        # State Pricing (Enriched)
        if "state_pricing_enriched" in enriched_data:
            lines.append("## State Pricing Details")
            lines.append("")

            for state, data in enriched_data["state_pricing_enriched"].items():
                lines.append(f"### {state}")
                lines.append(f"- **Warehouse Count:** {data.get('count', 0)}")
                lines.append(f"- **Price Range:** ${data.get('price_min', 0):.2f} - ${data.get('price_max', 0):.2f}")

                if "warehouses" in data and data["warehouses"]:
                    wh_numbers = ', '.join(f"#{w['warehouse_number']}" for w in data['warehouses'][:5])
                    lines.append(f"- **Warehouses:** {wh_numbers}")
                    if len(data["warehouses"]) > 5:
                        lines.append(f"  (...and {len(data['warehouses']) - 5} more)")
                lines.append("")

        # Write to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"Exported markdown report to {output_path}")

    def export_to_json(self, enriched_data: dict, output_path: str):
        """Export enriched data to JSON format"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        print(f"Exported JSON data to {output_path}")


def main():
    """Demonstration of the integrated scraper"""
    print("=" * 70)
    print("Warehouse Runner Production v2 - Location Intelligence Integration")
    print("=" * 70)
    print()

    # Initialize scraper
    scraper = WarehouseRunnerV2()

    # Scrape product (placeholder - would be real scraping in production)
    product_id = "1271581"  # Test product from mission brief
    print(f"Scraping product {product_id}...")
    product_data = scraper.scrape_product(product_id)

    # Enrich with location intelligence
    print("Enriching with location intelligence...")
    enriched_data = scraper.enrich_product_data(product_data)

    # Export results
    output_dir = Path("D:/Data/markdown_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / f"{product_id}_enriched.md"
    json_path = output_dir / f"{product_id}_enriched.json"

    scraper.export_to_markdown(enriched_data, str(markdown_path))
    scraper.export_to_json(enriched_data, str(json_path))

    # Print summary
    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    geo = enriched_data.get("geographic_analysis", {})
    print(f"Total Warehouses: {geo.get('total_warehouses', 0)}")
    print(f"States Covered: {len(geo.get('states', {}))}")
    print(f"Unique Cities: {geo.get('unique_cities', 0)}")

    if "warehouse_locations" in enriched_data:
        print("\nSample Warehouse Locations:")
        for wh in enriched_data["warehouse_locations"][:3]:
            print(f"  #{wh['warehouse_number']} {wh['name']}, {wh['city']}, {wh['state']}")

    print()
    print(f"Full results: {markdown_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
