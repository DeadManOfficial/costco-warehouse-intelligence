#!/usr/bin/env node
/**
 * Transform Apify Costco data to our app format
 */

const fs = require('fs');
const path = require('path');

const OUTPUT_FILE = path.join(__dirname, '../src/data/deals.json');

// Category mapping from Costco paths to our categories
const categoryMap = {
  'appliances': 'Home',
  'refrigerators': 'Kitchen',
  'tvs': 'Electronics',
  'computers': 'Electronics',
  'tablets': 'Electronics',
  'phones': 'Electronics',
  'audio': 'Electronics',
  'cameras': 'Electronics',
  'furniture': 'Home',
  'mattresses': 'Home',
  'bedding': 'Home',
  'outdoor': 'Outdoor',
  'patio': 'Outdoor',
  'grills': 'Outdoor',
  'lawn': 'Outdoor',
  'tires': 'Auto',
  'automotive': 'Auto',
  'toys': 'Toys',
  'games': 'Toys',
  'clothing': 'Clothing',
  'shoes': 'Clothing',
  'jewelry': 'Jewelry',
  'health': 'Health',
  'vitamins': 'Health',
  'cleaning': 'Cleaning',
  'laundry': 'Cleaning',
  'office': 'Office',
  'pet': 'Pet',
  'kitchen': 'Kitchen',
  'cookware': 'Kitchen',
  'small-appliances': 'Kitchen',
};

function getCategoryFromPaths(categoryPaths) {
  if (!categoryPaths || !categoryPaths.length) return 'Other';

  const pathStr = categoryPaths.join(' ').toLowerCase();
  for (const [keyword, category] of Object.entries(categoryMap)) {
    if (pathStr.includes(keyword)) {
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

function transformApifyProduct(product) {
  const salePrice = product.minPrice || product.listPrice || 0;
  const originalPrice = product.maxPrice || product.listPrice * 1.15 || salePrice * 1.15;

  // Only include if there's a meaningful discount
  const discount = (originalPrice - salePrice) / originalPrice;
  if (discount < 0.05) {
    // Still include but mark as regular price
  }

  return {
    id: product.itemNumber || product.id?.split('!')[0] || String(Math.random()).slice(2, 10),
    name: product.name || product.itemName || 'Unknown Product',
    brand: (product.brands && product.brands[0]) || '',
    originalPrice: Math.round(originalPrice * 100) / 100,
    salePrice: Math.round(salePrice * 100) / 100,
    priceCode: getPriceCode(salePrice),
    category: getCategoryFromPaths(product.categoryPaths),
    storesCount: product.reviewsCount || 1,
    states: [], // Apify doesn't have state-level data
    markdownType: discount > 0.1 ? ['instant_savings'] : ['online_deal'],
    url: product.productUrl || `https://www.costco.com/search?keyword=${encodeURIComponent(product.name)}`,
    image: product.image || product.images?.[0] || null,
    rating: product.rating || null,
  };
}

async function main() {
  console.log('Transforming Apify data...\n');

  const allProducts = [];
  const seenIds = new Set();

  // Read from local files
  const dataFiles = [
    path.join(__dirname, 'apify_deals1.json'),
    path.join(__dirname, 'apify_deals2.json'),
  ];

  for (const file of dataFiles) {
    try {
      if (fs.existsSync(file)) {
        const data = JSON.parse(fs.readFileSync(file, 'utf-8'));
        const products = Array.isArray(data) ? data : (data.deals || []);
        console.log(`  ${file}: ${products.length} products`);

        for (const p of products) {
          const transformed = transformApifyProduct(p);
          if (!seenIds.has(transformed.id)) {
            seenIds.add(transformed.id);
            allProducts.push(transformed);
          }
        }
      }
    } catch (err) {
      console.error(`  Error reading ${file}: ${err.message}`);
    }
  }

  console.log(`\nTotal unique products: ${allProducts.length}`);

  // Sort by discount percentage
  allProducts.sort((a, b) => {
    const discountA = (a.originalPrice - a.salePrice) / a.originalPrice;
    const discountB = (b.originalPrice - b.salePrice) / b.originalPrice;
    return discountB - discountA;
  });

  // Save
  const output = {
    timestamp: new Date().toISOString(),
    source: 'Apify Costco Scraper',
    count: allProducts.length,
    deals: allProducts,
  };

  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));
  console.log(`\nSaved to: ${OUTPUT_FILE}`);

  // Show top 5 deals
  console.log('\nTop 5 deals:');
  for (const deal of allProducts.slice(0, 5)) {
    const discount = Math.round((deal.originalPrice - deal.salePrice) / deal.originalPrice * 100);
    console.log(`  ${deal.name.slice(0, 50)}: $${deal.salePrice} (${discount}% off)`);
  }
}

main().catch(console.error);
