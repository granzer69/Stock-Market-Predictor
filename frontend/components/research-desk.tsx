"use client"

import { useEffect, useState } from "react"
import { apiGet, ApiError } from "@/lib/api"
import { formatInr, formatPercent } from "@/lib/format"
import type { BacktestReport } from "@/lib/types"

const PERIODS = ["6mo", "1y", "2y", "5y"] as const
const TICKERS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]

export function ResearchDesk() {
  const [ticker, setTicker] = useState("RELIANCE")
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("2y")
  const [report, setReport] = useState<BacktestReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    apiGet<BacktestReport>(`/api/research/backtest/${encodeURIComponent(ticker)}?period=${period}`, controller.signal)
      .then((payload) => {
        setReport(payload)
        setError(null)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setError(err instanceof ApiError ? err.message : "Backtest API failed.")
        setReport(null)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [ticker, period])

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <h1 className="text-xl font-semibold">Research backtest</h1>
      <p className="mt-1 text-sm text-[#8b9bb0]">
        Long-only LSTM signals with India delivery costs on daily closes. Compare to buy-and-hold on the same window.
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        <label className="text-sm text-[#8b9bb0]">
          Symbol
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="ml-2 rounded-md border border-white/10 bg-[#10151c] px-2 py-1.5 text-white"
          >
            {TICKERS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-sm text-[#8b9bb0]">
          Period
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as (typeof PERIODS)[number])}
            className="ml-2 rounded-md border border-white/10 bg-[#10151c] px-2 py-1.5 text-white"
          >
            {PERIODS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="mt-6 text-sm text-[#8b9bb0]">Running backtest…</p>}
      {error && <p className="mt-6 text-sm text-[#f0434c]">{error}</p>}

      {report && !loading && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-[#8b9bb0]">
            {report.name} ({report.ticker}) · {report.period} window · {report.disclaimer}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricCard title="Strategy equity" value={formatInr(report.strategy.ending_equity)} sub={`Return ${formatPercent(report.strategy.total_return * 100)}`} />
            <MetricCard title="Buy & hold" value={formatInr(report.benchmark.ending_equity)} sub={`Return ${formatPercent(report.benchmark.total_return * 100)}`} />
            <MetricCard title="Max drawdown (strategy)" value={formatPercent(report.strategy.max_drawdown * 100)} />
            <MetricCard title="Costs (INR)" value={formatInr(report.strategy.total_costs_inr)} sub={`${report.strategy.trade_count} legs`} />
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#10151c] p-4">
      <div className="text-[11px] uppercase tracking-wide text-[#8b9bb0]">{title}</div>
      <div className="mt-1 text-lg font-medium tabular-nums">{value}</div>
      {sub && <div className="mt-1 text-xs text-[#8b9bb0]">{sub}</div>}
    </div>
  )
}
