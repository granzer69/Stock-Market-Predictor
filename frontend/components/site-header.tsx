"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { apiGet } from "@/lib/api"
import type { Quote } from "@/lib/types"
import { MarketTape } from "@/components/market-tape"

const links = [
  { href: "/", label: "Markets" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/lab", label: "Lab" },
  { href: "/research", label: "Research" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/backtest", label: "Backtest" },
]

export function SiteHeader() {
  const pathname = usePathname()
  const [clock, setClock] = useState("")

  useEffect(() => {
    const tick = () => {
      setClock(
        new Date().toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }),
      )
    }
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[#07090d]/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          Bharat Desk
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {links.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href)
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 ${active ? "bg-white/10 text-white" : "text-[#8b9bb0] hover:text-white"}`}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>
        <div className="ml-auto text-right text-xs tabular-nums text-[#8b9bb0]">
          <div className="text-[10px] uppercase tracking-wider">IST</div>
          <div>{clock}</div>
        </div>
      </div>
      <p className="border-t border-white/5 px-4 py-1.5 text-center text-[11px] leading-relaxed text-[#8b9bb0]">
        Paper trading only. Forecasts are model output from daily closes, not investment advice and not a SEBI-registered recommendation. Orders fill at the latest available close and never reach an exchange.
      </p>
      <WorldTape />
    </header>
  )
}

function WorldTape() {
  const [series, setSeries] = useState<Quote[] | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    apiGet<{ series: Quote[] }>("/api/market/globals", controller.signal)
      .then((payload) => setSeries(payload.series))
      .catch(() => {
        if (!controller.signal.aborted) setSeries([])
      })
    return () => controller.abort()
  }, [])

  if (series == null) {
    return <div className="h-14 border-t border-white/10 bg-[#0c1118]" />
  }
  return (
    <div className="border-t border-white/10">
      <MarketTape series={series} />
    </div>
  )
}
