"use client"

import { useEffect, useState } from "react"
import { DisclaimerBanner } from "@/components/trading/disclaimer-banner"
import { SiteNav } from "@/components/trading/site-nav"
import { apiGet, ApiError } from "@/lib/api"

type Row = {
  mape_pct?: number
  rmse?: number
  directional_accuracy?: number
  n_symbols?: number
}

export default function EvaluationPage() {
  const [rows, setRows] = useState<Record<string, Row>>({})
  const [note, setNote] = useState("")
  const [champion, setChampion] = useState("")
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    apiGet<{
      pooled_model_comparison?: Record<string, Row>
      methodology?: { honest_note?: string }
      champion_model?: string
      error?: string
      hint?: string
    }>("/api/evaluation")
      .then((d) => {
        if (d.error) {
          setErr(d.hint || d.error)
          return
        }
        if (d.pooled_model_comparison) setRows(d.pooled_model_comparison)
        setNote(d.methodology?.honest_note || "")
        setChampion(d.champion_model || "")
      })
      .catch((e: unknown) => {
        setErr(
          e instanceof ApiError
            ? e.message
            : "Could not load evaluation. Check API_ORIGIN and Render deploy.",
        )
      })
  }, [])

  const order = Object.keys(rows).sort()

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <header className="text-center mb-6">
          <h1 className="text-3xl font-bold text-blue-400">Model evaluation</h1>
          <p className="text-gray-400 mt-2">Walk-forward holdout — same split for all baselines</p>
        </header>
        <SiteNav />
        <DisclaimerBanner />
        {err && <p className="text-red-400 mt-4">{err}</p>}
        {champion && (
          <p className="mt-4 text-green-400">
            Champion (by directional accuracy, then RMSE): <strong>{champion}</strong>
          </p>
        )}
        {note && <p className="mt-4 text-gray-400 text-sm">{note}</p>}
        <div className="overflow-x-auto mt-6">
          <table className="w-full text-sm border border-gray-700">
            <thead className="bg-gray-800">
              <tr>
                <th className="p-2 text-left">Model</th>
                <th className="p-2 text-right">Dir. accuracy</th>
                <th className="p-2 text-right">MAPE %</th>
                <th className="p-2 text-right">RMSE</th>
                <th className="p-2 text-right">Symbols</th>
              </tr>
            </thead>
            <tbody>
              {order.map((name) => (
                <tr key={name} className="border-t border-gray-800">
                  <td className="p-2 font-mono">{name}</td>
                  <td className="p-2 text-right">
                    {rows[name].directional_accuracy?.toFixed(4) ?? "—"}
                  </td>
                  <td className="p-2 text-right">{rows[name].mape_pct?.toFixed(4) ?? "—"}</td>
                  <td className="p-2 text-right">{rows[name].rmse?.toFixed(4) ?? "—"}</td>
                  <td className="p-2 text-right">{rows[name].n_symbols ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
