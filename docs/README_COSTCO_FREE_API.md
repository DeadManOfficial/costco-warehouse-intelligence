# COSTCO FREE API - Forever Free Alternative to Unwrangle

## What This Is

A **completely FREE** implementation of Costco product scraping API.
Replicates Unwrangle.com's $99/month Costco API - **FOR FREE**.

## Features

✅ Product detail extraction
✅ Markdown detection (.97 pricing)
✅ Clearance search
✅ Image URLs, specs, pricing
✅ Unlimited usage (no credits)
✅ No paid service
✅ No rate limits (be respectful)

## Installation

```bash
pip install cloudscraper beautifulsoup4 lxml
```

## Usage

### Get Single Product
```python
from costco_api_clone import CostcoAPIClone

api = CostcoAPIClone()
product = api.get_product_detail('https://www.costco.com/some-product.1234567.html')

print(f"Name: {product['product_name']}")
print(f"Price: ${product['price']}")
print(f"Is Markdown: {product['is_markdown']}")
```

### Search Clearance
```python
api = CostcoAPIClone()
markdowns = api.search_clearance(limit=50)

for item in markdowns:
    if item['is_markdown']:
        print(f"🎯 ${item['price']} - {item['product_name']}")
```

## Comparison to Unwrangle

| Feature | Unwrangle | Our Clone |
|---------|-----------|-----------|
| **Cost** | $99/month | **FREE** |
| **Credits** | 10 per request | **UNLIMITED** |
| **Rate Limit** | Yes | None (be respectful) |
| **Product Detail** | ✅ | ✅ |
| **Search** | ✅ | ✅ |
| **Markdown Detection** | ❌ | ✅ |
| **Setup** | API key signup | **ZERO** |

## How It Works

1. **cloudscraper** - Bypasses Cloudflare
2. **BeautifulSoup** - Parses HTML
3. **Caching** - Avoids duplicate requests
4. **Smart parsing** - Extracts all product data

## API Response Format

```json
{
  "product_name": "Product Name Here",
  "brand": "Brand Name",
  "price": 19.97,
  "listing_price": 29.99,
  "is_markdown": true,
  "description": "Product description...",
  "images": ["https://...", "https://..."],
  "sku": "1234567",
  "upc": "012345678901",
  "availability": "In Stock",
  "specs": {
    "Dimensions": "10 x 5 x 3",
    "Weight": "2 lbs"
  }
}
```

## Notes

- This is a scraper, not an official API
- Costco may block excessive requests
- Use responsibly
- Cache results to minimize requests
- Consider adding delays between requests

## Credits

Built by DeadMan AI Research
NO LIMITS. NO EXCUSES. FREE FOREVER.

