"""
Warehouse Number Enumerator - Discover all valid Costco warehouse numbers.

Tests warehouse numbers 1-1999 against Warehouse Runner to identify all valid locations.
Uses rate limiting and saves progress incrementally.
"""

import sys
import io
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class WarehouseEnumerator:
    """Enumerate warehouse numbers to find all valid Costco locations."""

    def __init__(self, output_file: str, checkpoint_file: str):
        self.output_file = Path(output_file)
        self.checkpoint_file = Path(checkpoint_file)
        self.valid_warehouses = {}
        self.load_checkpoint()

    def load_checkpoint(self):
        """Load existing progress if available."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                self.valid_warehouses = data.get('valid_warehouses', {})
                print(f"Loaded checkpoint: {len(self.valid_warehouses)} warehouses found so far")

    def save_checkpoint(self):
        """Save current progress."""
        checkpoint_data = {
            'valid_warehouses': self.valid_warehouses,
            'total_found': len(self.valid_warehouses),
            'last_updated': datetime.now().isoformat()
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

    def test_warehouse(self, number: int) -> Tuple[bool, Dict]:
        """
        Test if a warehouse number is valid.

        Returns:
            (is_valid, warehouse_data)
        """
        url = f"https://app.warehouserunner.com/store/xxx-{number}"

        try:
            response = requests.get(url, timeout=10, allow_redirects=False)

            # Valid warehouses return 200 with substantial content
            # Invalid numbers return a small error page (~9KB)
            is_valid = response.status_code == 200 and len(response.content) > 20000

            if is_valid:
                # Extract basic info from the page
                content = response.text
                warehouse_data = {
                    'number': number,
                    'url': url,
                    'content_length': len(response.content),
                    'discovered_at': datetime.now().isoformat()
                }

                # Try to extract warehouse name from title
                if '<title>' in content:
                    start = content.find('<title>') + 7
                    end = content.find('</title>', start)
                    if end > start:
                        title = content[start:end]
                        warehouse_data['title'] = title

                return (True, warehouse_data)
            else:
                return (False, {})

        except Exception as e:
            print(f"  Error testing #{number}: {e}")
            return (False, {})

    def enumerate_range(self, start: int, end: int, delay: float = 1.5):
        """
        Enumerate a range of warehouse numbers.

        Args:
            start: Starting warehouse number
            end: Ending warehouse number (exclusive)
            delay: Delay between requests in seconds
        """
        print(f"\nEnumerating warehouses {start} to {end-1}...")
        print("=" * 80)

        tested = 0
        found = 0
        start_time = time.time()

        for number in range(start, end):
            # Skip if already tested
            if str(number) in self.valid_warehouses:
                continue

            tested += 1
            is_valid, warehouse_data = self.test_warehouse(number)

            if is_valid:
                self.valid_warehouses[str(number)] = warehouse_data
                found += 1
                print(f"  #{number:4d}: [VALID] {warehouse_data.get('title', 'Unknown')[:60]}")

                # Save checkpoint every 10 valid warehouses
                if found % 10 == 0:
                    self.save_checkpoint()
                    print(f"  ... Checkpoint saved ({len(self.valid_warehouses)} total)")

            else:
                # Only show invalid for debugging (too verbose otherwise)
                if tested % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = tested / elapsed if elapsed > 0 else 0
                    eta_seconds = (end - number) / rate if rate > 0 else 0
                    eta_minutes = eta_seconds / 60
                    print(f"  ... Progress: {tested} tested, {found} found, {rate:.1f}/sec, ETA: {eta_minutes:.1f} min")

            time.sleep(delay)

        # Final save
        self.save_checkpoint()

        elapsed = time.time() - start_time
        print(f"\nCompleted range {start}-{end-1}")
        print(f"  Tested: {tested}")
        print(f"  Found: {found}")
        print(f"  Time: {elapsed/60:.1f} minutes")
        print(f"  Total valid warehouses: {len(self.valid_warehouses)}")

    def save_results(self):
        """Save final results."""
        # Sort by warehouse number
        sorted_warehouses = dict(sorted(
            self.valid_warehouses.items(),
            key=lambda x: int(x[0])
        ))

        results = {
            'total_valid_warehouses': len(sorted_warehouses),
            'warehouses': sorted_warehouses,
            'completed_at': datetime.now().isoformat()
        }

        with open(self.output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {self.output_file}")
        print(f"Total valid warehouses: {len(sorted_warehouses)}")

        # Also save just the numbers
        numbers_file = self.output_file.parent / "valid_warehouse_numbers_list.txt"
        with open(numbers_file, 'w') as f:
            for num in sorted(int(k) for k in sorted_warehouses.keys()):
                f.write(f"{num}\n")

        print(f"Warehouse numbers list: {numbers_file}")

def main():
    """Run warehouse enumeration."""
    output_dir = Path("D:/DeadMan_AI_Research/Data")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "valid_warehouse_numbers.json"
    checkpoint_file = output_dir / "warehouse_enumeration_checkpoint.json"

    enumerator = WarehouseEnumerator(str(output_file), str(checkpoint_file))

    print("=" * 80)
    print("WAREHOUSE NUMBER ENUMERATION")
    print("=" * 80)
    print(f"Output: {output_file}")
    print(f"Checkpoint: {checkpoint_file}")
    print(f"Rate limit: 1.5 seconds per request")
    print()

    # Enumerate in chunks for better progress tracking
    # Based on our data, warehouses go from 1 to ~1763
    ranges = [
        (1, 200),
        (200, 400),
        (400, 600),
        (600, 800),
        (800, 1000),
        (1000, 1200),
        (1200, 1400),
        (1400, 1600),
        (1600, 1800),
        (1800, 2000),  # Safety margin
    ]

    try:
        for start, end in ranges:
            enumerator.enumerate_range(start, end)

        # Save final results
        enumerator.save_results()

        print("\n" + "=" * 80)
        print("ENUMERATION COMPLETE")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Saving progress...")
        enumerator.save_checkpoint()
        print(f"Progress saved. Found {len(enumerator.valid_warehouses)} warehouses so far.")
        print(f"Run script again to resume from checkpoint.")

if __name__ == "__main__":
    main()
