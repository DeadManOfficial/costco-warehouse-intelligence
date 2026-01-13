<div align="center">

# Costco Warehouse Intelligence

### FREE Database of Every US Costco Location

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Warehouses](https://img.shields.io/badge/Warehouses-643-red?style=for-the-badge)](https://github.com/DeadManOfficial/costco-warehouse-intelligence)
[![States](https://img.shields.io/badge/States-48-success?style=for-the-badge)](https://github.com/DeadManOfficial/costco-warehouse-intelligence)

**Complete Costco database with coordinates, hours, services, and gas prices. Totally free.**

*No paid APIs. No subscriptions. No rate limits.*

</div>

---

## Why Use This?

| Problem | Solution |
|---------|----------|
| Commercial Costco APIs cost $80+ per month | **100% FREE** - complete database included |
| Location services are rate-limited | **Instant lookups** in <0.01ms (offline) |
| No official Costco API exists | **643 warehouses** fully geocoded and validated |
| Building your own scraper takes weeks | **Production-ready** - just clone and use |

---

## Quick Start (60 Seconds)

```bash
git clone https://github.com/DeadManOfficial/costco-warehouse-intelligence.git
cd costco-warehouse-intelligence
pip install -r requirements.txt
```

### Find Nearest Warehouses

```python
from src.costco_geocoder_v2 import CostcoGeocoder

geocoder = CostcoGeocoder()

# Lookup by warehouse number
warehouse = geocoder.lookup(428)
# {'name': 'Alhambra', 'city': 'Alhambra', 'state': 'CA', 'zip': '91801',
#  'lat': 34.0736, 'lon': -118.1296, 'phone': '(626) 289-1414', ...}

# Get all California warehouses
ca_warehouses = geocoder.by_state('CA')
print(f"Found {len(ca_warehouses)} warehouses in California")

# Find nearest to coordinates
nearby = geocoder.find_nearest(lat=37.7749, lon=-122.4194, limit=5)
```

### Scrape Markdown Deals

```python
from src.warehouse_runner_PRODUCTION_v2 import MarkdownScraper

scraper = MarkdownScraper()
deals = scraper.get_current_deals(warehouse_number=428)

for deal in deals:
    print(f"{deal['item']}: {deal['discount']}% off")
```

---

## What's Included

### Complete Database

```
643 US Costco warehouses
├── Full addresses (street, city, state, zip)
├── GPS coordinates (lat/lon)
├── Phone numbers
├── Operating hours
├── Services available (gas, tire, optical, etc.)
└── Warehouse numbers for API lookups
```

### High-Performance Geocoder

| Operation | Speed |
|-----------|-------|
| Single warehouse lookup | <0.01ms |
| State-wide search | <1ms |
| Nearest neighbor (k=5) | <5ms |
| Full database scan | <50ms |

### Markdown Scraper

- Current instant savings
- Regional discounts
- Coupon book deals
- Member-only pricing
- Gas prices (where available)

---

## Project Structure

```
costco-warehouse-intelligence/
├── data/
│   └── costco_warehouses_master.json   # 643 warehouses (302KB)
├── src/
│   ├── costco_geocoder_v2.py           # Fast warehouse lookups
│   ├── warehouse_runner_PRODUCTION_v2.py  # Markdown scraper
│   └── warehouse_number_enumerator.py  # Discovery tool
├── docs/                               # Full documentation
└── tests/                              # Test suite
```

---

## Use Cases

| Application | How This Helps |
|-------------|----------------|
| **Store Locator Apps** | Complete coordinates for map integration |
| **Price Comparison** | Scrape markdown deals across regions |
| **Delivery Services** | Calculate distances to nearest warehouses |
| **Business Intelligence** | Analyze store distribution by state |
| **Personal Projects** | Find best deals near you |

---

## Why I Built This

> Commercial Costco data costs $80/month. I spent a weekend building this instead.

**Result:**
- $960/year saved
- 100% data ownership
- Full customization
- No rate limits
- Works offline

---

## Requirements

- Python 3.10+
- `requests` (for scraping)
- `beautifulsoup4` (for parsing)

---

## License

MIT License

---

<div align="center">

**Created by DEADMAN**

[![GitHub](https://img.shields.io/badge/DeadManOfficial-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/DeadManOfficial)

*BUILD > BUY. Why pay $80/month when you can own the data forever?*

</div>
