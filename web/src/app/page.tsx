"use client";

import { useState, useMemo } from "react";
import warehouseData from "../costco_warehouses_master.json";

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
  quality_score?: number;
}

interface WarehouseData {
  metadata: {
    total_warehouses: number;
    states_covered: number;
  };
  warehouses: Record<string, Warehouse>;
}

const PRICE_CODES = [
  { code: ".97", meaning: "Manager's Special", description: "Store manager markdown - often last chance to buy", color: "bg-red-500" },
  { code: ".00 / .90", meaning: "Manufacturer Deal", description: "Vendor-sponsored discount or clearance", color: "bg-orange-500" },
  { code: ".88 / .77", meaning: "Clearance", description: "Item being discontinued - final markdown", color: "bg-yellow-500" },
  { code: "*", meaning: "Not Reordering", description: "Asterisk on price tag = item won't be restocked", color: "bg-purple-500" },
];

const data = warehouseData as WarehouseData;
const warehouses: Warehouse[] = Object.values(data.warehouses);

export default function Home() {
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [showPriceCodes, setShowPriceCodes] = useState(false);

  const states = useMemo(() => {
    const unique = [...new Set(warehouses.map((w) => w.state))].sort();
    return unique;
  }, []);

  const filtered = useMemo(() => {
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

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white">Costco Warehouse Intelligence</h1>
              <p className="text-gray-400 text-sm">{data.metadata.total_warehouses} US locations across {data.metadata.states_covered} states</p>
            </div>
            <button
              onClick={() => setShowPriceCodes(true)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
            >
              Price Codes Guide
            </button>
          </div>
        </div>
      </header>

      {/* Search & Filters */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <input
            type="text"
            placeholder="Search city, ZIP, or warehouse #..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-red-500 text-white placeholder-gray-400"
          />
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-red-500 text-white"
          >
            <option value="">All States ({warehouses.length})</option>
            {states.map((state) => (
              <option key={state} value={state}>
                {state} ({warehouses.filter((w) => w.state === state).length})
              </option>
            ))}
          </select>
        </div>

        {/* Results count */}
        <p className="text-gray-400 mb-4">
          Showing {filtered.length} warehouse{filtered.length !== 1 ? "s" : ""}
        </p>

        {/* Warehouse Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((warehouse) => (
            <div
              key={warehouse.number}
              className="bg-gray-800/50 border border-gray-700 rounded-xl p-5 hover:border-red-500/50 transition-colors"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-semibold text-lg text-white">{warehouse.name}</h3>
                  <p className="text-gray-400 text-sm">#{warehouse.number}</p>
                </div>
                <div className="flex items-center gap-2">
                  {warehouse.confidence === "very_high" && (
                    <span className="px-2 py-0.5 bg-green-600/30 text-green-400 rounded text-xs">
                      Verified
                    </span>
                  )}
                  <span className="px-2 py-1 bg-gray-700 rounded text-xs font-mono">
                    {warehouse.state}
                  </span>
                </div>
              </div>

              <p className="text-gray-300 text-sm mb-2">{warehouse.address}</p>
              <p className="text-gray-300 text-sm mb-4">
                {warehouse.city}, {warehouse.state} {warehouse.zip}
              </p>

              {warehouse.lat && warehouse.lon ? (
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${warehouse.lat},${warehouse.lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-red-400 hover:text-red-300"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Get Directions
                </a>
              ) : (
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`Costco ${warehouse.address} ${warehouse.city} ${warehouse.state} ${warehouse.zip}`)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-gray-300"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Search on Map
                </a>
              )}
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">No warehouses found matching your search.</p>
          </div>
        )}
      </div>

      {/* Price Codes Modal */}
      {showPriceCodes && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-lg w-full p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Costco Price Codes</h2>
              <button
                onClick={() => setShowPriceCodes(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              {PRICE_CODES.map((code) => (
                <div key={code.code} className="flex items-start gap-4">
                  <div className={`${code.color} px-3 py-1 rounded font-mono font-bold text-white min-w-[80px] text-center`}>
                    {code.code}
                  </div>
                  <div>
                    <p className="font-medium text-white">{code.meaning}</p>
                    <p className="text-gray-400 text-sm">{code.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-300">
                <strong className="text-red-400">Pro Tip:</strong> Check the bottom-right of price tags for these codes.
                Items ending in .97 are often the best deals - they're marked down by the store manager.
              </p>
            </div>

            <button
              onClick={() => setShowPriceCodes(false)}
              className="mt-6 w-full py-3 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
            >
              Got it!
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-gray-500 text-sm">
            Data updated regularly. Not affiliated with Costco Wholesale Corporation.
          </p>
          <p className="text-gray-600 text-xs mt-2">
            Built by <a href="https://github.com/DeadManOfficial" className="text-red-400 hover:text-red-300">DeadMan</a> | BUILD &gt; BUY
          </p>
        </div>
      </footer>
    </div>
  );
}
