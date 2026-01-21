import { NextResponse } from "next/server";
import dealsData from "@/data/deals.json";

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
  image?: string | null;
  rating?: number | null;
}

interface DealsData {
  timestamp: string;
  source: string;
  count: number;
  deals: Deal[];
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(parseInt(searchParams.get("limit") || "50"), 100);
  const category = searchParams.get("category");
  const state = searchParams.get("state");

  try {
    const data = dealsData as DealsData;
    let deals = [...data.deals];

    // Apply filters
    if (category && category !== "All") {
      deals = deals.filter((d) => d.category === category);
    }

    // Only filter by state if the deal has state data - empty states means available everywhere
    if (state) {
      deals = deals.filter((d) => d.states.length === 0 || d.states.includes(state));
    }

    // Sort by discount percentage
    deals.sort((a, b) => {
      const discountA = ((a.originalPrice - a.salePrice) / a.originalPrice) * 100;
      const discountB = ((b.originalPrice - b.salePrice) / b.originalPrice) * 100;
      return discountB - discountA;
    });

    // Apply limit
    deals = deals.slice(0, limit);

    return NextResponse.json({
      timestamp: data.timestamp,
      source: data.source,
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
