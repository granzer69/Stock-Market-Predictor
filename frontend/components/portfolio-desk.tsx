"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { apiGet, ApiError } from "@/lib/api"
import { formatInr, formatPercent, formatWhen, tone } from "@/lib/format"
import type { Order, Portfolio } from "@/lib/types"

export function PortfolioDesk() {
  const [book, setBook] = useState<Portfolio | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [error, setError] = useState<string | null>(null)

  function load() {
    return Promise.all([apiGet<Portfolio>("/api/portfolio"), apiGet<{ orders: Order[] }>("/api/orders")])
      .then(([portfolio, blotter]) => {
        setBook(portfolio)
        setOrders(blotter.orders)
        setError(null)
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "The paper book is not reachable.")
      })
  }

  useEffect(() => {
    load()
  }, [])

  const pnl = book ? book.equity - book.starting_cash : 0

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Paper portfolio</h1>
          <p className="text-sm text-[#8b9bb0]">Virtual rupees. Marks use the latest daily close.</p>
        </div>
        <button type="button" onClick={() => load()} className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8b9bb0] hover:text-white">
          Refresh
        </button>
      </div>
      {error && <p className="mt-4 text-sm text-[#f0434c]">{error}</p>}
      {book && (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Equity" value={formatInr(book.equity)} />
            <Stat label="Cash" value={formatInr(book.cash)} />
            <Stat label="Unrealized" value={formatInr(book.unrealized_pnl)} toneValue={book.unrealized_pnl} />
            <Stat label="Since start" value={`${formatInr(pnl)} (${formatPercent((pnl / book.starting_cash) * 100)})`} toneValue={pnl} />
          </div>
          <p className="mt-2 text-xs text-[#8b9bb0]">Realized {formatInr(book.realized_pnl)}. Started with {formatInr(book.starting_cash)}.</p>

          <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-4">
            <h2 className="mb-3 text-sm font-medium">Equity</h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={book.equity_curve}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="time" tickFormatter={(value) => formatWhen(String(value))} tick={{ fill: "#8b9bb0", fontSize: 11 }} minTickGap={28} />
                  <YAxis tickFormatter={(value) => formatInr(Number(value))} tick={{ fill: "#8b9bb0", fontSize: 11 }} width={96} domain={["auto", "auto"]} />
                  <Tooltip
                    formatter={(value) => formatInr(Number(value))}
                    labelFormatter={(value) => formatWhen(String(value))}
                    contentStyle={{ background: "#10151c", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
                  />
                  <Area type="monotone" dataKey="equity" name="Equity" stroke="#e3b341" fill="rgba(227,179,65,0.15)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="mt-4 overflow-x-auto rounded-lg border border-white/10">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-[#10151c] text-[11px] uppercase tracking-wide text-[#8b9bb0]">
                <tr>
                  <th className="px-3 py-2 font-medium">Position</th>
                  <th className="px-3 py-2 text-right font-medium">Qty</th>
                  <th className="px-3 py-2 text-right font-medium">Avg cost</th>
                  <th className="px-3 py-2 text-right font-medium">Last</th>
                  <th className="px-3 py-2 text-right font-medium">Value</th>
                  <th className="px-3 py-2 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {book.positions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-[#8b9bb0]">
                      No positions. Open a name from the Nifty 50 table to place a paper order.
                    </td>
                  </tr>
                )}
                {book.positions.map((position) => (
                  <tr key={position.symbol} className="border-t border-white/5">
                    <td className="px-3 py-2.5">
                      <Link href={`/stock/${encodeURIComponent(position.ticker)}`} className="font-medium hover:text-[#e3b341]">
                        {position.ticker}
                      </Link>
                      <div className="text-xs text-[#8b9bb0]">{position.name}</div>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{position.qty}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{formatInr(position.avg_cost)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {formatInr(position.last)}
                      {position.stale ? " *" : ""}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{formatInr(position.market_value)}</td>
                    <td className={`px-3 py-2.5 text-right tabular-nums ${tone(position.unrealized_pnl)}`}>
                      {formatInr(position.unrealized_pnl)} ({formatPercent(((position.last - position.avg_cost) / position.avg_cost) * 100)})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="mt-4 overflow-x-auto rounded-lg border border-white/10">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="bg-[#10151c] text-[11px] uppercase tracking-wide text-[#8b9bb0]">
                <tr>
                  <th className="px-3 py-2 font-medium">Time (IST)</th>
                  <th className="px-3 py-2 font-medium">Side</th>
                  <th className="px-3 py-2 font-medium">Symbol</th>
                  <th className="px-3 py-2 text-right font-medium">Qty</th>
                  <th className="px-3 py-2 text-right font-medium">Price</th>
                  <th className="px-3 py-2 text-right font-medium">Notional</th>
                </tr>
              </thead>
              <tbody>
                {orders.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-[#8b9bb0]">
                      No fills yet.
                    </td>
                  </tr>
                )}
                {orders.map((order) => (
                  <tr key={order.id} className="border-t border-white/5">
                    <td className="px-3 py-2.5 text-[#8b9bb0]">{formatWhen(order.created_at)}</td>
                    <td className={`px-3 py-2.5 font-medium ${order.side === "BUY" ? "text-[#1fbf75]" : "text-[#f0434c]"}`}>{order.side}</td>
                    <td className="px-3 py-2.5">{order.ticker}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{order.qty}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{formatInr(order.price)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{formatInr(order.notional)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}

function Stat({ label, value, toneValue }: { label: string; value: string; toneValue?: number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[#10151c] px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-[#8b9bb0]">{label}</div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${toneValue == null ? "" : tone(toneValue)}`}>{value}</div>
    </div>
  )
}
