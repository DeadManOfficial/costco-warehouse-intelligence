<div align="center">

<br>

# Costco Warehouse Intelligence

**FREE Database — 643 US Costco Locations**

Complete coordinates, hours, services & gas prices. No paid APIs.

<br>

<a href="https://github.com/DeadManOfficial/costco-warehouse-intelligence">
  <img src="https://img.shields.io/badge/GitHub-Source-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
</a>
<a href="https://www.python.org">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</a>
<a href="https://github.com/DeadManOfficial/costco-warehouse-intelligence">
  <img src="https://img.shields.io/badge/Warehouses-643-DC143C?style=for-the-badge" alt="Warehouses" />
</a>

<br><br>

</div>

---

## Quick Start

```bash
git clone https://github.com/DeadManOfficial/costco-warehouse-intelligence.git
cd costco-warehouse-intelligence
pip install -r requirements.txt
```

```python
from src.costco_geocoder_v2 import CostcoGeocoder

geocoder = CostcoGeocoder()

# Lookup by warehouse number
warehouse = geocoder.lookup(428)

# Get all California warehouses
ca_warehouses = geocoder.by_state('CA')

# Find nearest to coordinates
nearby = geocoder.find_nearest(lat=37.7749, lon=-122.4194, limit=5)
```

---

## Features

| Feature | Description |
|---------|-------------|
| **643 Warehouses** | Full US coverage, GPS coordinates |
| **Instant Lookups** | <0.01ms offline queries |
| **State Search** | Filter by state, <1ms |
| **Nearest Neighbor** | Distance-based search |
| **Markdown Scraper** | Current deals & discounts |

---

## Performance

| Operation | Speed |
|-----------|-------|
| Single lookup | <0.01ms |
| State search | <1ms |
| Nearest (k=5) | <5ms |
| Full scan | <50ms |

---

## Why Free?

Commercial Costco APIs cost $80+/month. This is free forever.

- $960/year saved
- 100% data ownership
- Works offline
- No rate limits

---

## Related

- **[mcp-auditor](https://github.com/DeadManOfficial/mcp-auditor)** — Security & compliance auditor for Claude
- **[token-optimization](https://github.com/DeadManOfficial/token-optimization)** — Save 30-50% on API costs
- **[AI-Updates](https://github.com/DeadManOfficial/AI-Updates)** — Daily AI intelligence briefs

---

## License

MIT

---

<div align="center">

<br>

<a href="https://twitter.com/DeadManAI">
  <img src="https://img.shields.io/badge/X-000000?style=flat&logo=x&logoColor=white" alt="X" />
</a>
<a href="https://youtube.com/@DeadManAI">
  <img src="https://img.shields.io/badge/YouTube-FF0000?style=flat&logo=youtube&logoColor=white" alt="YouTube" />
</a>
<a href="https://tiktok.com/@DeadManAI">
  <img src="https://img.shields.io/badge/TikTok-000000?style=flat&logo=tiktok&logoColor=white" alt="TikTok" />
</a>

<br><br>

<sub>**BUILD > BUY**</sub>

</div>
