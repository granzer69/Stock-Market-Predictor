"use client"

import { useEffect, useState } from "react"
import { DisclaimerBanner } from "@/components/trading/disclaimer-banner"
import { SiteNav } from "@/components/trading/site-nav"
import { apiGet, ApiError } from "@/lib/api"

type Row = {
  mape_pct?: number | null
  rmse?: number | null
  directional_accuracy?: number | null
  n_symbols?: number | null
}

function shownMape(value: number | null | undefined): string | null {
  if (value == null || Number.isNaN(value)) return null
  return String(value)
}

export default function EvaluationPage() {
  const [rows, setRows] = useState<Record<string, Row>>({})
  const [note, setNote] = useState("")
  const [champion, setChampion] = useState("")
  const [deskModel, setDeskModel] = useState("")
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    apiGet<{
      pooled_model_comparison?: Record<string, Row>
      methodology?: { honest_note?: string }
      champion_model?: string
      production_model?: string
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
        setDeskModel(d.production_model || "lightgbm")
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
  const arimaMape = shownMape(rows.arima_111?.mape_pct)
  const persistenceMape = shownMape(rows.persistence?.mape_pct)
  const pickLine =
    champion && champion !== "momentum" && arimaMape && persistenceMape
      ? `${champion} is the stored directional-accuracy pick. The desk hint is ${deskModel || "lightgbm"}. This row's MAPE is ${arimaMape}, much worse than persistence at ${persistenceMape}.`
      : ""

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <header className="text-center mb-6">
          <h1 className="text-3xl font-bold text-blue-400">Model evaluation</h1>
          <p className="text-gray-400 mt-2">
            Stored comparison from the evaluation report. The rows were not all produced by one split.
          </p>
        </header>
        <SiteNav />
        <DisclaimerBanner />
        {err && <p className="text-red-400 mt-4">{err}</p>}
        {pickLine && <p className="mt-4 text-gray-300">{pickLine}</p>}
        {note && (
          <p className="mt-4 text-gray-400 text-sm">
            {`File's original wording: ${note} The report records one chronological split, not a walk-forward.`}
          </p>
        )}
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
                  <td className="p-2 font-mono">
                    {name}
                    {name === "momentum" && (
                      <p className="mt-1 font-sans text-xs text-amber-300">
                        Pre-fix same-return score: the sign of the return being graded. Not a lagged baseline and not a champion.
                      </p>
                    )}
                    {name === "gru_reliance_sample" && (
                      <p className="mt-1 font-sans text-xs text-amber-300">
                        Single-symbol sample, not a Nifty-wide champion.
                      </p>
                    )}
                  </td>
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
