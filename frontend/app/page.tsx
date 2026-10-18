"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowUpIcon, ArrowDownIcon } from "lucide-react";
import { formatINR } from "@/lib/format";
import { DisclaimerBanner } from "@/components/trading/disclaimer-banner";
import { SiteNav } from "@/components/trading/site-nav";
import { CandlestickChart, type OhlcBar } from "@/components/trading/candlestick-chart";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const WATCHLIST_KEY = "nse_watchlist_v1";
const DEFAULT_WATCH = ["RELIANCE", "TCS", "INFY"];

type SymbolEntry = {
  symbol: string;
  yahoo_symbol: string;
  name: string;
  sector: string;
};

export default function TradingDeskPage() {
  const [symbols, setSymbols] = useState<SymbolEntry[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>(DEFAULT_WATCH);
  const [selectedStock, setSelectedStock] = useState("RELIANCE");
  const [bars, setBars] = useState<OhlcBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [dataError, setDataError] = useState<string | null>(null);

  const [quote, setQuote] = useState({
    price: 0,
    change: 0,
    changePercent: 0,
    asOf: "",
  });

  const [prediction, setPrediction] = useState({
    price: 0,
    p10: 0,
    p50: 0,
    p90: 0,
    confidence: 0,
    direction: "up",
  });

  useEffect(() => {
    const saved = localStorage.getItem(WATCHLIST_KEY);
    if (saved) {
      try {
        setWatchlist(JSON.parse(saved));
      } catch {
        /* ignore */
      }
    }
    fetch(`${API_BASE}/symbols`)
      .then((r) => r.json())
      .then((d) => d.symbols && setSymbols(d.symbols))
      .catch(() => setDataError("API unavailable"));
  }, []);

  const persistWatch = useCallback((list: string[]) => {
    setWatchlist(list);
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(list));
  }, []);

  const toggleWatch = (sym: string) => {
    if (watchlist.includes(sym)) {
      persistWatch(watchlist.filter((s) => s !== sym));
    } else {
      persistWatch([...watchlist, sym]);
    }
  };

  useEffect(() => {
    setLoading(true);
    setDataError(null);

    fetch(`${API_BASE}/realtime?symbol=${selectedStock}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.price != null) {
          setQuote({
            price: d.price,
            change: d.change,
            changePercent: d.change_percent,
            asOf: d.as_of || "",
          });
        }
      });

    fetch(`${API_BASE}/predict?symbol=${selectedStock}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.predicted_price) {
          setPrediction({
            price: d.predicted_price,
            p10: d.interval?.p10 ?? d.predicted_price,
            p50: d.interval?.p50 ?? d.predicted_price,
            p90: d.interval?.p90 ?? d.predicted_price,
            confidence: d.confidence ?? 0,
            direction: d.direction ?? "up",
          });
        }
      });

    fetch(`${API_BASE}/ohlcv?symbol=${selectedStock}&tail=120`)
      .then((r) => r.json())
      .then((d) => {
        if (d.bars) setBars(d.bars);
      })
      .catch(() =>
        fetch(`${API_BASE}/chart?symbol=${selectedStock}`)
          .then((r) => r.json())
          .then((d) => {
            if (d.chart_data) {
              setBars(
                d.chart_data.map((c: { date: string; price: number }) => ({
                  date: c.date,
                  open: c.price,
                  high: c.price,
                  low: c.price,
                  close: c.price,
                }))
              );
            }
          })
      )
      .finally(() => setLoading(false));
  }, [selectedStock]);

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-6 text-center">
          <h1 className="text-4xl font-extrabold bg-gradient-to-r from-blue-400 to-purple-600 text-transparent bg-clip-text">
            NSE Trading Desk
          </h1>
          <p className="text-gray-400 mt-2">Paper research · predictions · backtest</p>
        </header>
        <SiteNav />
        <DisclaimerBanner />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-8">
          <aside className="lg:col-span-1 bg-gray-800 rounded-xl p-4 border border-gray-700">
            <h2 className="font-semibold text-gray-300 mb-3">Watchlist</h2>
            <ul className="space-y-2 text-sm">
              {watchlist.map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    className={`w-full text-left px-2 py-1 rounded ${
                      selectedStock === s ? "bg-blue-900/60 text-white" : "hover:bg-gray-700"
                    }`}
                    onClick={() => setSelectedStock(s)}
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
            <select
              className="w-full mt-4 p-2 rounded bg-gray-900 border border-gray-600 text-sm"
              value={selectedStock}
              onChange={(e) => setSelectedStock(e.target.value)}
            >
              {symbols.map((s) => (
                <option key={s.symbol} value={s.symbol}>
                  {s.name} ({s.symbol})
                </option>
              ))}
            </select>
            <button
              type="button"
              className="mt-2 w-full text-xs text-blue-400 hover:underline"
              onClick={() => toggleWatch(selectedStock)}
            >
              {watchlist.includes(selectedStock) ? "Remove from watchlist" : "Add to watchlist"}
            </button>
          </aside>

          <div className="lg:col-span-3 space-y-6">
            {dataError && <p className="text-red-400">{dataError}</p>}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <h2 className="text-gray-400 text-sm">Latest close (EOD)</h2>
                <p className="text-2xl font-bold">{selectedStock}</p>
                <p className="text-4xl font-bold mt-2">{formatINR(quote.price)}</p>
                <div className="flex items-center mt-2">
                  {quote.change >= 0 ? (
                    <span className="text-green-500 flex items-center text-sm">
                      <ArrowUpIcon className="w-4 h-4 mr-1" />
                      {quote.change} ({quote.changePercent}%)
                    </span>
                  ) : (
                    <span className="text-red-500 flex items-center text-sm">
                      <ArrowDownIcon className="w-4 h-4 mr-1" />
                      {Math.abs(quote.change)} ({Math.abs(quote.changePercent)}%)
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-2">As of {quote.asOf}</p>
              </div>

              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <h2 className="text-gray-400 text-sm">Next session (champion model)</h2>
                <p className="text-4xl font-bold text-purple-400 mt-2">
                  {loading ? "…" : formatINR(prediction.p50 || prediction.price)}
                </p>
                <p className="text-sm text-gray-400 mt-2">
                  Band {formatINR(prediction.p10)} – {formatINR(prediction.p90)}
                </p>
                <p className="text-sm mt-2 capitalize">
                  Signal:{" "}
                  <span className={prediction.direction === "up" ? "text-green-400" : "text-red-400"}>
                    {prediction.direction}
                  </span>
                </p>
                <div className="mt-3 w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${Math.min(100, prediction.confidence * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Directional accuracy on holdout: {(prediction.confidence * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4">OHLC · last 120 sessions</h2>
              <CandlestickChart
                bars={bars}
                prediction={{ p10: prediction.p10, p50: prediction.p50, p90: prediction.p90 }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
