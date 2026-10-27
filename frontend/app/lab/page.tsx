"use client"

import { useCallback, useEffect, useState } from "react"
import { apiGet, apiPost, ApiError } from "@/lib/api"
import { formatInr } from "@/lib/format"

type LabJob = {
  id: string
  status: string
  candidate_id: string
  config_hash: string
  rejection_reason: string | null
  created_at: string
  log_tail: string
}

type LabSession = {
  id: string
  approved_job_id: string
  status: string
  halt_reason: string | null
  max_names: number
  max_notional: number
  max_daily_loss: number
  apply_india_costs: boolean
}

type LabFill = {
  symbol: string
  model: string
  model_version: string
  forecast_as_of: string
  fill_date: string
  order_id: number | null
}

type LabJobsPayload = {
  jobs: LabJob[]
  approved_job_id: string | null
  previous_approved_job_id: string | null
  session: LabSession | null
}

type LabPortfolio = {
  snapshot: {
    equity: number
    cash: number
    realized_pnl: number
    unrealized_pnl: number
  }
  fills: LabFill[]
  session: LabSession | null
}

export default function LabPage() {
  const [jobs, setJobs] = useState<LabJob[]>([])
  const [approvedId, setApprovedId] = useState<string | null>(null)
  const [session, setSession] = useState<LabSession | null>(null)
  const [book, setBook] = useState<LabPortfolio | null>(null)
  const [candidate, setCandidate] = useState("lstm_returns")
  const [error, setError] = useState<string | null>(null)
  const [symbol, setSymbol] = useState("RELIANCE.NS")
  const [qty, setQty] = useState(1)

  const load = useCallback(() => {
    return Promise.all([apiGet<LabJobsPayload>("/api/lab/jobs"), apiGet<LabPortfolio>("/api/lab/portfolio")])
      .then(([listing, portfolio]) => {
        setJobs(listing.jobs)
        setApprovedId(listing.approved_job_id)
        setSession(listing.session)
        setBook(portfolio)
        setError(null)
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "The lab is not reachable.")
      })
  }, [])

  useEffect(() => {
    load()
    const id = window.setInterval(load, 2000)
    return () => window.clearInterval(id)
  }, [load])

  async function send(path: string, body: unknown) {
    try {
      await apiPost(path, body)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "Request failed.")
    }
    await load()
  }

  const active = jobs.find((job) => job.status === "running" || job.status === "paused")
  const focus = active ?? jobs[0]
  const verified = jobs.find((job) => job.status === "verified")

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Paper lab</h1>
          <p className="text-sm text-[#8b9bb0]">
            One training job. A passing check waits for a person. Orders stay in the paper book.
          </p>
        </div>
        <button
          type="button"
          onClick={() => load()}
          className="rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8b9bb0] hover:text-white"
        >
          Refresh
        </button>
      </div>
      {error && <p className="mt-4 text-sm text-[#f0434c]">{error}</p>}

      <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-4">
        <h2 className="text-sm font-medium">Job</h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="text-xs text-[#8b9bb0]" htmlFor="candidate">
            Candidate
          </label>
          <select
            id="candidate"
            value={candidate}
            onChange={(event) => setCandidate(event.target.value)}
            className="rounded-md border border-white/10 bg-[#07090d] px-2 py-1.5 text-sm"
          >
            <option value="lstm_returns">Returns LSTM</option>
            <option value="lightgbm">LightGBM</option>
          </select>
          <button type="button" className={buttonClass} onClick={() => send("/api/lab/jobs", { action: "start", candidate_id: candidate })}>
            Start
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!active || active.status !== "running"}
            onClick={() => active && send("/api/lab/jobs", { action: "pause", job_id: active.id })}
          >
            Pause
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!active || active.status !== "paused"}
            onClick={() => active && send("/api/lab/jobs", { action: "resume", job_id: active.id })}
          >
            Resume
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!active}
            onClick={() => active && send("/api/lab/jobs", { action: "cancel", job_id: active.id })}
          >
            Cancel
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!verified}
            onClick={() => verified && send(`/api/lab/jobs/${verified.id}/approve`, {})}
          >
            Approve
          </button>
          <button
            type="button"
            className={buttonClass}
            disabled={!approvedId}
            onClick={() => approvedId && send(`/api/lab/jobs/${approvedId}/rollback`, {})}
          >
            Rollback
          </button>
        </div>
        <pre className="mt-4 max-h-40 overflow-auto whitespace-pre-wrap rounded-md bg-[#07090d] p-3 text-xs text-[#c5d0de]">
          {focus?.log_tail || "No log yet."}
        </pre>
      </section>

      <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-4">
        <h2 className="text-sm font-medium">History</h2>
        {jobs.length === 0 ? (
          <p className="mt-3 text-sm text-[#8b9bb0]">No lab jobs yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-white/5 text-sm">
            {jobs.map((job) => (
              <li key={job.id} className="py-2">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-medium">{job.candidate_id}</span>
                  <span className="text-[#8b9bb0]">{job.status}</span>
                  <span className="text-xs text-[#8b9bb0]">{job.id}</span>
                </div>
                {job.rejection_reason && <p className="mt-1 text-[#f0434c]">{job.rejection_reason}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-4 rounded-lg border border-white/10 bg-[#10151c] p-4">
        <h2 className="text-sm font-medium">Paper session</h2>
        <p className="mt-1 text-xs text-[#8b9bb0]">
          {session
            ? `${session.status}${session.halt_reason ? `: ${session.halt_reason}` : ""} · job ${session.approved_job_id}`
            : "No session. Approve a job, then open a session."}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={buttonClass}
            onClick={() =>
              send("/api/lab/session", {
                max_names: 5,
                max_notional: 100000,
                max_daily_loss: 50000,
                apply_india_costs: false,
              })
            }
          >
            Open session
          </button>
          <input
            aria-label="Symbol"
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            className="w-36 rounded-md border border-white/10 bg-[#07090d] px-2 py-1.5 text-sm"
          />
          <input
            aria-label="Quantity"
            type="number"
            min={1}
            value={qty}
            onChange={(event) => setQty(Number(event.target.value))}
            className="w-20 rounded-md border border-white/10 bg-[#07090d] px-2 py-1.5 text-sm"
          />
          <button
            type="button"
            className={buttonClass}
            onClick={() =>
              send("/api/lab/session/tick", {
                symbol,
                side: "BUY",
                qty,
                quote: { price: 1000, as_of: "2026-10-27", stale: false },
                forecast_as_of: "2026-10-16",
              })
            }
          >
            Tick
          </button>
        </div>
        {book && (
          <p className="mt-3 text-sm text-[#8b9bb0]">
            Equity {formatInr(book.snapshot.equity)} · Cash {formatInr(book.snapshot.cash)}
          </p>
        )}
        {book && book.fills.length > 0 && (
          <table className="mt-3 w-full text-left text-sm">
            <thead className="text-xs text-[#8b9bb0]">
              <tr>
                <th className="py-1 font-medium">Symbol</th>
                <th className="py-1 font-medium">Model</th>
                <th className="py-1 font-medium">Job</th>
                <th className="py-1 font-medium">Forecast as of</th>
                <th className="py-1 font-medium">Fill date</th>
              </tr>
            </thead>
            <tbody>
              {book.fills.map((fill) => (
                <tr key={`${fill.order_id}-${fill.symbol}`} className="border-t border-white/5">
                  <td className="py-1">{fill.symbol}</td>
                  <td className="py-1">{fill.model}</td>
                  <td className="py-1">{fill.model_version}</td>
                  <td className="py-1">{fill.forecast_as_of}</td>
                  <td className="py-1">{fill.fill_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {book && book.fills.length === 0 && <p className="mt-3 text-sm text-[#8b9bb0]">No paper session fills.</p>}
      </section>
    </div>
  )
}

const buttonClass = "rounded-md border border-white/10 px-3 py-1.5 text-sm text-[#8b9bb0] hover:text-white disabled:opacity-40"
