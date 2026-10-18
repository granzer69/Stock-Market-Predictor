"use client"

import { useEffect, useState } from "react"
import { apiGet, ApiError } from "@/lib/api"
import type { ModelSummary, Quote } from "@/lib/types"
import { NiftyTable } from "@/components/nifty-table"

export function Overview() {
  const [stocks, setStocks] = useState<Quote[]>([])
  const [model, setModel] = useState<ModelSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    apiGet<{ stocks: Quote[]; model: ModelSummary | null }>("/api/market/overview", controller.signal)
      .then((overview) => {
        setStocks(overview.stocks)
        setModel(overview.model)
        setError(null)
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setError(err instanceof ApiError ? err.message : "The market API is not reachable.")
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  return (
    <div>
      <div className="mx-auto max-w-7xl">
        {loading && <p className="px-4 py-8 text-sm text-[#8b9bb0]">Loading Nifty 50 closes…</p>}
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
  if (!model || model.directional_accuracy == null || model.mae_log_return == null) {
    return (
      <p className="px-4 pt-6 text-sm text-[#8b9bb0]">
        {count} quotes loaded. The forecast model is not available yet, so the next-close column stays empty.
      </p>
    )
  }
  const beats = model.naive_mae_log_return != null && model.mae_log_return < model.naive_mae_log_return
  return (
    <p className="px-4 pt-6 text-sm leading-relaxed text-[#8b9bb0]">
      Holdout directional accuracy {(model.directional_accuracy * 100).toFixed(1)}% across {model.symbols ?? "the"} trained names.
      Mean absolute log-return error {model.mae_log_return.toFixed(4)} versus {model.naive_mae_log_return?.toFixed(4)} for a flat forecast.
      {beats ? " The model is tighter than predicting no change." : " A flat forecast is as tight or tighter on this holdout."}
      {" "}A buy or sell hint needs a predicted move past {((model.signal_threshold ?? 0.003) * 100).toFixed(1)}%.
    </p>
  )
}
