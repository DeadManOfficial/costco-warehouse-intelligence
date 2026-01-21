#!/usr/bin/env node
/**
 * Costco Deals Scraper for GitHub Actions
 * Uses Apify's free tier to scrape Costco directly
 */

const fs = require('fs');
const path = require('path');

const OUTPUT_FILE = path.join(__dirname, '../src/data/deals.json');

// Apify config - uses environment variable for API token
const APIFY_TOKEN = process.env.APIFY_TOKEN || '';
const APIFY_ACTOR_ID = 'Eqbeoob5hzg5Cg83D'; // costco-fast-product-scraper

// Search keywords to get variety of deals
const SEARCH_KEYWORDS = ['clearance', 'deals', 'savings', 'sale'];

// Category mapping
const categoryMap = {
  'appliances': 'Home',
  'refrigerator': 'Kitchen',
  'tv': 'Electronics',
  'computer': 'Electronics',
  'laptop': 'Electronics',
  'tablet': 'Electronics',
  'phone': 'Electronics',
  'audio': 'Electronics',
  'furniture': 'Home',
  'mattress': 'Home',
  'outdoor': 'Outdoor',
  'patio': 'Outdoor',
  'grill': 'Outdoor',
  'tire': 'Auto',
  'toy': 'Toys',
  'clothing': 'Clothing',
  'jewelry': 'Jewelry',
  'vitamin': 'Health',
  'cleaning': 'Cleaning',
  'office': 'Office',
  'pet': 'Pet',
  'kitchen': 'Kitchen',
  'cookware': 'Kitchen',
};

function getCategory(name, categoryPaths = []) {
  const text = (name + ' ' + categoryPaths.join(' ')).toLowerCase();
  for (const [keyword, category] of Object.entries(categoryMap)) {
    if (text.includes(keyword)) {
      return category;
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

async function runApifyScrape(keyword, maxItems = 25) {
  if (!APIFY_TOKEN) {
    console.log('  No APIFY_TOKEN set, skipping Apify scrape');
    return [];
  }

  console.log(`  Searching Apify for "${keyword}"...`);

  try {
    // Start the actor run
    const runResponse = await fetch(
      `https://api.apify.com/v2/acts/${APIFY_ACTOR_ID}/runs?token=${APIFY_TOKEN}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, maxItems }),
      }
    );

    if (!runResponse.ok) {
      console.log(`    API error: ${runResponse.status}`);
      return [];
    }

    const runData = await runResponse.json();
    const runId = runData.data?.id;
    const datasetId = runData.data?.defaultDatasetId;

    if (!runId) {
      console.log('    No run ID returned');
      return [];
    }

    console.log(`    Run started: ${runId}`);

    // Wait for completion (max 60 seconds)
    let status = 'RUNNING';
    let attempts = 0;
    while (status === 'RUNNING' || status === 'READY') {
      await new Promise(r => setTimeout(r, 3000));
      attempts++;

      const statusResponse = await fetch(
        `https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}`
      );
      const statusData = await statusResponse.json();
      status = statusData.data?.status;

      if (attempts > 20) {
        console.log('    Timeout waiting for completion');
        break;
      }
    }

    if (status !== 'SUCCEEDED') {
      console.log(`    Run finished with status: ${status}`);
      return [];
    }

    // Fetch results
    const dataResponse = await fetch(
      `https://api.apify.com/v2/datasets/${datasetId}/items?token=${APIFY_TOKEN}`
    );
    const items = await dataResponse.json();

    console.log(`    Found ${items.length} products`);
    return items;

  } catch (error) {
    console.log(`    Error: ${error.message}`);
    return [];
  }
}

function transformApifyProduct(product) {
  const salePrice = product.minPrice || product.listPrice || 0;
  const originalPrice = product.maxPrice || salePrice * 1.15;

  return {
    id: product.itemNumber || product.id?.split('!')[0] || String(Math.random()).slice(2, 10),
    name: product.name || product.itemName || 'Unknown Product',
    brand: (product.brands && product.brands[0]) || '',
    originalPrice: Math.round(originalPrice * 100) / 100,
    salePrice: Math.round(salePrice * 100) / 100,
    priceCode: getPriceCode(salePrice),
    category: getCategory(product.name || '', product.categoryPaths || []),
    storesCount: product.reviewsCount || 1,
    states: [],
    markdownType: ['online_deal'],
    url: product.productUrl || `https://www.costco.com/search?keyword=${encodeURIComponent(product.name || '')}`,
    image: product.image || product.images?.[0] || null,
    rating: product.rating || null,
  };
}

async function main() {
  console.log('Costco Deals Scraper (Apify)');
  console.log('============================');
  console.log(`Started: ${new Date().toISOString()}`);
  console.log(`APIFY_TOKEN: ${APIFY_TOKEN ? 'Set ✓' : 'Not set ✗'}\n`);

  const allProducts = new Map();

  // Run Apify scrapes for each keyword
  for (const keyword of SEARCH_KEYWORDS) {
    const products = await runApifyScrape(keyword, 20);

    for (const p of products) {
      const transformed = transformApifyProduct(p);
      if (transformed.salePrice > 0 && !allProducts.has(transformed.id)) {
        allProducts.set(transformed.id, transformed);
      }
    }

    // Rate limit between searches
    await new Promise(r => setTimeout(r, 2000));
  }

  console.log(`\nTotal unique products: ${allProducts.size}`);

  const deals = Array.from(allProducts.values());

  // Sort by discount
  deals.sort((a, b) => {
    const discountA = (a.originalPrice - a.salePrice) / a.originalPrice;
    const discountB = (b.originalPrice - b.salePrice) / b.originalPrice;
    return discountB - discountA;
  });

  // If we got very few results, keep existing data
  if (deals.length < 10) {
    console.log('\nWarning: Very few products found.');

    if (fs.existsSync(OUTPUT_FILE)) {
      const existing = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf-8'));
      existing.lastAttempt = new Date().toISOString();
      existing.lastAttemptCount = deals.length;

      // Merge new deals with existing
      if (deals.length > 0) {
        const existingIds = new Set(existing.deals.map(d => d.id));
        for (const deal of deals) {
          if (!existingIds.has(deal.id)) {
            existing.deals.push(deal);
          }
        }
        existing.count = existing.deals.length;
        console.log(`Merged ${deals.length} new products with existing data.`);
      }

      fs.writeFileSync(OUTPUT_FILE, JSON.stringify(existing, null, 2));
      console.log('Updated existing data file.');
      return;
    }
  }

  // Save results
  const output = {
    timestamp: new Date().toISOString(),
    source: 'Apify Costco Scraper (GitHub Actions)',
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
