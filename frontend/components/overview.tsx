"use client"

import { useEffect, useState } from "react"
import { apiGet, ApiError } from "@/lib/api"
import type { ModelSummary, Quote } from "@/lib/types"
import { NiftyTable } from "@/components/nifty-table"
import Link from "next/link"

export function Overview() {
  const [stocks, setStocks] = useState<Quote[]>([])
  const [model, setModel] = useState<ModelSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    async function loadOverview(attempt: number) {
      setLoading(true)
      if (attempt === 0) setError(null)
      try {
        const overview = await apiGet<{ stocks: Quote[]; model: ModelSummary | null }>(
          "/api/market/overview",
          controller.signal,
        )
        if (cancelled) return
        setStocks(overview.stocks)
        setModel(overview.model)
        setError(null)
      } catch (err: unknown) {
        if (controller.signal.aborted || cancelled) return
        if (attempt === 0) {
          await new Promise((r) => setTimeout(r, 2500))
          if (!cancelled) return loadOverview(1)
          return
        }
        setError(err instanceof ApiError ? err.message : "The market API is not reachable.")
      } finally {
        if (!cancelled && !controller.signal.aborted) setLoading(false)
      }
    }

    void loadOverview(0)
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [])

  return (
    <div>
      <div className="mx-auto max-w-7xl">
        {loading && (
          <p className="px-4 py-8 text-sm text-[#8b9bb0]">
            Loading Nifty 50 quotes and forecasts… (first load after the API sleeps can take up to a minute)
          </p>
        )}
        {error && <p className="px-4 py-8 text-sm text-[#f0434c]">{error}</p>}
        {!loading && !error && (
          <>
            <ModelStrip model={model} count={stocks.length} />
            <NiftyTable stocks={stocks} />
          </>
        )}
      </div>
    </div>
  )
}

function ModelStrip({ model, count }: { model: ModelSummary | null; count: number }) {
  if (!model) {
    return (
      <p className="px-4 pt-6 text-sm text-[#8b9bb0]">
        {count} quotes loaded. Forecast model loading…
      </p>
    )
  }

  const baselines = model.baselines
  const dir = model.directional_accuracy
  const lgbDir = baselines?.lightgbm_directional_accuracy
  const arimaDir = baselines?.arima_directional_accuracy
  const ma20Dir = baselines?.ma20_directional_accuracy

  return (
    <div className="space-y-3 px-4 pt-6 text-sm leading-relaxed text-[#8b9bb0]">
      <p>
        <strong className="text-[#e7eef7]">Production:</strong> {model.production_model ?? "lightgbm"}{" "}
        directional accuracy {lgbDir != null ? `${(lgbDir * 100).toFixed(1)}%` : "—"} on holdout.
        Best simple baseline: {model.champion_model ?? "ARIMA/MA20"}{" "}
        {model.champion_directional_accuracy != null
          ? `${(model.champion_directional_accuracy * 100).toFixed(1)}%`
          : arimaDir != null
            ? `${(arimaDir * 100).toFixed(1)}% (ARIMA)`
            : "—"}
        . Legacy LSTM close MAPE ~{baselines?.legacy_lstm_mape_pct ?? "1.39"}% vs persistence{" "}
        {baselines?.persistence_mape_pct ?? "1.23"}%.
        {model.honest_note ? ` ${model.honest_note}` : ""}
      </p>
      <p className="text-xs">
        Signals need a move past {((model.signal_threshold ?? 0.003) * 100).toFixed(1)}% — most names show{" "}
        <span className="text-[#e7eef7]">HOLD</span> when the model is near a flat forecast.{" "}
        <Link href="/evaluation" className="text-[#5b9cf5] underline">
          Full baseline table
        </Link>{" "}
        ·{" "}
        <Link href="/backtest" className="text-[#5b9cf5] underline">
          Paper backtest
        </Link>
      </p>
      {dir != null && model.mae_log_return != null && model.naive_mae_log_return != null && (
        <p className="text-xs">
          LSTM log-return MAE {model.mae_log_return.toFixed(4)} vs naive {model.naive_mae_log_return.toFixed(4)}.
        </p>
      )}
      {ma20Dir != null && (
        <p className="text-xs tabular-nums">
          Holdout direction: LightGBM {(lgbDir! * 100).toFixed(1)}% · MA20 {(ma20Dir * 100).toFixed(1)}% · ARIMA{" "}
          {((arimaDir ?? 0) * 100).toFixed(1)}%
        </p>
      )}
    </div>
  )
}
