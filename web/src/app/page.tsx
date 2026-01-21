"use client";

import { useState, useMemo, useEffect } from "react";
import warehouseData from "../costco_warehouses_master.json";
// Static fallback deals
import staticDealsData from "../data/deals.json";

interface Warehouse {
  number: number;
  name: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  lat?: number;
  lon?: number;
  confidence?: string;
}

interface WarehouseData {
  metadata: { total_warehouses: number; states_covered: number };
  warehouses: Record<string, Warehouse>;
}

interface Deal {
  id: string;
  name: string;
  brand: string;
  originalPrice: number;
  salePrice: number;
  priceCode: ".97" | ".00" | ".88" | "*" | "regular";
  category: string;
  storesCount: number;
  states: string[];
  url?: string;
}

const PRICE_CODES = [
  { code: ".97", meaning: "Corporate Clearance", description: "Store manager markdown - HIGH VALUE, often last chance", color: "bg-red-600", textColor: "text-red-400" },
  { code: ".00", meaning: "Manager Special", description: "Negotiable - store-level discretion pricing", color: "bg-orange-600", textColor: "text-orange-400" },
  { code: ".88", meaning: "Manager Markdown", description: "Reduced to move - check for deeper discounts", color: "bg-yellow-600", textColor: "text-yellow-400" },
  { code: "*", meaning: "Death Star", description: "NO RESTOCK - item being discontinued", color: "bg-purple-600", textColor: "text-purple-400" },
];

const CATEGORIES = ["All", "Electronics", "Home", "Kitchen", "Outdoor", "Auto", "Toys", "Clothing", "Health", "Cleaning", "Office", "Pet"];

// Transform static deals to match interface
const STATIC_DEALS: Deal[] = (staticDealsData.deals || []).map((d: Record<string, unknown>) => ({
  id: String(d.id || ""),
  name: String(d.name || ""),
  brand: String(d.brand || ""),
  originalPrice: Number(d.originalPrice) || 0,
  salePrice: Number(d.salePrice) || 0,
  priceCode: (d.priceCode as Deal["priceCode"]) || "regular",
  category: String(d.category || "Other"),
  storesCount: Number(d.storesCount) || 0,
  states: Array.isArray(d.states) ? d.states.map(String) : [],
  url: String(d.url || ""),
}));

const data = warehouseData as WarehouseData;
const warehouses: Warehouse[] = Object.values(data.warehouses);

export default function Home() {
  const [activeTab, setActiveTab] = useState<"finder" | "hunter">("finder");
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [showPriceCodes, setShowPriceCodes] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [scanning, setScanning] = useState(false);
  const [deals, setDeals] = useState<Deal[]>(STATIC_DEALS);
  const [showApiModal, setShowApiModal] = useState(false);
  const [dataSource, setDataSource] = useState<"static" | "live">("static");
  const [lastUpdated, setLastUpdated] = useState<string>(staticDealsData.timestamp || "");

  // Load deals on mount
  useEffect(() => {
    loadDeals();
  }, []);

  const loadDeals = async () => {
    setScanning(true);
    try {
      const res = await fetch(`/api/deals?limit=50&category=${categoryFilter}&state=${stateFilter}`);
      if (res.ok) {
        const data = await res.json();
        if (data.deals && data.deals.length > 0) {
          setDeals(data.deals);
          setDataSource("live");
          setLastUpdated(data.timestamp);
        }
      }
    } catch {
      // Fall back to static data
      setDeals(STATIC_DEALS);
      setDataSource("static");
    } finally {
      setScanning(false);
    }
  };

  const states = useMemo(() => {
    const unique = [...new Set(warehouses.map((w) => w.state))].sort();
    return unique;
  }, []);

  const filteredWarehouses = useMemo(() => {
    return warehouses.filter((w) => {
      const matchesState = !stateFilter || w.state === stateFilter;
      const searchLower = search.toLowerCase();
      const matchesSearch =
        !search ||
        w.city.toLowerCase().includes(searchLower) ||
        w.zip.includes(search) ||
        w.number.toString().includes(search) ||
        w.name.toLowerCase().includes(searchLower) ||
        w.address.toLowerCase().includes(searchLower);
      return matchesState && matchesSearch;
    });
  }, [search, stateFilter]);

  const filteredDeals = useMemo(() => {
    return deals.filter((d) => {
      const matchesCategory = categoryFilter === "All" || d.category === categoryFilter;
      const matchesState = !stateFilter || d.states.includes(stateFilter);
      return matchesCategory && matchesState;
    }).sort((a, b) => {
      // Sort by discount percentage
      const discountA = ((a.originalPrice - a.salePrice) / a.originalPrice) * 100;
      const discountB = ((b.originalPrice - b.salePrice) / b.originalPrice) * 100;
      return discountB - discountA;
    });
  }, [deals, categoryFilter, stateFilter]);

  const runScan = async () => {
    setScanning(true);
    try {
      const res = await fetch(`/api/deals?limit=50&category=${categoryFilter}&state=${stateFilter}`);
      if (res.ok) {
        const data = await res.json();
        if (data.deals && data.deals.length > 0) {
          setDeals(data.deals);
          setDataSource("live");
          setLastUpdated(data.timestamp);
        }
      }
    } catch {
      setDeals(STATIC_DEALS);
      setDataSource("static");
    } finally {
      setScanning(false);
    }
  };

  const getPriceCodeStyle = (code: Deal["priceCode"]) => {
    const priceCode = PRICE_CODES.find(p => p.code === code);
    return priceCode ? priceCode.textColor : "text-gray-400";
  };

  return (
    <div className="min-h-screen bg-black text-white font-mono">
      {/* Header */}
      <header className="border-b border-gray-800 bg-black/90 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">
                <span className="text-green-500">DEADMAN</span>
                <span className="text-gray-500"> // </span>
                <span className="text-white">Costco Intelligence</span>
              </h1>
              <p className="text-gray-500 text-sm">{data.metadata.total_warehouses} warehouses | {data.metadata.states_covered} states | Real-time markdown hunting</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowPriceCodes(true)}
                className="px-4 py-2 bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded font-medium transition-colors text-sm"
              >
                PRICE CODES
              </button>
              <button
                onClick={() => setShowApiModal(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded font-medium transition-colors text-sm"
              >
                SETTINGS
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex gap-2 border-b border-gray-800 pb-4">
          <button
            onClick={() => setActiveTab("finder")}
            className={`px-6 py-3 rounded-t font-medium transition-colors ${
              activeTab === "finder"
                ? "bg-gray-900 text-green-500 border border-gray-700 border-b-black"
                : "text-gray-500 hover:text-white"
            }`}
          >
            WAREHOUSE FINDER
          </button>
          <button
            onClick={() => setActiveTab("hunter")}
            className={`px-6 py-3 rounded-t font-medium transition-colors ${
              activeTab === "hunter"
                ? "bg-gray-900 text-green-500 border border-gray-700 border-b-black"
                : "text-gray-500 hover:text-white"
            }`}
          >
            MARKDOWN HUNTER
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        {activeTab === "finder" ? (
          /* Warehouse Finder */
          <div>
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
              <input
                type="text"
                placeholder="Search city, ZIP, warehouse #..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="flex-1 px-4 py-3 bg-gray-900 border border-gray-700 rounded focus:outline-none focus:border-green-500 text-white placeholder-gray-500 font-mono"
              />
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="px-4 py-3 bg-gray-900 border border-gray-700 rounded focus:outline-none focus:border-green-500 text-white font-mono"
              >
                <option value="">All States ({warehouses.length})</option>
                {states.map((state) => (
                  <option key={state} value={state}>
                    {state} ({warehouses.filter((w) => w.state === state).length})
                  </option>
                ))}
              </select>
            </div>

            <p className="text-gray-500 mb-4 text-sm">
              [ {filteredWarehouses.length} TARGETS FOUND ]
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredWarehouses.slice(0, 50).map((warehouse) => (
                <div
                  key={warehouse.number}
                  className="bg-gray-900/50 border border-gray-800 rounded-lg p-5 hover:border-green-500/50 transition-colors"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg text-white">{warehouse.name}</h3>
                      <p className="text-green-500 text-sm font-mono">#{warehouse.number}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {warehouse.confidence === "very_high" && (
                        <span className="px-2 py-0.5 bg-green-900/50 text-green-400 rounded text-xs border border-green-800">
                          VERIFIED
                        </span>
                      )}
                      <span className="px-2 py-1 bg-gray-800 rounded text-xs font-mono text-gray-400">
                        {warehouse.state}
                      </span>
                    </div>
                  </div>

                  <p className="text-gray-400 text-sm mb-1">{warehouse.address}</p>
                  <p className="text-gray-400 text-sm mb-4">
                    {warehouse.city}, {warehouse.state} {warehouse.zip}
                  </p>

                  {warehouse.lat && warehouse.lon ? (
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${warehouse.lat},${warehouse.lon}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-green-500 hover:text-green-400"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      GET DIRECTIONS
                    </a>
                  ) : (
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`Costco ${warehouse.address} ${warehouse.city} ${warehouse.state}`)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-400"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      SEARCH MAP
                    </a>
                  )}
                </div>
              ))}
            </div>

            {filteredWarehouses.length > 50 && (
              <p className="text-center text-gray-500 mt-6">
                Showing 50 of {filteredWarehouses.length} warehouses. Refine your search.
              </p>
            )}
          </div>
        ) : (
          /* Markdown Hunter */
          <div>
            {/* Controls */}
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-sm">TARGET:</span>
                  <select
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value)}
                    className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm font-mono"
                  >
                    <option value="">All States</option>
                    {states.map((state) => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-gray-500 text-sm">CATEGORY:</span>
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white text-sm font-mono"
                  >
                    {CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={runScan}
                  disabled={scanning}
                  className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 rounded font-bold text-black disabled:text-gray-400 transition-colors"
                >
                  {scanning ? "SCANNING..." : "LOAD DEALS"}
                </button>

                <span className={`text-sm font-mono ${scanning ? "text-yellow-500" : "text-green-500"}`}>
                  [ {scanning ? "SCANNING" : "READY"} ]
                </span>
              </div>
            </div>

            {/* Results Header */}
            <div className="bg-gray-900 border border-gray-800 rounded-t-lg">
              <div className="px-4 py-3 border-b border-gray-800">
                <span className="text-green-500 font-bold">// OUTPUT</span>
                <span className="text-gray-500 ml-4">{filteredDeals.length} deals found</span>
              </div>
            </div>

            {/* Deals Grid */}
            <div className="bg-gray-900/50 border border-t-0 border-gray-800 rounded-b-lg p-4">
              {filteredDeals.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p>No deals found matching your filters.</p>
                  <p className="text-sm mt-2">Try selecting different category or state.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredDeals.map((deal, index) => {
                    const discount = Math.round(((deal.originalPrice - deal.salePrice) / deal.originalPrice) * 100);
                    return (
                      <div
                        key={deal.id}
                        className="bg-black/50 border border-gray-800 rounded-lg p-4 hover:border-green-500/30 transition-colors"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-gray-500 text-sm">{String(index + 1).padStart(2, '0')}.</span>
                              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                                deal.priceCode === ".97" ? "bg-red-900/50 text-red-400 border border-red-800" :
                                deal.priceCode === ".00" ? "bg-orange-900/50 text-orange-400 border border-orange-800" :
                                deal.priceCode === ".88" ? "bg-yellow-900/50 text-yellow-400 border border-yellow-800" :
                                deal.priceCode === "*" ? "bg-purple-900/50 text-purple-400 border border-purple-800" :
                                "bg-gray-800 text-gray-400"
                              }`}>
                                {deal.priceCode}
                              </span>
                              <span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400">
                                {deal.category.toUpperCase()}
                              </span>
                            </div>
                            <h3 className="text-white font-medium">{deal.name}</h3>
                            <p className="text-gray-500 text-sm">{deal.brand}</p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-3">
                              <span className="text-gray-500 line-through text-sm">${deal.originalPrice.toFixed(2)}</span>
                              <span className={`text-xl font-bold ${getPriceCodeStyle(deal.priceCode)}`}>
                                ${deal.salePrice.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex items-center justify-end gap-2 mt-1">
                              <span className="text-green-500 text-sm font-bold">{discount}% OFF</span>
                              <span className="text-gray-600 text-xs">|</span>
                              <span className="text-gray-500 text-xs">{deal.storesCount} stores</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Price Code Legend */}
            <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="text-green-500 font-bold mb-3">// PRICE CODE INTEL</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {PRICE_CODES.map((code) => (
                  <div key={code.code} className="text-center">
                    <span className={`inline-block px-3 py-1 ${code.color} rounded font-bold text-white text-sm mb-1`}>
                      {code.code}
                    </span>
                    <p className="text-xs text-gray-400">{code.meaning}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Price Codes Modal */}
      {showPriceCodes && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-lg w-full p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-green-500">// PRICE CODE INTEL</h2>
              <button onClick={() => setShowPriceCodes(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              {PRICE_CODES.map((code) => (
                <div key={code.code} className="flex items-start gap-4">
                  <div className={`${code.color} px-4 py-2 rounded font-mono font-bold text-white min-w-[80px] text-center`}>
                    {code.code}
                  </div>
                  <div>
                    <p className="font-medium text-white">{code.meaning}</p>
                    <p className="text-gray-400 text-sm">{code.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-black rounded-lg border border-gray-800">
              <p className="text-sm text-gray-300">
                <strong className="text-green-500">PRO TIP:</strong> Check the bottom-right corner of price tags.
                Items ending in <span className="text-red-400 font-bold">.97</span> are the best deals - corporate clearance.
              </p>
            </div>

            <button
              onClick={() => setShowPriceCodes(false)}
              className="mt-6 w-full py-3 bg-green-600 hover:bg-green-700 rounded font-bold text-black transition-colors"
            >
              GOT IT
            </button>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showApiModal && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-green-500">// SETTINGS</h2>
              <button onClick={() => setShowApiModal(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Groq API Key (Optional)</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-4 py-3 bg-black border border-gray-700 rounded focus:outline-none focus:border-green-500 text-white font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Get a FREE API key at{" "}
                  <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" className="text-green-500 hover:underline">
                    console.groq.com
                  </a>
                </p>
              </div>

              <div className="p-4 bg-black rounded-lg border border-gray-800">
                <p className="text-sm text-gray-400">
                  <strong className="text-yellow-500">NOTE:</strong> The web app uses demo data. For live deal scanning,
                  use the desktop app with your Groq API key for AI-powered analysis.
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowApiModal(false)}
                className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 rounded font-bold transition-colors"
              >
                CANCEL
              </button>
              <button
                onClick={() => {
                  localStorage.setItem("groq_api_key", apiKey);
                  setShowApiModal(false);
                }}
                className="flex-1 py-3 bg-green-600 hover:bg-green-700 rounded font-bold text-black transition-colors"
              >
                SAVE
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-gray-600 text-sm">
            Data for demonstration. Not affiliated with Costco Wholesale Corporation.
          </p>
          <p className="text-gray-700 text-xs mt-2">
            Built by{" "}
            <a href="https://github.com/DeadManOfficial" className="text-green-500 hover:text-green-400">
              DeadMan
            </a>{" "}
            | BUILD &gt; BUY
          </p>
        </div>
      </footer>
    </div>
  );
}
