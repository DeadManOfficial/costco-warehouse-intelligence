#!/usr/bin/env node
/**
 * Costco Deals Scraper for GitHub Actions
 * Uses Warehouse Runner as primary source (works from GitHub Actions IPs)
 * Falls back to static popular item IDs
 */

const fs = require('fs');
const path = require('path');

const OUTPUT_FILE = path.join(__dirname, '../src/data/deals.json');

// Popular item IDs known to have deals
const POPULAR_ITEM_IDS = [
  // Verified deal items
  "28028", "1320970", "112266", "88566", "1554558", "2598", "112218",
  "121211", "1719029", "35960", "50051", "1641430", "105946", "41012",
  "1717954", "1738655", "1713380", "1803765", "1786498", "1712756",
  // Electronics
  "1600170", "1600180", "1700100", "1700200", "1700300",
  // Home
  "1500100", "1500200", "1500300", "1400100", "1400200",
  // Kitchen
  "1300100", "1300200", "1200100", "1200200",
  // Outdoor
  "1100100", "1100200", "1000100", "1000200",
  // Range of item IDs to sample
  "100", "500", "1000", "2000", "3000", "5000", "7500", "10000",
  "15000", "20000", "25000", "30000", "40000", "50000", "75000",
  "100000", "150000", "200000", "300000", "400000", "500000",
  "600000", "700000", "800000", "900000", "1000000", "1100000",
  "1200000", "1300000", "1400000", "1500000", "1600000", "1700000",
];

const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.5',
};

// Category mapping
const categories = {
  Electronics: ["tv", "tablet", "laptop", "headphone", "speaker", "camera", "phone", "computer", "monitor", "airpod", "ipad", "macbook", "sony", "samsung", "lg"],
  Home: ["furniture", "mattress", "bed", "table", "chair", "sofa", "desk", "rug", "pillow", "blanket", "vacuum", "dyson"],
  Kitchen: ["cookware", "pan", "pot", "knife", "blender", "mixer", "instant pot", "air fryer", "cuisinart", "kitchenaid", "refrigerator"],
  Outdoor: ["grill", "patio", "lawn", "garden", "hose", "mower", "umbrella", "gazebo", "traeger", "weber", "wreath", "plant", "planter"],
  Auto: ["tire", "oil", "car", "motor", "synthetic", "wiper", "battery", "michelin", "goodyear"],
  Toys: ["toy", "game", "puzzle", "doll", "lego", "playstation", "xbox", "nintendo", "nerf"],
  Clothing: ["shirt", "pants", "jacket", "shoes", "socks", "dress", "coat", "sweater", "pant", "brief", "clog"],
  Health: ["vitamin", "supplement", "medicine", "protein", "probiotic"],
  Cleaning: ["detergent", "soap", "cleaner", "wipes", "sanitizer", "tide"],
  Office: ["paper", "pen", "printer", "ink", "stapler", "binder"],
  Pet: ["dog", "cat", "pet", "litter"],
  Jewelry: ["gold", "diamond", "ring", "necklace", "bracelet", "14kt", "18kt"],
};

function getCategory(name) {
  const nameLower = name.toLowerCase();
  for (const [cat, keywords] of Object.entries(categories)) {
    if (keywords.some(kw => nameLower.includes(kw))) {
      return cat;
    }
  }
  return 'Other';
}

function getPriceCode(price) {
  const priceStr = price.toFixed(2);
  if (priceStr.endsWith('.97')) return '.97';
  if (priceStr.endsWith('.00') || priceStr.endsWith('.90')) return '.00';
  if (priceStr.endsWith('.88') || priceStr.endsWith('.77')) return '.88';
  return 'regular';
}

async function fetchDealFromWarehouseRunner(itemId) {
  const url = `https://app.warehouserunner.com/costco/${itemId}`;

  try {
    const response = await fetch(url, { headers: HEADERS });
    if (!response.ok) return null;

    const html = await response.text();

    // Extract Schema.org Product data
    const schemaMatches = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g) || [];
    let productData = null;

    for (const schema of schemaMatches) {
      try {
        const jsonStr = schema.replace(/<script type="application\/ld\+json">/, '').replace(/<\/script>/, '');
        const data = JSON.parse(jsonStr);
        if (data['@type'] === 'Product') {
          productData = data;
          break;
        }
      } catch {
        continue;
      }
    }

    if (!productData?.name) return null;

    const name = productData.name;
    const brand = typeof productData.brand === 'object' ? productData.brand?.name || '' : String(productData.brand || '');
    const offers = productData.offers || {};
    const lowPrice = Number(offers.lowPrice) || 0;
    const highPrice = Number(offers.highPrice) || lowPrice * 1.2;

    // Check for markdown indicators
    const discountMatch = html.match(/\\"discount_count\\":\s*(\d+)/);
    const discountCount = discountMatch ? parseInt(discountMatch[1]) : 0;

    const managerMatch = html.match(/\\"manager_special_count\\":\s*(\d+)/);
    const managerCount = managerMatch ? parseInt(managerMatch[1]) : 0;

    const saleInfoMatch = html.match(/\\"saleInfo\\":(null|\{[^}]+\})/);
    const hasSaleInfo = saleInfoMatch && saleInfoMatch[1] !== 'null';

    const isMarkdown = discountCount > 0 || managerCount > 0 || hasSaleInfo;

    if (!isMarkdown) return null;

    // Extract state data
    const states = [];
    const statePattern = /\\"state\\":\\"([A-Z]{2})\\"/g;
    let stateMatch;
    const seenStates = new Set();
    while ((stateMatch = statePattern.exec(html)) !== null && states.length < 10) {
      if (!seenStates.has(stateMatch[1])) {
        states.push(stateMatch[1]);
        seenStates.add(stateMatch[1]);
      }
    }

    // Extract image if available
    const imageMatch = html.match(/\\"thumbnail\\":\\"([^"]+)\\"/);
    const image = imageMatch ? imageMatch[1].replace(/\\\//g, '/') : null;

    return {
      id: itemId,
      name,
      brand,
      originalPrice: Math.round(highPrice * 100) / 100,
      salePrice: Math.round(lowPrice * 100) / 100,
      priceCode: getPriceCode(lowPrice),
      category: getCategory(name),
      storesCount: discountCount || managerCount || states.length * 10,
      states,
      markdownType: [
        ...(hasSaleInfo ? ['instant_savings'] : []),
        ...(discountCount > 0 ? ['regional_discount'] : []),
        ...(managerCount > 0 ? ['manager_special'] : []),
      ],
      url,
      image,
      rating: null,
    };
  } catch {
    return null;
  }
}

async function main() {
  console.log('Costco Deals Scraper (Warehouse Runner)');
  console.log('=======================================');
  console.log(`Started: ${new Date().toISOString()}\n`);

  const deals = [];
  let processed = 0;
  let found = 0;

  // Shuffle items for variety
  const shuffled = [...POPULAR_ITEM_IDS].sort(() => Math.random() - 0.5);

  // Process in batches
  const BATCH_SIZE = 5;
  for (let i = 0; i < shuffled.length; i += BATCH_SIZE) {
    const batch = shuffled.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(batch.map(fetchDealFromWarehouseRunner));

    for (const result of results) {
      if (result) {
        deals.push(result);
        found++;
        console.log(`  ✓ ${result.name.slice(0, 45)} - $${result.salePrice} (${result.priceCode})`);
      }
    }

    processed += batch.length;
    process.stdout.write(`\rProgress: ${processed}/${shuffled.length} | Found: ${found}`);

    // Rate limiting
    await new Promise(r => setTimeout(r, 1000));
  }

  console.log('\n');
  console.log(`Processed: ${processed} items`);
  console.log(`Found: ${deals.length} deals`);

  // Sort by discount percentage
  deals.sort((a, b) => {
    const discountA = (a.originalPrice - a.salePrice) / a.originalPrice;
    const discountB = (b.originalPrice - b.salePrice) / b.originalPrice;
    return discountB - discountA;
  });

  // If we got very few results, keep existing data
  if (deals.length < 5) {
    console.log('\nWarning: Very few deals found. Source may be blocking.');

    if (fs.existsSync(OUTPUT_FILE)) {
      const existing = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf-8'));
      existing.lastAttempt = new Date().toISOString();
      existing.lastAttemptCount = deals.length;
      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(existing, null, 2));
      console.log('Kept existing data, updated attempt timestamp.');
      return;
    }
  }

  // Save results
  const output = {
    timestamp: new Date().toISOString(),
    source: 'Warehouse Runner (GitHub Actions)',
    count: deals.length,
    deals,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`\nSaved ${deals.length} deals to: ${OUTPUT_FILE}`);

  // Show top deals
  console.log('\nTop 5 deals:');
  for (const deal of deals.slice(0, 5)) {
    const discount = Math.round((deal.originalPrice - deal.salePrice) / deal.originalPrice * 100);
    console.log(`  ${deal.name.slice(0, 45)}: $${deal.salePrice} (${discount}% off)`);
  }
}

main().catch(err => {
  console.error('Scraper failed:', err);
  process.exit(1);
});
