"use client"

import { useEffect, useMemo, useState } from "react"
import { BacktestEquityChart } from "@/components/backtest-equity-chart"
import { apiGet, ApiError } from "@/lib/api"
import { downloadBacktestCsv, downloadBacktestJson } from "@/lib/export-backtest"
import { formatInr, formatPercent } from "@/lib/format"
import type { BacktestReport, NiftyListing, PortfolioBacktestReport, RuntimeConfig } from "@/lib/types"

const PERIODS = ["6mo", "1y", "2y", "5y"] as const
const DEFAULT_PORTFOLIO = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ITC"]

type Mode = "single" | "portfolio"

export function ResearchDesk() {
  const [mode, setMode] = useState<Mode>("single")
  const [universe, setUniverse] = useState<NiftyListing[]>([])
  const [ticker, setTicker] = useState("RELIANCE")
  const [portfolioPick, setPortfolioPick] = useState<string[]>(DEFAULT_PORTFOLIO)
  const [portfolioQuery, setPortfolioQuery] = useState("")
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("2y")
  const [fill, setFill] = useState<"close" | "next_close">("close")
  const [report, setReport] = useState<BacktestReport | null>(null)
  const [portfolio, setPortfolio] = useState<PortfolioBacktestReport | null>(null)
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const maxPortfolio = config?.research_portfolio_max_symbols ?? 10

  useEffect(() => {
    apiGet<RuntimeConfig>("/api/config")
      .then((cfg) => {
        setConfig(cfg)
        if (cfg.backtest_default_fill) setFill(cfg.backtest_default_fill)
      })
      .catch(() => setConfig(null))
    apiGet<{ names: NiftyListing[] }>("/api/universe/nifty50")
      .then((payload) => setUniverse(payload.names))
      .catch(() => setUniverse([]))
  }, [])

  const portfolioSymbolsParam = useMemo(() => portfolioPick.join(","), [portfolioPick])

  useEffect(() => {
    if (mode === "portfolio" && portfolioPick.length < 2) return
    const controller = new AbortController()
    setLoading(true)
    const fillQuery = `&fill=${encodeURIComponent(fill)}`
    const path =
      mode === "single"
        ? `/api/research/backtest/${encodeURIComponent(ticker)}?period=${period}${fillQuery}`
        : `/api/research/backtest/portfolio?period=${period}&symbols=${encodeURIComponent(portfolioSymbolsParam)}${fillQuery}`

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
  }, [ticker, period, mode, portfolioSymbolsParam, fill])

  const tickers = universe.length > 0 ? universe.map((item) => item.ticker) : DEFAULT_PORTFOLIO
  const filteredUniverse = useMemo(() => {
    const needle = portfolioQuery.trim().toLowerCase()
    if (!needle) return universe
    return universe.filter(
      (item) =>
        item.ticker.toLowerCase().includes(needle) ||
        item.name.toLowerCase().includes(needle) ||
        item.sector.toLowerCase().includes(needle),
    )
  }, [universe, portfolioQuery])

  const active = mode === "single" ? report : portfolio
  const benchLabel = mode === "single" ? "Buy & hold" : "Equal-weight B&H"

  function togglePortfolioSymbol(symbolTicker: string) {
    setPortfolioPick((current) => {
      if (current.includes(symbolTicker)) {
        return current.filter((item) => item !== symbolTicker)
      }
      if (current.length >= maxPortfolio) return current
      return [...current, symbolTicker]
    })
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Research backtest</h1>
          <p className="mt-1 text-sm text-[#8b9bb0]">
            Long-only LSTM signals with India delivery costs on daily closes.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {config && (
            <span className="rounded-md border border-white/10 bg-[#10151c] px-2 py-1 text-[11px] text-[#8b9bb0]">
              Data: {config.market_data_label}
              {config.paper_apply_india_costs ? " · paper costs on" : ""}
            </span>
          )}
          {config?.model_card_url && (
            <a
              href={config.model_card_url}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] text-[#e3b341] underline-offset-2 hover:underline"
            >
              Model card
            </a>
          )}
        </div>
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
              className="ml-2 max-w-[12rem] rounded-md border border-white/10 bg-[#10151c] px-2 py-1.5 text-white"
            >
              {tickers.map((item) => (
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
        <label className="text-sm text-[#8b9bb0]">
          Fill
          <select
            value={fill}
            onChange={(e) => setFill(e.target.value as "close" | "next_close")}
            className="ml-2 rounded-md border border-white/10 bg-[#10151c] px-2 py-1.5 text-white"
          >
            <option value="close">Same close</option>
            <option value="next_close">Next close</option>
          </select>
        </label>
      </div>

      {mode === "portfolio" && (
        <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-[#8b9bb0]">
              Portfolio names ({portfolioPick.length}/{maxPortfolio}, min 2)
            </p>
            <input
              value={portfolioQuery}
              onChange={(e) => setPortfolioQuery(e.target.value)}
              placeholder="Search Nifty 50"
              className="w-full max-w-xs rounded-md border border-white/10 bg-[#07090d] px-2 py-1 text-sm outline-none placeholder:text-[#5d6b7c] sm:w-56"
            />
          </div>
          <div className="mt-2 max-h-40 overflow-y-auto scrollbar-tape">
            <div className="flex flex-wrap gap-2">
              {filteredUniverse.map((item) => {
                const selected = portfolioPick.includes(item.ticker)
                const disabled = !selected && portfolioPick.length >= maxPortfolio
                return (
                  <button
                    key={item.ticker}
                    type="button"
                    disabled={disabled}
                    onClick={() => togglePortfolioSymbol(item.ticker)}
                    className={`rounded-md border px-2 py-1 text-xs ${selected ? "border-[#e3b341]/50 bg-[#e3b341]/10 text-white" : "border-white/10 text-[#8b9bb0] hover:text-white"} ${disabled ? "opacity-40" : ""}`}
                  >
                    {item.ticker}
                  </button>
                )
              })}
            </div>
          </div>
          {portfolioPick.length < 2 && (
            <p className="mt-2 text-xs text-[#f0434c]">Select at least two symbols to run the portfolio backtest.</p>
          )}
        </section>
      )}

      {loading && <p className="mt-6 text-sm text-[#8b9bb0]">Running backtest…</p>}
      {error && <p className="mt-6 text-sm text-[#f0434c]">{error}</p>}

      {active && !loading && (
        <div className="mt-6 space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => downloadBacktestJson(active, mode)}
              className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8b9bb0] hover:text-white"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={() => downloadBacktestCsv(active, mode)}
              className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8b9bb0] hover:text-white"
            >
              Export CSV
            </button>
          </div>
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
