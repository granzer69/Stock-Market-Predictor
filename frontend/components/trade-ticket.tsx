"use client"

import { useEffect, useState } from "react"
import { apiGet, apiPost, ApiError } from "@/lib/api"
import { formatInr, formatPercent, tone } from "@/lib/format"
import type { Order, Portfolio, PredictionDetail, PredictionSummary } from "@/lib/types"

type TradeTicketProps = {
  ticker: string
  price: number
  asOf: string
  prediction: PredictionSummary | PredictionDetail | null
}

export function TradeTicket({ ticker, price, asOf, prediction }: TradeTicketProps) {
  const [qty, setQty] = useState(1)
  const [cash, setCash] = useState<number | null>(null)
  const [held, setHeld] = useState(0)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<"BUY" | "SELL" | null>(null)

  async function refreshBook() {
    const portfolio = await apiGet<Portfolio>("/api/portfolio")
    setCash(portfolio.cash)
    const position = portfolio.positions.find((item) => item.ticker === ticker)
    setHeld(position?.qty ?? 0)
  }

  useEffect(() => {
    refreshBook().catch(() => setCash(null))
  }, [ticker])

  const notional = qty * price
  const signal = prediction?.signal
  const modelId = prediction && typeof prediction.model === "string" ? prediction.model : null

  async function submit(side: "BUY" | "SELL") {
    setPending(side)
    setError(null)
    setMessage(null)
    try {
      const order = await apiPost<Order>("/api/orders", { symbol: ticker, side, qty })
      setMessage(`${order.side} ${order.qty} ${order.ticker} filled at ${formatInr(order.price)}`)
      await refreshBook()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Order failed")
    } finally {
      setPending(null)
    }
  }

  return (
    <aside className="rounded-lg border border-white/10 bg-[#10151c] p-4">
      <div className="text-xs uppercase tracking-wide text-[#8b9bb0]">Paper order</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{formatInr(price)}</div>
      <p className="text-xs text-[#8b9bb0]">Latest close {asOf}. This is the fill price.</p>

      {prediction && (
        <div className="mt-4 rounded-md border border-white/10 px-3 py-2 text-sm">
          <div className="text-xs uppercase tracking-wide text-[#8b9bb0]">
            {modelId ? `${modelId} hint` : "Model hint"}
          </div>
          <div className={`mt-1 font-medium ${signal === "BUY" ? "text-[#1fbf75]" : signal === "SELL" ? "text-[#f0434c]" : "text-[#8b9bb0]"}`}>
            {signal} · next close {formatInr(prediction.predicted_close)}
          </div>
          <div className={`text-xs tabular-nums ${tone(prediction.predicted_return)}`}>
            {formatPercent(prediction.predicted_return * 100)}
            {prediction.confidence != null
              ? prediction.confidence_source
                ? ` · ${modelId ?? "model"} holdout ${(prediction.confidence * 100).toFixed(1)}%`
                : ` · holdout hit rate ${(prediction.confidence * 100).toFixed(0)}%`
              : ""}
          </div>
          {prediction.as_of && (
            <p className="mt-1 text-[11px] text-[#8b9bb0]">
              Forecast as of {prediction.as_of}
              {prediction.last_close != null ? `, base close ${formatInr(prediction.last_close)}` : ""}. Fill uses the quote above.
            </p>
          )}
          <p className="mt-1 text-[11px] leading-relaxed text-[#8b9bb0]">A hint from the model, not an instruction to trade.</p>
        </div>
      )}

      <label className="mt-4 block text-xs uppercase tracking-wide text-[#8b9bb0]" htmlFor="qty">
        Shares
      </label>
      <input
        id="qty"
        type="number"
        min={1}
        step={1}
        value={qty}
        onChange={(event) => setQty(Math.max(1, Math.floor(Number(event.target.value) || 1)))}
        className="mt-1 w-full rounded-md border border-white/10 bg-[#07090d] px-3 py-2 tabular-nums outline-none focus:border-[#e3b341]/60"
      />
      <div className="mt-2 flex justify-between text-xs text-[#8b9bb0]">
        <span>Notional {formatInr(notional)}</span>
        <span>Held {held}</span>
      </div>
      <div className="text-xs text-[#8b9bb0]">Cash {cash == null ? "—" : formatInr(cash)}</div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={pending != null || (cash != null && notional > cash)}
          onClick={() => submit("BUY")}
          className="rounded-md bg-[#1fbf75] px-3 py-2 text-sm font-semibold text-[#062116] disabled:opacity-40"
        >
          {pending === "BUY" ? "Buying" : "Buy"}
        </button>
        <button
          type="button"
          disabled={pending != null || qty > held}
          onClick={() => submit("SELL")}
          className="rounded-md bg-[#f0434c] px-3 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {pending === "SELL" ? "Selling" : "Sell"}
        </button>
      </div>
      {message && <p className="mt-3 text-sm text-[#1fbf75]">{message}</p>}
      {error && <p className="mt-3 text-sm text-[#f0434c]">{error}</p>}
    </aside>
  )
}
