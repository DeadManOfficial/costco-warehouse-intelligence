#!/usr/bin/env python3
"""
Costco Warehouse Geocoder - Integration Layer
Provides warehouse location lookup, enrichment, and reverse geocoding capabilities
for the Warehouse Runner production scraper.

Part of Agent Taskforce TF-2026-001-LOCATION
"""

import json
import sys
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

# Windows encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


@dataclass
class WarehouseLocation:
    """Costco warehouse location data"""
    number: int
    name: str
    address: str
    city: str
    state: str
    zip: str
    lat: float
    lon: float
    phone: Optional[str] = None

    def __str__(self):
        return f"#{self.number} {self.name}, {self.city}, {self.state}"

    def full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip}"

    def to_dict(self):
        return {
            'warehouse_number': self.number,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'latitude': self.lat,
            'longitude': self.lon,
            'phone': self.phone
        }


class CostcoGeocoder:
    """
    Warehouse location lookup and enrichment engine.

    Features:
    - Lookup by warehouse number
    - Search by city/state
    - Reverse geocoding (lat/lon -> warehouse)
    - State-based filtering
    - Distance calculations
    """

    def __init__(self, database_path: str = "D:/DeadMan_AI_Research/Data/costco_warehouses_master.json"):
        """Initialize geocoder with warehouse database"""
        self.database_path = database_path
        self.warehouses: Dict[int, WarehouseLocation] = {}
        self._state_index: Dict[str, List[int]] = {}
        self._city_index: Dict[str, List[int]] = {}

        self._load_database()
        self._build_indexes()

    def _load_database(self):
        """Load warehouse database from JSON"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle master database format (has 'warehouses' key)
            if 'warehouses' in data:
                warehouse_data = data['warehouses']
            else:
                warehouse_data = data

            for num_str, info in warehouse_data.items():
                num = int(num_str)

                # Skip records missing core fields (lat/lon optional now)
                if not all(key in info for key in ['name', 'city', 'state']):
                    continue

                self.warehouses[num] = WarehouseLocation(
                    number=num,
                    name=info['name'],
                    address=info.get('address', ''),
                    city=info['city'],
                    state=info['state'],
                    zip=info.get('zip', ''),
                    lat=info.get('lat', 0.0),
                    lon=info.get('lon', 0.0),
                    phone=info.get('phone')
                )

            print(f"Loaded {len(self.warehouses)} warehouses from {self.database_path}")

        except FileNotFoundError:
            print(f"ERROR: Database not found at {self.database_path}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR loading database: {e}")
            sys.exit(1)

    def _build_indexes(self):
        """Build lookup indexes for fast searching"""
        for num, wh in self.warehouses.items():
            # State index
            if wh.state:
                if wh.state not in self._state_index:
                    self._state_index[wh.state] = []
                self._state_index[wh.state].append(num)

            # City index (normalized)
            if wh.city:
                city_key = wh.city.lower().strip()
                if city_key not in self._city_index:
                    self._city_index[city_key] = []
                self._city_index[city_key].append(num)

    # ========== Lookup Methods ==========

    def get_warehouse(self, warehouse_number: int) -> Optional[WarehouseLocation]:
        """Get warehouse by number"""
        return self.warehouses.get(warehouse_number)

    def get_warehouses_by_state(self, state_code: str) -> List[WarehouseLocation]:
        """Get all warehouses in a state"""
        state_upper = state_code.upper()
        warehouse_nums = self._state_index.get(state_upper, [])
        return [self.warehouses[num] for num in warehouse_nums]

    def get_warehouses_by_city(self, city: str, state: Optional[str] = None) -> List[WarehouseLocation]:
        """Get warehouses by city name (optionally filtered by state)"""
        city_key = city.lower().strip()
        warehouse_nums = self._city_index.get(city_key, [])
        warehouses = [self.warehouses[num] for num in warehouse_nums]

        if state:
            state_upper = state.upper()
            warehouses = [wh for wh in warehouses if wh.state == state_upper]

        return warehouses

    def search_warehouses(self, query: str) -> List[WarehouseLocation]:
        """
        Search warehouses by name, city, or warehouse number
        Returns list of matching warehouses
        """
        query_lower = query.lower().strip()
        results = []

        # Check if query is a number
        if query.isdigit():
            wh = self.get_warehouse(int(query))
            if wh:
                return [wh]

        # Search by name and city
        for wh in self.warehouses.values():
            if (query_lower in wh.name.lower() or
                query_lower in wh.city.lower() or
                query_lower in wh.address.lower()):
                results.append(wh)

        return results

    # ========== Reverse Geocoding ==========

    def find_nearest_warehouse(self, lat: float, lon: float) -> Optional[WarehouseLocation]:
        """Find nearest warehouse to given coordinates"""
        if not self.warehouses:
            return None

        min_distance = float('inf')
        nearest = None

        for wh in self.warehouses.values():
            distance = self._haversine_distance(lat, lon, wh.lat, wh.lon)
            if distance < min_distance:
                min_distance = distance
                nearest = wh

        return nearest

    def find_warehouses_within_radius(self, lat: float, lon: float,
                                      radius_miles: float) -> List[Tuple[WarehouseLocation, float]]:
        """
        Find all warehouses within radius (miles) of coordinates
        Returns list of (warehouse, distance_miles) tuples, sorted by distance
        """
        results = []

        for wh in self.warehouses.values():
            distance = self._haversine_distance(lat, lon, wh.lat, wh.lon)
            if distance <= radius_miles:
                results.append((wh, distance))

        # Sort by distance
        results.sort(key=lambda x: x[1])
        return results

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in miles
        """
        R = 3959.0  # Earth radius in miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    # ========== Enrichment Methods ==========

    def enrich_state_pricing(self, state_pricing: Dict[str, dict]) -> Dict[str, dict]:
        """
        Enrich state pricing data with warehouse locations

        Input format:
        {
            "CA": {"count": 28, "price_min": 4.97, "price_max": 5.97},
            "TX": {"count": 12, "price_min": 6.47, "price_max": 6.47}
        }

        Output format: Same as input, plus 'warehouses' array with full location data
        """
        enriched = {}

        for state, pricing_data in state_pricing.items():
            warehouses = self.get_warehouses_by_state(state)
            enriched[state] = {
                **pricing_data,
                'warehouses': [wh.to_dict() for wh in warehouses]
            }

        return enriched

    def enrich_warehouse_numbers(self, warehouse_numbers: List[int]) -> List[dict]:
        """
        Enrich list of warehouse numbers with full location data
        Returns list of warehouse dictionaries
        """
        enriched = []

        for num in warehouse_numbers:
            wh = self.get_warehouse(num)
            if wh:
                enriched.append(wh.to_dict())
            else:
                # Warehouse not in database
                enriched.append({
                    'warehouse_number': num,
                    'name': 'Unknown',
                    'address': '',
                    'city': '',
                    'state': '',
                    'zip': '',
                    'latitude': None,
                    'longitude': None,
                    'phone': None,
                    'note': 'Not found in database'
                })

        return enriched

    # ========== Statistics ==========

    def get_statistics(self) -> dict:
        """Get database statistics"""
        states = {}
        for wh in self.warehouses.values():
            if wh.state:
                states[wh.state] = states.get(wh.state, 0) + 1

        return {
            'total_warehouses': len(self.warehouses),
            'states_covered': len(states),
            'warehouses_by_state': dict(sorted(states.items())),
            'warehouses_with_phone': sum(1 for wh in self.warehouses.values() if wh.phone),
            'coverage_percentage': round(len(self.warehouses) / 600 * 100, 1)
        }


# ========== CLI Interface ==========

def main():
    """Command-line interface for geocoder"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Costco Warehouse Geocoder - Location Lookup Tool'
    )
    parser.add_argument(
        'command',
        choices=['lookup', 'search', 'state', 'city', 'nearest', 'stats', 'enrich'],
        help='Command to execute'
    )
    parser.add_argument(
        'args',
        nargs='*',
        help='Command arguments'
    )
    parser.add_argument(
        '-d', '--database',
        default='D:/Data/costco_warehouses.json',
        help='Path to warehouse database'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    args = parser.parse_args()

    # Initialize geocoder
    geocoder = CostcoGeocoder(args.database)

    # Execute command
    if args.command == 'lookup':
        if not args.args:
            print("Usage: costco_geocoder.py lookup <warehouse_number>")
            sys.exit(1)

        wh = geocoder.get_warehouse(int(args.args[0]))
        if wh:
            if args.json:
                print(json.dumps(wh.to_dict(), indent=2))
            else:
                print(f"Warehouse {wh}")
                print(f"Address: {wh.full_address()}")
                print(f"Coordinates: {wh.lat}, {wh.lon}")
                if wh.phone:
                    print(f"Phone: {wh.phone}")
        else:
            print(f"Warehouse #{args.args[0]} not found")

    elif args.command == 'search':
        if not args.args:
            print("Usage: costco_geocoder.py search <query>")
            sys.exit(1)

        results = geocoder.search_warehouses(' '.join(args.args))
        if args.json:
            print(json.dumps([wh.to_dict() for wh in results], indent=2))
        else:
            print(f"Found {len(results)} warehouses:")
            for wh in results:
                print(f"  {wh} - {wh.full_address()}")

    elif args.command == 'state':
        if not args.args:
            print("Usage: costco_geocoder.py state <state_code>")
            sys.exit(1)

        warehouses = geocoder.get_warehouses_by_state(args.args[0])
        if args.json:
            print(json.dumps([wh.to_dict() for wh in warehouses], indent=2))
        else:
            print(f"Found {len(warehouses)} warehouses in {args.args[0]}:")
            for wh in sorted(warehouses, key=lambda x: x.number):
                print(f"  {wh}")

    elif args.command == 'city':
        if not args.args:
            print("Usage: costco_geocoder.py city <city_name> [state_code]")
            sys.exit(1)

        city = args.args[0]
        state = args.args[1] if len(args.args) > 1 else None
        warehouses = geocoder.get_warehouses_by_city(city, state)

        if args.json:
            print(json.dumps([wh.to_dict() for wh in warehouses], indent=2))
        else:
            print(f"Found {len(warehouses)} warehouses in {city}:")
            for wh in warehouses:
                print(f"  {wh}")

    elif args.command == 'nearest':
        if len(args.args) < 2:
            print("Usage: costco_geocoder.py nearest <latitude> <longitude> [radius_miles]")
            sys.exit(1)

        lat = float(args.args[0])
        lon = float(args.args[1])

        if len(args.args) >= 3:
            radius = float(args.args[2])
            results = geocoder.find_warehouses_within_radius(lat, lon, radius)
            if args.json:
                print(json.dumps([{**wh.to_dict(), 'distance_miles': round(dist, 2)}
                                  for wh, dist in results], indent=2))
            else:
                print(f"Found {len(results)} warehouses within {radius} miles:")
                for wh, dist in results:
                    print(f"  {wh} - {dist:.2f} miles")
        else:
            wh = geocoder.find_nearest_warehouse(lat, lon)
            if wh:
                dist = geocoder._haversine_distance(lat, lon, wh.lat, wh.lon)
                if args.json:
                    result = wh.to_dict()
                    result['distance_miles'] = round(dist, 2)
                    print(json.dumps(result, indent=2))
                else:
                    print(f"Nearest warehouse: {wh}")
                    print(f"Distance: {dist:.2f} miles")

    elif args.command == 'stats':
        stats = geocoder.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.command == 'enrich':
        # Read JSON from stdin
        import sys
        data = json.load(sys.stdin)

        if 'warehouse_numbers' in data:
            enriched = geocoder.enrich_warehouse_numbers(data['warehouse_numbers'])
        elif 'state_pricing' in data:
            enriched = geocoder.enrich_state_pricing(data['state_pricing'])
        else:
            print("ERROR: Input must contain 'warehouse_numbers' or 'state_pricing'")
            sys.exit(1)

        print(json.dumps(enriched, indent=2))


if __name__ == '__main__':
    main()
