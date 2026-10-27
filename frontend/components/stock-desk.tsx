"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { apiGet, ApiError } from "@/lib/api"
import { formatInr, formatNumber, formatPercent, formatVolume, tone } from "@/lib/format"
import type { History, PredictionDetail } from "@/lib/types"
import { ComparisonChart } from "@/components/comparison-chart"
import { StockChart } from "@/components/stock-chart"
import { TradeTicket } from "@/components/trade-ticket"

const ranges = ["6mo", "1y", "2y", "5y"]

export function StockDesk({ ticker }: { ticker: string }) {
  const [period, setPeriod] = useState("1y")
  const [history, setHistory] = useState<History | null>(null)
  const [prediction, setPrediction] = useState<PredictionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    const encoded = encodeURIComponent(ticker)
    Promise.all([
      apiGet<History>(`/api/market/history/${encoded}?period=${period}`, controller.signal),
      apiGet<PredictionDetail>(`/api/predict/${encoded}`, controller.signal).catch((err: unknown) => {
        if (controller.signal.aborted) throw err
        return null
      }),
    ])
      .then(([bars, forecast]) => {
        setHistory(bars)
        setPrediction(forecast)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setHistory(null)
        setPrediction(null)
        setError(err instanceof ApiError ? err.message : "Could not load this symbol.")
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [ticker, period])

  const quote = history?.quote
  const servedModel = typeof prediction?.model === "string" && prediction.model ? prediction.model : null
  const modelId = servedModel ?? (prediction ? "LSTM" : "Model")

  return (
    <div>
      <div className="mx-auto max-w-7xl px-4 py-6">
        <Link href="/" className="text-xs uppercase tracking-wide text-[#8b9bb0] hover:text-white">
          Nifty 50
        </Link>
        {loading && <p className="mt-6 text-sm text-[#8b9bb0]">Loading {ticker}…</p>}
        {error && <p className="mt-6 text-sm text-[#f0434c]">{error}</p>}
        {history && quote && (
          <>
            <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold">{history.ticker}</h1>
                <p className="text-sm text-[#8b9bb0]">
                  {history.name} · {history.sector}
                </p>
                <div className="mt-2 flex items-baseline gap-3">
                  <span className="text-3xl font-semibold tabular-nums">{formatInr(quote.price)}</span>
                  <span className={`tabular-nums ${tone(quote.change)}`}>
                    {formatInr(quote.change)} ({formatPercent(quote.change_percent)})
                  </span>
                </div>
                <p className="text-xs text-[#8b9bb0]">Close on {quote.as_of}</p>
              </div>
              <div className="flex gap-1">
                {ranges.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setPeriod(item)}
                    className={`rounded-md px-2.5 py-1 text-xs ${period === item ? "bg-white/10 text-white" : "text-[#8b9bb0]"}`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-4">
              <Stat label="Open" value={formatInr(quote.open)} />
              <Stat label="High" value={formatInr(quote.high)} />
              <Stat label="Low" value={formatInr(quote.low)} />
              <Stat label="Volume" value={formatVolume(quote.volume)} />
            </div>

            <div className="mt-4 grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
              <div className="rounded-lg border border-white/10 bg-[#10151c] p-3">
                <div className="mb-2 flex flex-wrap gap-3 text-[11px] uppercase tracking-wide text-[#8b9bb0]">
                  <span>Candles</span>
                  <span className="text-[#7aa2f7]">SMA 20</span>
                  <span className="text-[#e3b341]">SMA 50 · {modelId} next</span>
                </div>
                <StockChart
                  bars={history.bars}
                  sma20={history.sma20}
                  sma50={history.sma50}
                  predicted={prediction?.predicted_close ?? null}
                  forecastLabel={modelId}
                />
              </div>
              <TradeTicket
                ticker={history.ticker}
                price={quote.price}
                asOf={quote.as_of}
                prediction={prediction}
              />
            </div>

            <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-4">
              <h2 className="text-sm font-medium">
                {servedModel
                  ? `Next-session ${servedModel} forecast`
                  : "Recent actual close vs one-step LSTM close"}
              </h2>
              <p className="mb-3 text-xs text-[#8b9bb0]">
                {servedModel
                  ? `${servedModel} scored the panel bar dated ${prediction?.as_of ?? "—"}. The forecast base close is that bar. The quote above is the live session.`
                  : "Each gold point is the close the model expected from the prior 60 sessions. It is a check on the fit, not a promise about the next session."}
                {prediction?.confidence != null
                  ? prediction.confidence_source
                    ? ` Evaluation-report pooled directional accuracy across per-symbol LightGBM fits is ${(prediction.confidence * 100).toFixed(1)}% (${prediction.confidence_source}).`
                    : ` This name's holdout directional hit rate is ${(prediction.confidence * 100).toFixed(0)}%.`
                  : ""}
              </p>
              {prediction ? (
                <ComparisonChart points={prediction.comparison} seriesName={servedModel ? `${servedModel} close` : "LSTM close"} />
              ) : (
                <p className="text-sm text-[#8b9bb0]">Prediction series is not available.</p>
              )}
              {prediction && (
                <p className="mt-2 text-xs text-[#8b9bb0]">
                  Next session {modelId} close {formatInr(prediction.predicted_close)} ({formatPercent(prediction.predicted_return * 100)}), direction {prediction.direction}. Forecast as of {prediction.as_of}, base close {formatNumber(prediction.last_close)}. Quote close on {quote.as_of} is the paper fill.
                </p>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-white/10 px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-[#8b9bb0]">{label}</div>
      <div className="tabular-nums">{value}</div>
    </div>
  )
}
