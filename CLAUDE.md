# Costco Warehouse Intelligence

**Identity:** DeadMan's FREE Costco markdown intelligence system.

---

## QUICK START

```bash
# Install dependencies
pip install -r requirements.txt

# Run production scraper
python src/warehouse_runner_PRODUCTION_v2.py

# Use geocoder
python -c "from src.costco_geocoder_v2 import CostcoGeocoder; g=CostcoGeocoder(); print(g.lookup(428))"
```

---

## PROJECT FILES

```
PROJECT.md  → Vision, goals, architecture
ROADMAP.md  → 5-phase execution plan
STATE.md    → Decisions log, current status
PLAN.md     → Active tasks (XML structure)
```

---

## KEY SCRIPTS

| Script | Purpose | Performance |
|--------|---------|-------------|
| `warehouse_runner_PRODUCTION_v2.py` | Markdown scraper | 4.1 items/sec |
| `costco_geocoder_v2.py` | Warehouse lookup | <0.01ms |
| `warehouse_number_enumerator.py` | Discover warehouses | 100-9999 range |

---

## DATABASE

- **643 warehouses** across 48 states
- **100% coverage** of US Costco locations
- File: `data/costco_warehouses_master.json` (302KB)

---

## ALWAYS

- NEVER pay for Costco data (we BUILD, not BUY)
- ALWAYS respect rate limits (2s delay minimum)
- ALWAYS validate data from multiple sources

---

Created-By: DEADMAN
