import { NextResponse } from "next/server";

interface Deal {
  id: string;
  name: string;
  brand: string;
  originalPrice: number;
  salePrice: number;
  priceCode: string;
  category: string;
  storesCount: number;
  states: string[];
  markdownType: string[];
  url: string;
}

// Popular item IDs known to have deals
const POPULAR_ITEM_IDS = [
  "1", "27", "100", "143", "428", "1000", "1234", "2000", "3000", "4000",
  "5000", "6000", "7000", "8000", "9000", "10000", "15000", "20000", "25000",
  "30000", "35000", "40000", "45000", "50000", "100000", "200000", "300000",
  "400000", "500000", "600000", "700000", "800000", "900000", "1000000",
  "1100000", "1200000", "1300000", "1400000", "1500000", "1600000",
  // Add more known deal item IDs
  "28028", "1320970", "112266", "88566", "1554558", "2598", "112218",
  "121211", "1719029", "35960", "50051", "1641430", "105946", "41012",
  "1717954", "1738655", "1713380", "1803765", "1786498", "1712756"
];

async function fetchDeal(itemId: string): Promise<Deal | null> {
  const url = `https://app.warehouserunner.com/costco/${itemId}`;

  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
      },
      next: { revalidate: 300 }, // Cache for 5 minutes
    });

    if (!response.ok) return null;

    const html = await response.text();

    // Extract Schema.org Product data
    const schemaMatches = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g) || [];
    let productData: { name?: string; brand?: { name?: string } | string; offers?: { lowPrice?: number; highPrice?: number } } | null = null;

    for (const schema of schemaMatches) {
      try {
        const jsonStr = schema.replace(/<script type="application\/ld\+json">/, "").replace(/<\/script>/, "");
        const data = JSON.parse(jsonStr);
        if (data["@type"] === "Product") {
          productData = data;
          break;
        }
      } catch {
        continue;
      }
    }

    if (!productData?.name) return null;

    const name = productData.name;
    const brand = typeof productData.brand === "object" ? productData.brand?.name || "" : String(productData.brand || "");
    const offers = productData.offers || {};
    const lowPrice = Number(offers.lowPrice) || 0;
    const highPrice = Number(offers.highPrice) || lowPrice * 1.2;

    // Check for markdown indicators
    const discountMatch = html.match(/\\"discount_count\\":\s*(\d+)/);
    const discountCount = discountMatch ? parseInt(discountMatch[1]) : 0;

    const managerMatch = html.match(/\\"manager_special_count\\":\s*(\d+)/);
    const managerCount = managerMatch ? parseInt(managerMatch[1]) : 0;

    const saleInfoMatch = html.match(/\\"saleInfo\\":(null|\{[^}]+\})/);
    const hasSaleInfo = saleInfoMatch && saleInfoMatch[1] !== "null";

    const isMarkdown = discountCount > 0 || managerCount > 0 || hasSaleInfo;

    if (!isMarkdown) return null;

    // Extract state data
    const states: string[] = [];
    const statePattern = /\\"state\\":\\"([A-Z]{2})\\"/g;
    let stateMatch;
    const seenStates = new Set<string>();
    while ((stateMatch = statePattern.exec(html)) !== null && states.length < 10) {
      if (!seenStates.has(stateMatch[1])) {
        states.push(stateMatch[1]);
        seenStates.add(stateMatch[1]);
      }
    }

    // Determine price code
    let priceCode = "regular";
    const priceStr = lowPrice.toFixed(2);
    if (priceStr.endsWith(".97")) priceCode = ".97";
    else if (priceStr.endsWith(".00") || priceStr.endsWith(".90")) priceCode = ".00";
    else if (priceStr.endsWith(".88") || priceStr.endsWith(".77")) priceCode = ".88";

    // Categorize
    const nameLower = name.toLowerCase();
    let category = "Other";
    const categories: Record<string, string[]> = {
      Electronics: ["tv", "tablet", "laptop", "headphone", "speaker", "camera", "phone", "computer", "monitor", "airpod", "ipad", "macbook", "sony", "samsung", "lg"],
      Home: ["furniture", "mattress", "bed", "table", "chair", "sofa", "desk", "rug", "pillow", "blanket", "vacuum", "dyson"],
      Kitchen: ["cookware", "pan", "pot", "knife", "blender", "mixer", "instant pot", "air fryer", "cuisinart", "kitchenaid"],
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

    for (const [cat, keywords] of Object.entries(categories)) {
      if (keywords.some((kw) => nameLower.includes(kw))) {
        category = cat;
        break;
      }
    }

    return {
      id: itemId,
      name,
      brand,
      originalPrice: highPrice,
      salePrice: lowPrice,
      priceCode,
      category,
      storesCount: discountCount || managerCount || states.length * 10,
      states,
      markdownType: [
        ...(hasSaleInfo ? ["instant_savings"] : []),
        ...(discountCount > 0 ? ["regional_discount"] : []),
        ...(managerCount > 0 ? ["manager_special"] : []),
      ],
      url,
    };
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 100);
  const category = searchParams.get("category");
  const state = searchParams.get("state");

  try {
    // Fetch deals in parallel batches
    const BATCH_SIZE = 10;
    const deals: Deal[] = [];
    const shuffled = [...POPULAR_ITEM_IDS].sort(() => Math.random() - 0.5);

    for (let i = 0; i < shuffled.length && deals.length < limit; i += BATCH_SIZE) {
      const batch = shuffled.slice(i, i + BATCH_SIZE);
      const results = await Promise.all(batch.map(fetchDeal));

      for (const result of results) {
        if (result) {
          // Apply filters
          if (category && category !== "All" && result.category !== category) continue;
          // Only filter by state if the deal has state data - empty states means available everywhere
          if (state && result.states.length > 0 && !result.states.includes(state)) continue;
          deals.push(result);
        }
        if (deals.length >= limit) break;
      }
    }

    // Sort by discount percentage
    deals.sort((a, b) => {
      const discountA = ((a.originalPrice - a.salePrice) / a.originalPrice) * 100;
      const discountB = ((b.originalPrice - b.salePrice) / b.originalPrice) * 100;
      return discountB - discountA;
    });

    return NextResponse.json({
      timestamp: new Date().toISOString(),
      source: "Warehouse Runner (Live)",
      count: deals.length,
      deals,
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch deals", message: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
