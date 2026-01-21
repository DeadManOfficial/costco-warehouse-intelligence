<div align="center">

<br>

# Costco Warehouse Intelligence

**FREE Database + Markdown Hunter App**

643 US warehouses with GPS, hours, services & a desktop app to find hidden deals.

<br>

<a href="https://costco-warehouse-intelligence.vercel.app">
  <img src="https://img.shields.io/badge/Live_App-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live App" />
</a>
<a href="https://github.com/DeadManOfficial/costco-warehouse-intelligence">
  <img src="https://img.shields.io/badge/GitHub-Source-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" />
</a>
<a href="https://github.com/DeadManOfficial/costco-warehouse-intelligence">
  <img src="https://img.shields.io/badge/Warehouses-643-DC143C?style=for-the-badge" alt="Warehouses" />
</a>

<br><br>

</div>

---

## Three Tools, One Repo

| Tool | Description |
|------|-------------|
| **[Live Web App](https://costco-warehouse-intelligence.vercel.app)** | Search all 643 warehouses online |
| **Database + Geocoder** | Python API for GPS coords, instant lookups |
| **Markdown Hunter App** | Desktop app to find hidden deals |

---

## 1. Database & Geocoder

```bash
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

### Performance

| Operation | Speed |
|-----------|-------|
| Single lookup | <0.01ms |
| State search | <1ms |
| Nearest (k=5) | <5ms |

---

## 2. Markdown Hunter App

```bash
cd app
pip install -r requirements.txt
python app.py
```

### Price Codes

| Ending | Meaning |
|--------|---------|
| **.97** | Corporate clearance - HIGH VALUE |
| **.00** | Manager special - NEGOTIABLE |
| **.88** | Manager markdown |
| **\*** | Death star - NO RESTOCK |

### Setup

1. Get free Groq API key from [console.groq.com](https://console.groq.com)
2. Click **SETTINGS** in app
3. Enter API key, select state & warehouse
4. Click **LOAD DEALS**

---

## Why Free?

Commercial Costco APIs cost $80+/month. This is free forever.

- $960/year saved
- 100% data ownership
- Works offline
- No rate limits

---

## Project Structure

```
costco-warehouse-intelligence/
├── web/                    # Next.js web app (Vercel)
├── src/                    # Geocoder library
├── data/                   # Warehouse database
├── app/                    # Markdown Hunter desktop app
│   ├── app.py              # Main GUI
│   ├── costco_geocoder_v2.py
│   └── warehouse_runner_*.py
└── docs/                   # Documentation
```

---

## Related

- **[mcp-auditor](https://github.com/DeadManOfficial/mcp-auditor)** — Security auditor for Claude
- **[token-optimization](https://github.com/DeadManOfficial/token-optimization)** — Save 30-50% on API costs
- **[AI-Updates](https://github.com/DeadManOfficial/AI-Updates)** — Daily AI intelligence

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
