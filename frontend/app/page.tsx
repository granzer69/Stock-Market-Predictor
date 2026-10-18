"use client";

import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ArrowUpIcon, ArrowDownIcon } from "lucide-react";
import { formatINR } from "@/lib/format";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

type SymbolEntry = {
  symbol: string;
  yahoo_symbol: string;
  name: string;
  sector: string;
};

export default function StockDashboard() {
  const [symbols, setSymbols] = useState<SymbolEntry[]>([]);
  const [symbolsError, setSymbolsError] = useState<string | null>(null);
  const [selectedStock, setSelectedStock] = useState("RELIANCE");
  const [chartData, setChartData] = useState<{ date: string; price: number }[]>(
    []
  );
  const [loading, setLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

  const [stockData, setStockData] = useState({
    symbol: "RELIANCE",
    price: 0,
    change: 0,
    changePercent: 0,
    previousClose: 0,
    asOf: "",
  });

  const [aiPrediction, setAiPrediction] = useState({
    nextDayPrice: 0,
    confidence: 0,
  });

  useEffect(() => {
    fetch(`${API_BASE}/symbols`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load symbols (${res.status})`);
        }
        return res.json();
      })
      .then((data: { symbols?: SymbolEntry[] }) => {
        const list = data.symbols ?? [];
        setSymbols(list);
        setSymbolsError(null);
        if (list.length > 0) {
          const hasReliance = list.some((s) => s.symbol === "RELIANCE");
          if (!hasReliance && !list.some((s) => s.symbol === selectedStock)) {
            setSelectedStock(list[0].symbol);
          }
        }
      })
      .catch((err: Error) => {
        setSymbolsError(err.message || "Could not load symbol list.");
        setSymbols([]);
      });
  }, []);

  useEffect(() => {
    if (!selectedStock) return;

    setLoading(true);
    setDataError(null);

    const quotePromise = fetch(
      `${API_BASE}/realtime?symbol=${encodeURIComponent(selectedStock)}`
    )
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Quote unavailable (${res.status})`);
        }
        return res.json();
      })
      .then((data) => {
        if (data) {
          setStockData({
            symbol: data.symbol,
            price: data.price,
            change: data.change,
            changePercent: data.change_percent,
            previousClose: data.previous_close,
            asOf: data.as_of ?? "",
          });
        }
      });

    const predictPromise = fetch(
      `${API_BASE}/predict?symbol=${encodeURIComponent(selectedStock)}`
    )
      .then((res) => {
        if (!res.ok) {
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (data?.predicted_price != null) {
          setAiPrediction({
            nextDayPrice: data.predicted_price,
            confidence: data.confidence ?? 0,
          });
        }
      });

    const chartPromise = fetch(
      `${API_BASE}/chart?symbol=${encodeURIComponent(selectedStock)}`
    )
      .then((res) => {
        if (!res.ok) {
          return null;
        }
        return res.json();
      })
      .then((data) => {
        if (data?.chart_data) {
          setChartData(data.chart_data);
        } else {
          setChartData([]);
        }
      });

    Promise.all([quotePromise, predictPromise, chartPromise])
      .catch((err: Error) => {
        setDataError(err.message || "Failed to load market data.");
      })
      .finally(() => setLoading(false));
  }, [selectedStock]);

  const selectedMeta = symbols.find((s) => s.symbol === selectedStock);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="container mx-auto px-4 py-8 flex-1">
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-blue-400 to-purple-600 text-transparent bg-clip-text">
            Indian Stock Market Predictor
          </h1>
        </header>

        <div className="max-w-md mx-auto mb-8">
          {symbolsError && (
            <p className="text-red-400 text-sm mb-2 text-center" role="alert">
              {symbolsError}
            </p>
          )}
          <select
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            disabled={symbols.length === 0 && !!symbolsError}
            className="w-full p-3 rounded bg-gray-800 text-white border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {symbols.length > 0
              ? symbols.map((stock) => (
                  <option key={stock.symbol} value={stock.symbol}>
                    {stock.name} ({stock.symbol})
                  </option>
                ))
              : (
                <option value="RELIANCE">RELIANCE</option>
              )}
          </select>
        </div>

        {dataError && (
          <p
            className="text-amber-400 text-sm text-center mb-6 max-w-lg mx-auto"
            role="alert"
          >
            {dataError}
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
            <h2 className="text-xl font-semibold text-gray-400 mb-2">
              Latest close
            </h2>
            <h3 className="text-2xl font-bold">
              {selectedMeta?.name ?? selectedStock}
            </h3>
            <p className="text-sm text-gray-500">{selectedStock} · NSE</p>
            <div className="mt-2 text-5xl font-bold tracking-tighter">
              {loading && stockData.price === 0
                ? "…"
                : formatINR(stockData.price)}
            </div>
            <div className="flex mt-2 items-center">
              {stockData.change >= 0 ? (
                <span className="text-green-500 flex items-center">
                  <ArrowUpIcon className="w-5 h-5 mr-1" />
                  {formatINR(stockData.change)} ({stockData.changePercent}%)
                </span>
              ) : (
                <span className="text-red-500 flex items-center">
                  <ArrowDownIcon className="w-5 h-5 mr-1" />
                  {formatINR(Math.abs(stockData.change))} (
                  {Math.abs(stockData.changePercent)}%)
                </span>
              )}
            </div>
            {stockData.asOf && (
              <div className="text-sm text-gray-400 mt-2">
                As of session: {stockData.asOf}
              </div>
            )}
          </div>

          <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
            <h2 className="text-xl font-semibold text-gray-400 mb-2">
              AI Predicted Price
            </h2>
            <h3 className="text-2xl font-bold">Next Trading Day</h3>
            <div className="mt-2 text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
              {loading ? "…" : formatINR(aiPrediction.nextDayPrice)}
            </div>
            <div className="mt-4 flex items-center">
              <div className="w-full bg-gray-700 rounded-full h-2.5">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{ width: `${aiPrediction.confidence * 100}%` }}
                ></div>
              </div>
              <span className="ml-2 text-sm text-gray-400 whitespace-nowrap">
                {(aiPrediction.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-700">
          <h2 className="text-xl font-semibold mb-6">Last 60 sessions</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" />
                <YAxis
                  stroke="#9CA3AF"
                  tickFormatter={(v) => formatINR(v)}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1F2937",
                    borderColor: "#374151",
                    color: "#F9FAFB",
                  }}
                  formatter={(value: number) => [formatINR(value), "Close"]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="price"
                  name="Close (INR)"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <footer className="border-t border-gray-800 py-6 px-4 text-center text-sm text-gray-500">
        <p>
          This app is for educational purposes only and is not trading or
          investment advice. Model confidence is derived as 1 − test MAPE and
          does not guarantee future performance.
        </p>
      </footer>
    </div>
  );
}
