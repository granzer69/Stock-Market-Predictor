"use client"

import { useEffect, useState } from "react"
import { BacktestEquityChart } from "@/components/backtest-equity-chart"
import { apiGet, ApiError } from "@/lib/api"
import { formatInr, formatPercent } from "@/lib/format"
import type { BacktestReport, PortfolioBacktestReport, RuntimeConfig } from "@/lib/types"

const PERIODS = ["6mo", "1y", "2y", "5y"] as const
const TICKERS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]
const PORTFOLIO_TICKERS = TICKERS.join(",")

type Mode = "single" | "portfolio"

export function ResearchDesk() {
  const [mode, setMode] = useState<Mode>("single")
  const [ticker, setTicker] = useState("RELIANCE")
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("2y")
  const [report, setReport] = useState<BacktestReport | null>(null)
  const [portfolio, setPortfolio] = useState<PortfolioBacktestReport | null>(null)
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet<RuntimeConfig>("/api/config").then(setConfig).catch(() => setConfig(null))
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    const path =
      mode === "single"
        ? `/api/research/backtest/${encodeURIComponent(ticker)}?period=${period}`
        : `/api/research/backtest/portfolio?period=${period}&symbols=${encodeURIComponent(PORTFOLIO_TICKERS)}`

    apiGet<BacktestReport | PortfolioBacktestReport>(path, controller.signal)
      .then((payload) => {
        if (mode === "single") {
          setReport(payload as BacktestReport)
          setPortfolio(null)
        } else {
          setPortfolio(payload as PortfolioBacktestReport)
          setReport(null)
        }
        setError(null)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setError(err instanceof ApiError ? err.message : "Backtest API failed.")
        setReport(null)
        setPortfolio(null)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [ticker, period, mode])

  const active = mode === "single" ? report : portfolio
  const benchLabel = mode === "single" ? "Buy & hold" : "Equal-weight B&H"

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Research backtest</h1>
          <p className="mt-1 text-sm text-[#8b9bb0]">
            Long-only LSTM signals with India delivery costs on daily closes.
          </p>
        </div>
        {config && (
          <span className="rounded-md border border-white/10 bg-[#10151c] px-2 py-1 text-[11px] text-[#8b9bb0]">
            Data: {config.market_data_label}
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <div className="flex rounded-md border border-white/10 p-0.5 text-sm">
          {(["single", "portfolio"] as Mode[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setMode(item)}
              className={`rounded px-3 py-1.5 capitalize ${mode === item ? "bg-white/10 text-white" : "text-[#8b9bb0] hover:text-white"}`}
            >
              {item}
            </button>
          ))}
        </div>
        {mode === "single" && (
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
        )}
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

      {active && !loading && (
        <div className="mt-6 space-y-4">
          {mode === "single" && report && (
            <p className="text-sm text-[#8b9bb0]">
              {report.name} ({report.ticker}) · {report.period} · {report.disclaimer}
            </p>
          )}
          {mode === "portfolio" && portfolio && (
            <p className="text-sm text-[#8b9bb0]">
              Shared cash across {portfolio.symbols.length} names ({portfolio.symbols.map((s) => s.replace(".NS", "")).join(", ")}) · {portfolio.disclaimer}
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <MetricCard title="Strategy equity" value={formatInr(active.strategy.ending_equity)} sub={`Return ${formatPercent(active.strategy.total_return * 100)}`} />
            <MetricCard title={benchLabel} value={formatInr(active.benchmark.ending_equity)} sub={`Return ${formatPercent(active.benchmark.total_return * 100)}`} />
            <MetricCard title="Max drawdown (strategy)" value={formatPercent(active.strategy.max_drawdown * 100)} />
            <MetricCard title="Costs (INR)" value={formatInr(active.strategy.total_costs_inr)} sub={`${active.strategy.trade_count} legs`} />
          </div>
          {active.equity_curve.length > 0 && active.benchmark.equity_curve.length > 0 && (
            <BacktestEquityChart strategy={active.equity_curve} benchmark={active.benchmark.equity_curve} benchmarkLabel={benchLabel} />
          )}
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
