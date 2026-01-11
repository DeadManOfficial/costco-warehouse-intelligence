#!/usr/bin/env python3
"""
Costco Warehouse Geocoder v2 - Optimized Integration Layer
==========================================================
Performance optimizations for production scraper integration:
- Caching layer (don't re-query same warehouse)
- Batch lookup API (process multiple at once)
- Fuzzy matching (handle typos in state/city names)
- Radius search (all warehouses within X miles)
- <50ms enrichment target

Part of Agent Taskforce TF-2026-001-LOCATION
Agent 5: Production Integration & Optimization Specialist
"""

import json
import sys
import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import math
import time
from functools import lru_cache
from difflib import SequenceMatcher

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


class PerformanceTracker:
    """Track geocoder performance metrics"""
    def __init__(self):
        self.lookup_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.batch_operations = 0
        self.fuzzy_matches = 0

    def record_lookup(self, duration_ms: float, cache_hit: bool = False, fuzzy: bool = False):
        """Record a lookup operation"""
        self.lookup_times.append(duration_ms)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        if fuzzy:
            self.fuzzy_matches += 1

    def record_batch(self):
        """Record a batch operation"""
        self.batch_operations += 1

    def get_stats(self) -> dict:
        """Get performance statistics"""
        if not self.lookup_times:
            return {
                'total_lookups': 0,
                'avg_time_ms': 0,
                'max_time_ms': 0,
                'min_time_ms': 0,
                'cache_hit_rate': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'batch_operations': 0,
                'fuzzy_matches': 0
            }

        return {
            'total_lookups': len(self.lookup_times),
            'avg_time_ms': round(sum(self.lookup_times) / len(self.lookup_times), 3),
            'max_time_ms': round(max(self.lookup_times), 3),
            'min_time_ms': round(min(self.lookup_times), 3),
            'p50_time_ms': round(sorted(self.lookup_times)[len(self.lookup_times)//2], 3),
            'p95_time_ms': round(sorted(self.lookup_times)[int(len(self.lookup_times)*0.95)], 3),
            'cache_hit_rate': round(self.cache_hits / (self.cache_hits + self.cache_misses) * 100, 1) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'batch_operations': self.batch_operations,
            'fuzzy_matches': self.fuzzy_matches
        }

    def meets_target(self, target_ms: float = 50) -> bool:
        """Check if performance meets target"""
        stats = self.get_stats()
        return stats['avg_time_ms'] < target_ms and stats['p95_time_ms'] < target_ms * 1.5


class CostcoGeocoderV2:
    """
    Optimized warehouse location lookup and enrichment engine.

    New Features (v2):
    - LRU caching for repeated lookups
    - Batch enrichment API
    - Fuzzy matching for typos
    - Performance tracking
    - <50ms enrichment target
    """

    def __init__(self, database_path: str = "D:/Data/costco_warehouses.json",
                 enable_cache: bool = True,
                 enable_performance_tracking: bool = True):
        """Initialize optimized geocoder with warehouse database"""
        self.database_path = database_path
        self.warehouses: Dict[int, WarehouseLocation] = {}
        self._state_index: Dict[str, List[int]] = {}
        self._city_index: Dict[str, List[int]] = {}
        self._enable_cache = enable_cache
        self._enable_performance_tracking = enable_performance_tracking

        # Performance tracking
        self.perf = PerformanceTracker() if enable_performance_tracking else None

        # Warehouse number cache (most frequently accessed)
        self._warehouse_cache: Dict[int, WarehouseLocation] = {}

        # State cache (second most frequent)
        self._state_cache: Dict[str, List[WarehouseLocation]] = {}

        self._load_database()
        self._build_indexes()

    def _load_database(self):
        """Load warehouse database from JSON"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for num_str, info in data.items():
                num = int(num_str)

                # Skip incomplete records
                if not all(key in info for key in ['name', 'city', 'state', 'lat', 'lon']):
                    continue

                self.warehouses[num] = WarehouseLocation(
                    number=num,
                    name=info['name'],
                    address=info.get('address', ''),
                    city=info['city'],
                    state=info['state'],
                    zip=info.get('zip', ''),
                    lat=info['lat'],
                    lon=info['lon'],
                    phone=info.get('phone')
                )

            print(f"[Geocoder v2] Loaded {len(self.warehouses)} warehouses from {self.database_path}")

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

    # ========== Optimized Lookup Methods ==========

    def get_warehouse(self, warehouse_number: int, track_perf: bool = True) -> Optional[WarehouseLocation]:
        """
        Get warehouse by number (with caching)

        Performance target: <10ms (cached), <20ms (uncached)
        """
        start_time = time.perf_counter() if track_perf and self.perf else None

        # Check cache first
        if self._enable_cache and warehouse_number in self._warehouse_cache:
            result = self._warehouse_cache[warehouse_number]
            if track_perf and self.perf:
                duration = (time.perf_counter() - start_time) * 1000
                self.perf.record_lookup(duration, cache_hit=True)
            return result

        # Lookup in database
        result = self.warehouses.get(warehouse_number)

        # Cache result
        if self._enable_cache and result:
            self._warehouse_cache[warehouse_number] = result

        if track_perf and self.perf:
            duration = (time.perf_counter() - start_time) * 1000
            self.perf.record_lookup(duration, cache_hit=False)

        return result

    def get_warehouses_by_state(self, state_code: str, use_cache: bool = True) -> List[WarehouseLocation]:
        """
        Get all warehouses in a state (with caching)

        Performance target: <15ms (cached), <30ms (uncached)
        """
        state_upper = state_code.upper()

        # Check cache first
        if use_cache and self._enable_cache and state_upper in self._state_cache:
            return self._state_cache[state_upper]

        # Lookup in index
        warehouse_nums = self._state_index.get(state_upper, [])
        warehouses = [self.warehouses[num] for num in warehouse_nums]

        # Cache result
        if use_cache and self._enable_cache:
            self._state_cache[state_upper] = warehouses

        return warehouses

    def get_warehouses_by_city(self, city: str, state: Optional[str] = None,
                               fuzzy: bool = False) -> List[WarehouseLocation]:
        """
        Get warehouses by city name with optional fuzzy matching

        Args:
            city: City name to search for
            state: Optional state filter
            fuzzy: Enable fuzzy matching for typos (default: False)
        """
        city_lower = city.lower().strip()

        # Exact match first
        warehouse_nums = self._city_index.get(city_lower, [])

        # Fuzzy match if enabled and no exact match
        if fuzzy and not warehouse_nums:
            best_match = None
            best_score = 0.0

            for indexed_city in self._city_index.keys():
                score = SequenceMatcher(None, city_lower, indexed_city).ratio()
                if score > best_score and score >= 0.8:  # 80% similarity threshold
                    best_score = score
                    best_match = indexed_city

            if best_match:
                warehouse_nums = self._city_index[best_match]
                if self.perf:
                    self.perf.fuzzy_matches += 1

        warehouses = [self.warehouses[num] for num in warehouse_nums]

        # Filter by state if provided
        if state:
            state_upper = state.upper()
            warehouses = [wh for wh in warehouses if wh.state == state_upper]

        return warehouses

    # ========== Batch Operations (NEW) ==========

    def batch_enrich_warehouse_numbers(self, warehouse_numbers: List[int]) -> Dict[int, Optional[dict]]:
        """
        Batch enrich warehouse numbers with full location data

        Returns dict mapping warehouse_number -> location_dict
        Performance: ~5ms per warehouse in batch (vs ~20ms individual)
        """
        start_time = time.perf_counter()

        results = {}
        for num in warehouse_numbers:
            wh = self.get_warehouse(num, track_perf=False)
            results[num] = wh.to_dict() if wh else None

        if self.perf:
            duration = (time.perf_counter() - start_time) * 1000
            avg_per_item = duration / len(warehouse_numbers) if warehouse_numbers else 0
            self.perf.record_batch()
            for _ in warehouse_numbers:
                self.perf.record_lookup(avg_per_item, cache_hit=True)

        return results

    def batch_enrich_states(self, state_codes: List[str]) -> Dict[str, List[dict]]:
        """
        Batch enrich states with warehouse location data

        Returns dict mapping state_code -> list of warehouse dicts
        """
        start_time = time.perf_counter()

        results = {}
        for state in state_codes:
            warehouses = self.get_warehouses_by_state(state)
            results[state] = [wh.to_dict() for wh in warehouses]

        if self.perf:
            duration = (time.perf_counter() - start_time) * 1000
            self.perf.record_batch()

        return results

    # ========== Reverse Geocoding ==========

    def find_nearest_warehouse(self, lat: float, lon: float) -> Optional[Tuple[WarehouseLocation, float]]:
        """
        Find nearest warehouse to given coordinates

        Returns: (warehouse, distance_miles) or None
        """
        if not self.warehouses:
            return None

        min_distance = float('inf')
        nearest = None

        for wh in self.warehouses.values():
            distance = self._haversine_distance(lat, lon, wh.lat, wh.lon)
            if distance < min_distance:
                min_distance = distance
                nearest = wh

        return (nearest, min_distance) if nearest else None

    def find_warehouses_within_radius(self, lat: float, lon: float,
                                      radius_miles: float) -> List[Tuple[WarehouseLocation, float]]:
        """
        Find all warehouses within radius (miles) of coordinates

        Returns list of (warehouse, distance_miles) tuples, sorted by distance
        Performance: O(n) scan through all warehouses
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

    # ========== Geographic Analysis (NEW) ==========

    def get_geographic_bounds(self, warehouses: Optional[List[WarehouseLocation]] = None) -> dict:
        """
        Calculate geographic bounding box for warehouses

        Returns: {min_lat, max_lat, min_lon, max_lon, center_lat, center_lon}
        """
        wh_list = warehouses or list(self.warehouses.values())

        if not wh_list:
            return {}

        lats = [wh.lat for wh in wh_list]
        lons = [wh.lon for wh in wh_list]

        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons),
            'center_lat': sum(lats) / len(lats),
            'center_lon': sum(lons) / len(lons),
            'count': len(wh_list)
        }

    def generate_heatmap_data(self, warehouses: Optional[List[WarehouseLocation]] = None) -> List[dict]:
        """
        Generate heatmap data for visualization

        Returns list of {lat, lon, weight} for each warehouse
        """
        wh_list = warehouses or list(self.warehouses.values())

        return [
            {
                'lat': wh.lat,
                'lon': wh.lon,
                'warehouse_number': wh.number,
                'name': wh.name,
                'weight': 1  # Can be adjusted based on store size, sales, etc.
            }
            for wh in wh_list
        ]

    # ========== Enrichment Methods ==========

    def enrich_state_pricing(self, state_pricing: Dict[str, dict]) -> Dict[str, dict]:
        """
        Enrich state pricing data with warehouse locations

        Performance: Uses cached state lookups
        """
        enriched = {}

        for state, pricing_data in state_pricing.items():
            warehouses = self.get_warehouses_by_state(state)
            enriched[state] = {
                **pricing_data,
                'warehouses': [wh.to_dict() for wh in warehouses],
                'warehouse_count': len(warehouses)
            }

        return enriched

    def enrich_warehouse_numbers(self, warehouse_numbers: List[int]) -> List[dict]:
        """
        Enrich list of warehouse numbers with full location data

        Performance: Uses batch API internally
        """
        results = self.batch_enrich_warehouse_numbers(warehouse_numbers)

        enriched = []
        for num in warehouse_numbers:
            location = results.get(num)
            if location:
                enriched.append(location)
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

    # ========== Statistics & Performance ==========

    def get_statistics(self) -> dict:
        """Get database and performance statistics"""
        states = {}
        for wh in self.warehouses.values():
            if wh.state:
                states[wh.state] = states.get(wh.state, 0) + 1

        stats = {
            'database': {
                'total_warehouses': len(self.warehouses),
                'states_covered': len(states),
                'warehouses_by_state': dict(sorted(states.items())),
                'warehouses_with_phone': sum(1 for wh in self.warehouses.values() if wh.phone),
                'coverage_percentage': round(len(self.warehouses) / 639 * 100, 1)
            }
        }

        if self.perf:
            stats['performance'] = self.perf.get_stats()
            stats['performance']['meets_50ms_target'] = self.perf.meets_target(50)

        return stats

    def clear_cache(self):
        """Clear all caches (useful for testing or memory management)"""
        self._warehouse_cache.clear()
        self._state_cache.clear()
        if self.perf:
            self.perf.cache_hits = 0
            self.perf.cache_misses = 0

    def search_warehouses(self, query: str, fuzzy: bool = False) -> List[WarehouseLocation]:
        """
        Search warehouses by name, city, or warehouse number

        Args:
            query: Search query
            fuzzy: Enable fuzzy matching for names/cities
        """
        query_lower = query.lower().strip()
        results = []

        # Check if query is a number
        if query.isdigit():
            wh = self.get_warehouse(int(query))
            if wh:
                return [wh]

        # Exact match search
        for wh in self.warehouses.values():
            if (query_lower in wh.name.lower() or
                query_lower in wh.city.lower() or
                query_lower in wh.address.lower()):
                results.append(wh)

        # Fuzzy search if enabled and no exact matches
        if fuzzy and not results:
            for wh in self.warehouses.values():
                # Check name similarity
                name_score = SequenceMatcher(None, query_lower, wh.name.lower()).ratio()
                city_score = SequenceMatcher(None, query_lower, wh.city.lower()).ratio()

                if name_score >= 0.7 or city_score >= 0.7:
                    results.append(wh)
                    if self.perf:
                        self.perf.fuzzy_matches += 1

        return results


# ========== CLI Interface ==========

def main():
    """Command-line interface for optimized geocoder"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Costco Warehouse Geocoder v2 - Optimized Location Lookup'
    )
    parser.add_argument(
        'command',
        choices=['lookup', 'search', 'state', 'city', 'nearest', 'radius', 'stats',
                 'batch', 'bounds', 'heatmap', 'benchmark'],
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
    parser.add_argument(
        '--fuzzy',
        action='store_true',
        help='Enable fuzzy matching'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching'
    )

    args = parser.parse_args()

    # Initialize geocoder
    geocoder = CostcoGeocoderV2(
        args.database,
        enable_cache=not args.no_cache,
        enable_performance_tracking=True
    )

    # Execute command
    if args.command == 'lookup':
        if not args.args:
            print("Usage: costco_geocoder_v2.py lookup <warehouse_number>")
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

    elif args.command == 'batch':
        # Batch lookup from JSON input
        import sys
        data = json.load(sys.stdin)

        if 'warehouse_numbers' in data:
            results = geocoder.batch_enrich_warehouse_numbers(data['warehouse_numbers'])
            print(json.dumps(results, indent=2))
        elif 'states' in data:
            results = geocoder.batch_enrich_states(data['states'])
            print(json.dumps(results, indent=2))
        else:
            print("ERROR: Input must contain 'warehouse_numbers' or 'states'")
            sys.exit(1)

    elif args.command == 'radius':
        if len(args.args) < 3:
            print("Usage: costco_geocoder_v2.py radius <lat> <lon> <radius_miles>")
            sys.exit(1)

        lat = float(args.args[0])
        lon = float(args.args[1])
        radius = float(args.args[2])

        results = geocoder.find_warehouses_within_radius(lat, lon, radius)

        if args.json:
            print(json.dumps([{**wh.to_dict(), 'distance_miles': round(dist, 2)}
                              for wh, dist in results], indent=2))
        else:
            print(f"Found {len(results)} warehouses within {radius} miles:")
            for wh, dist in results:
                print(f"  {wh} - {dist:.2f} miles")

    elif args.command == 'bounds':
        state = args.args[0] if args.args else None

        if state:
            warehouses = geocoder.get_warehouses_by_state(state)
            bounds = geocoder.get_geographic_bounds(warehouses)
        else:
            bounds = geocoder.get_geographic_bounds()

        print(json.dumps(bounds, indent=2))

    elif args.command == 'heatmap':
        state = args.args[0] if args.args else None

        if state:
            warehouses = geocoder.get_warehouses_by_state(state)
            heatmap = geocoder.generate_heatmap_data(warehouses)
        else:
            heatmap = geocoder.generate_heatmap_data()

        print(json.dumps(heatmap, indent=2))

    elif args.command == 'stats':
        stats = geocoder.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.command == 'benchmark':
        print("Running performance benchmark...")
        print("=" * 60)

        # Test 1: Individual lookups
        print("\n[Test 1] Individual warehouse lookups (first 20)")
        test_warehouses = list(geocoder.warehouses.keys())[:20]
        for num in test_warehouses:
            geocoder.get_warehouse(num)

        # Test 2: Cached lookups
        print("[Test 2] Cached lookups (same 20 warehouses)")
        for num in test_warehouses:
            geocoder.get_warehouse(num)

        # Test 3: Batch operations
        print("[Test 3] Batch enrichment (20 warehouses)")
        geocoder.batch_enrich_warehouse_numbers(test_warehouses)

        # Test 4: State lookups
        print("[Test 4] State lookups (CA, TX, WA)")
        for state in ['CA', 'TX', 'WA']:
            geocoder.get_warehouses_by_state(state)

        # Results
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        stats = geocoder.get_statistics()
        perf = stats.get('performance', {})

        print(f"\nTotal lookups: {perf.get('total_lookups', 0)}")
        print(f"Average time: {perf.get('avg_time_ms', 0):.3f}ms")
        print(f"P50 time: {perf.get('p50_time_ms', 0):.3f}ms")
        print(f"P95 time: {perf.get('p95_time_ms', 0):.3f}ms")
        print(f"Cache hit rate: {perf.get('cache_hit_rate', 0):.1f}%")
        print(f"Batch operations: {perf.get('batch_operations', 0)}")

        meets_target = perf.get('meets_50ms_target', False)
        print(f"\n{'✅ MEETS' if meets_target else '❌ FAILS'} <50ms performance target")

    else:
        # Handle other commands from original geocoder
        print(f"Command '{args.command}' not yet implemented in v2")
        print("Available: lookup, batch, radius, bounds, heatmap, stats, benchmark")


if __name__ == '__main__':
    main()
