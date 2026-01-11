# Costco Warehouse Intelligence

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FREE Costco warehouse and markdown intelligence system.** No paid APIs, no subscriptions.

## Features

| Feature | Description |
|---------|-------------|
| 🏪 **643 Warehouses** | Complete US Costco database |
| 📍 **Geocoder** | <0.01ms warehouse lookups |
| 💰 **Markdown Scraper** | Instant savings, regional discounts |
| 🆓 **100% Free** | No paid data services |

## Quick Start

```bash
# Clone the repo
git clone https://github.com/DeadManOfficial/costco-warehouse-intelligence.git
cd costco-warehouse-intelligence

# Install dependencies
pip install -r requirements.txt

# Run the scraper
python src/warehouse_runner_PRODUCTION_v2.py
```

## Database

The master database contains **643 warehouses** across **48 states**:

```python
from src.costco_geocoder_v2 import CostcoGeocoder

geocoder = CostcoGeocoder()

# Lookup by warehouse number
warehouse = geocoder.lookup(428)
# Returns: {'name': 'Alhambra', 'city': 'Alhambra', 'state': 'CA', 'zip': '91801', ...}

# Find warehouses by state
ca_warehouses = geocoder.by_state('CA')
# Returns: List of all California warehouses
```

## Project Structure

```
costco-warehouse-intelligence/
├── CLAUDE.md           # AI assistant context
├── PROJECT.md          # Vision and architecture
├── ROADMAP.md          # Development phases
├── STATE.md            # Current decisions
├── PLAN.md             # Active tasks
├── src/                # Source code
│   ├── warehouse_runner_PRODUCTION_v2.py
│   ├── costco_geocoder_v2.py
│   └── warehouse_number_enumerator.py
├── data/               # Warehouse database
│   └── costco_warehouses_master.json
├── docs/               # Documentation
└── tests/              # Test files
```

## Philosophy

> "The creation and utilization of something free is way more practical" - DeadMan

This project was built instead of paying $80 for commercial Costco data. The result:
- **$80 saved**
- **100% data ownership**
- **Full customization**

## License

MIT License - Created-By: DEADMAN
