"use client";

import { useEffect, useState } from "react";
import { DisclaimerBanner } from "@/components/trading/disclaimer-banner";
import { SiteNav } from "@/components/trading/site-nav";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    fetch(`${API_BASE}/backtest?symbol=${symbol}`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then(setData)
      .catch(() => setErr("Backtest not available for this symbol yet."));
  }, [symbol]);

  const m = (data?.metrics || {}) as Record<string, number>;
  const bench = (data?.nifty_buy_hold_benchmark || {}) as Record<string, number>;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8 max-w-3xl">
        <header className="text-center mb-6">
          <h1 className="text-3xl font-bold text-purple-400">Paper backtest</h1>
          <p className="text-gray-400">Long/flat on predicted sign · 10bps cost · 5bps slippage</p>
        </header>
        <SiteNav />
        <DisclaimerBanner />
        <div className="mt-6 max-w-xs mx-auto">
          <input
            className="w-full p-2 rounded bg-gray-800 border border-gray-600"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="NSE symbol"
          />
        </div>
        {err && <p className="text-amber-400 text-center mt-4">{err}</p>}
        {data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
            <MetricCard title="Strategy CAGR" value={pct(m.cagr)} />
            <MetricCard title="Buy & hold CAGR" value={pct(m.buy_hold_cagr)} />
            <MetricCard title="Strategy Sharpe" value={num(m.sharpe)} />
            <MetricCard title="Buy & hold Sharpe" value={num(m.buy_hold_sharpe)} />
            <MetricCard title="Max drawdown" value={pct(m.max_drawdown)} />
            <MetricCard title="Win rate" value={pct(m.win_rate)} />
          </div>
        )}
        {bench.cagr != null && (
          <p className="text-center text-gray-400 text-sm mt-8">
            Nifty index buy-and-hold (same test window): CAGR {pct(bench.cagr)}, Sharpe{" "}
            {num(bench.sharpe)}, max DD {pct(bench.max_drawdown)}
          </p>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
      <div className="text-gray-400 text-sm">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}

function pct(v?: number) {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function num(v?: number) {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toFixed(2);
}
