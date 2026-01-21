#!/usr/bin/env node
/**
 * Quick Deal Scraper for Costco Warehouse Intelligence
 * Fetches real markdown data from Warehouse Runner
 */

const fs = require('fs');
const path = require('path');

const ITEMS_FILE = path.join(__dirname, '../../app/warehouse_runner_all_items.txt');
const OUTPUT_FILE = path.join(__dirname, '../src/data/deals.json');

// Sample of item IDs to check (popular categories)
const SAMPLE_SIZE = 500;

async function fetchDeal(itemId) {
  const url = `https://app.warehouserunner.com/costco/${itemId}`;

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      }
    });

    if (!response.ok) return null;

    const html = await response.text();

    // Extract Schema.org data
    const schemaMatch = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
    if (!schemaMatch) return null;

    let productData;
    try {
      const schemas = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g) || [];
      for (const schema of schemas) {
        const jsonStr = schema.replace(/<script type="application\/ld\+json">/, '').replace(/<\/script>/, '');
        const data = JSON.parse(jsonStr);
        if (data['@type'] === 'Product') {
          productData = data;
          break;
        }
      }
    } catch (e) {
      return null;
    }

    if (!productData) return null;

    const name = productData.name || '';
    const brand = typeof productData.brand === 'object' ? productData.brand.name : productData.brand || '';
    const offers = productData.offers || {};
    const lowPrice = parseFloat(offers.lowPrice) || 0;
    const highPrice = parseFloat(offers.highPrice) || 0;

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
    const statePattern = /\\"state\\":\\"([A-Z]{2})\\"[^}]*?\\"avgPrice\\":\s*([0-9.]+)[^}]*?\\"storeCount\\":\s*(\d+)/g;
    let stateMatch;
    while ((stateMatch = statePattern.exec(html)) !== null && states.length < 10) {
      states.push({
        state: stateMatch[1],
        avgPrice: parseFloat(stateMatch[2]),
        storeCount: parseInt(stateMatch[3])
      });
    }

    // Determine price code
    let priceCode = 'regular';
    const priceStr = lowPrice.toFixed(2);
    if (priceStr.endsWith('.97')) priceCode = '.97';
    else if (priceStr.endsWith('.00') || priceStr.endsWith('.90')) priceCode = '.00';
    else if (priceStr.endsWith('.88') || priceStr.endsWith('.77')) priceCode = '.88';

    // Categorize
    const nameLower = name.toLowerCase();
    let category = 'Other';
    const categories = {
      'Electronics': ['tv', 'tablet', 'laptop', 'headphone', 'speaker', 'camera', 'phone', 'computer', 'monitor', 'airpod', 'ipad', 'macbook'],
      'Home': ['furniture', 'mattress', 'bed', 'table', 'chair', 'sofa', 'desk', 'rug', 'pillow', 'blanket', 'vacuum', 'dyson'],
      'Kitchen': ['cookware', 'pan', 'pot', 'knife', 'blender', 'mixer', 'instant pot', 'air fryer', 'cuisinart', 'kitchenaid'],
      'Outdoor': ['grill', 'patio', 'lawn', 'garden', 'hose', 'mower', 'umbrella', 'gazebo', 'traeger', 'weber'],
      'Auto': ['tire', 'oil', 'car', 'motor', 'synthetic', 'wiper', 'battery', 'michelin', 'goodyear'],
      'Toys': ['toy', 'game', 'puzzle', 'doll', 'lego', 'playstation', 'xbox', 'nintendo', 'nerf'],
      'Clothing': ['shirt', 'pants', 'jacket', 'shoes', 'socks', 'dress', 'coat', 'sweater'],
      'Health': ['vitamin', 'supplement', 'medicine', 'protein', 'probiotic', 'kirkland signature vitamin'],
      'Cleaning': ['detergent', 'soap', 'cleaner', 'wipes', 'sanitizer', 'tide'],
      'Office': ['paper', 'pen', 'printer', 'ink', 'stapler', 'binder'],
      'Pet': ['dog', 'cat', 'pet', 'litter']
    };

    for (const [cat, keywords] of Object.entries(categories)) {
      if (keywords.some(kw => nameLower.includes(kw))) {
        category = cat;
        break;
      }
    }

    return {
      id: itemId,
      name,
      brand,
      originalPrice: highPrice || lowPrice * 1.2,
      salePrice: lowPrice,
      priceCode,
      category,
      storesCount: discountCount || states.reduce((sum, s) => sum + s.storeCount, 0),
      states: states.map(s => s.state),
      markdownType: [
        ...(hasSaleInfo ? ['instant_savings'] : []),
        ...(discountCount > 0 ? ['regional_discount'] : []),
        ...(managerCount > 0 ? ['manager_special'] : [])
      ],
      url
    };
  } catch (error) {
    return null;
  }
}

async function main() {
  console.log('Costco Deal Scraper');
  console.log('='.repeat(50));

  // Load item IDs
  const allItems = fs.readFileSync(ITEMS_FILE, 'utf-8')
    .split('\n')
    .map(l => l.trim())
    .filter(Boolean);

  console.log(`Total items: ${allItems.length}`);

  // Sample random items
  const shuffled = allItems.sort(() => Math.random() - 0.5);
  const sample = shuffled.slice(0, SAMPLE_SIZE);

  console.log(`Sampling: ${SAMPLE_SIZE} items`);
  console.log('');

  const deals = [];
  let processed = 0;

  // Process in batches
  const BATCH_SIZE = 10;
  for (let i = 0; i < sample.length; i += BATCH_SIZE) {
    const batch = sample.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(batch.map(fetchDeal));

    for (const result of results) {
      if (result) {
        deals.push(result);
        console.log(`  Found: ${result.name.slice(0, 40)} - $${result.salePrice} (${result.priceCode})`);
      }
    }

    processed += batch.length;
    process.stdout.write(`\rProgress: ${processed}/${SAMPLE_SIZE} | Deals: ${deals.length}`);

    // Rate limit
    await new Promise(r => setTimeout(r, 500));
  }

  console.log('\n');
  console.log(`Found ${deals.length} deals`);

  // Ensure output directory exists
  const outputDir = path.dirname(OUTPUT_FILE);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // Save
  const output = {
    timestamp: new Date().toISOString(),
    source: 'Warehouse Runner',
    count: deals.length,
    deals: deals.sort((a, b) => {
      const discountA = (a.originalPrice - a.salePrice) / a.originalPrice;
      const discountB = (b.originalPrice - b.salePrice) / b.originalPrice;
      return discountB - discountA;
    })
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`Saved to: ${OUTPUT_FILE}`);
}

main().catch(console.error);
