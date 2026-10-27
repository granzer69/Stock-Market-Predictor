"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { formatInr, formatPercent, formatVolume, tone } from "@/lib/format"
import type { Quote } from "@/lib/types"

type SortKey = "ticker" | "price" | "change_percent" | "predicted"

const signalTone: Record<string, string> = {
  BUY: "text-[#1fbf75]",
  SELL: "text-[#f0434c]",
  HOLD: "text-[#8b9bb0]",
}

export function NiftyTable({ stocks }: { stocks: Quote[] }) {
  const [query, setQuery] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("ticker")
  const [ascending, setAscending] = useState(true)

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const filtered = stocks.filter((stock) => {
      if (!needle) return true
      return (
        stock.ticker.toLowerCase().includes(needle) ||
        stock.name.toLowerCase().includes(needle) ||
        stock.sector.toLowerCase().includes(needle)
      )
    })
    const sorted = [...filtered].sort((left, right) => {
      const direction = ascending ? 1 : -1
      if (sortKey === "ticker") return left.ticker.localeCompare(right.ticker) * direction
      if (sortKey === "price") return (left.price - right.price) * direction
      if (sortKey === "change_percent") return (left.change_percent - right.change_percent) * direction
      const leftPred = left.prediction?.predicted_return ?? -Infinity
      const rightPred = right.prediction?.predicted_return ?? -Infinity
      return (leftPred - rightPred) * direction
    })
    return sorted
  }, [stocks, query, sortKey, ascending])

  function toggle(key: SortKey) {
    if (sortKey === key) {
      setAscending((value) => !value)
      return
    }
    setSortKey(key)
    setAscending(key === "ticker")
  }

  const modelIds = Array.from(
    new Set(
      stocks
        .map((stock) => stock.prediction?.model)
        .filter((model): model is string => typeof model === "string" && model.length > 0),
    ),
  )
  const forecastHeader = modelIds.length === 1 ? `${modelIds[0]} next` : "Model next"
  const forecastDates = Array.from(
    new Set(stocks.map((stock) => stock.prediction?.as_of).filter((value): value is string => Boolean(value))),
  )
  const quoteDates = Array.from(new Set(stocks.map((stock) => stock.as_of).filter(Boolean)))

  return (
    <section className="px-4 py-6">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Nifty 50</h1>
          <p className="text-sm text-[#8b9bb0]">
            {rows.length} names. Last daily close, with the next-session model close.
            {modelIds.length === 1 ? ` ${modelIds[0]} forecast bar ${forecastDates.length === 1 ? forecastDates[0] : "varies"}.` : ""}
            {quoteDates.length === 1 ? ` Quote session ${quoteDates[0]}.` : ""}
          </p>
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search symbol, company, sector"
          className="w-full rounded-md border border-white/10 bg-[#10151c] px-3 py-2 text-sm outline-none placeholder:text-[#5d6b7c] focus:border-[#e3b341]/60 sm:w-80"
        />
      </div>
      <div className="overflow-x-auto rounded-lg border border-white/10">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-[#10151c] text-[11px] uppercase tracking-wide text-[#8b9bb0]">
            <tr>
              <Header label="Symbol" onClick={() => toggle("ticker")} />
              <th className="px-3 py-2 font-medium">Sector</th>
              <Header label="Last" onClick={() => toggle("price")} align="right" />
              <Header label="Change" onClick={() => toggle("change_percent")} align="right" />
              <th className="px-3 py-2 text-right font-medium">Volume</th>
              <Header label={forecastHeader} onClick={() => toggle("predicted")} align="right" />
              <th className="px-3 py-2 text-right font-medium">Move</th>
              <th className="px-3 py-2 text-right font-medium">Signal</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((stock) => {
              const prediction = stock.prediction
              return (
                <tr key={stock.symbol} className="border-t border-white/5 hover:bg-white/[0.03]">
                  <td className="px-3 py-2.5">
                    <Link href={`/stock/${encodeURIComponent(stock.ticker)}`} className="font-medium hover:text-[#e3b341]">
                      {stock.ticker}
                    </Link>
                    <div className="text-xs text-[#8b9bb0]">{stock.name}</div>
                  </td>
                  <td className="px-3 py-2.5 text-[#8b9bb0]">{stock.sector}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">{formatInr(stock.price)}</td>
                  <td className={`px-3 py-2.5 text-right tabular-nums ${tone(stock.change)}`}>
                    {formatPercent(stock.change_percent)}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums text-[#8b9bb0]">{formatVolume(stock.volume)}</td>
                  <td className="px-3 py-2.5 text-right tabular-nums">
                    {prediction ? formatInr(prediction.predicted_close) : "—"}
                  </td>
                  <td className={`px-3 py-2.5 text-right tabular-nums ${tone(prediction?.predicted_return ?? 0)}`}>
                    {prediction ? formatPercent(prediction.predicted_return * 100) : "—"}
                  </td>
                  <td className={`px-3 py-2.5 text-right text-xs font-medium ${prediction ? signalTone[prediction.signal] : "text-[#8b9bb0]"}`}>
                    {prediction?.signal ?? "—"}
                  </td>
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-[#8b9bb0]">
                  No names match that search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Header({ label, onClick, align = "left" }: { label: string; onClick: () => void; align?: "left" | "right" }) {
  return (
    <th className={`px-3 py-2 font-medium ${align === "right" ? "text-right" : "text-left"}`}>
      <button type="button" onClick={onClick} className="uppercase tracking-wide hover:text-white">
        {label}
      </button>
    </th>
  )
}
