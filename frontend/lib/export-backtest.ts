import type { BacktestReport, PortfolioBacktestReport } from "@/lib/types"

export type ExportableBacktest = BacktestReport | PortfolioBacktestReport

function triggerDownload(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function downloadBacktestJson(report: ExportableBacktest, mode: "single" | "portfolio") {
  const stamp = new Date().toISOString().slice(0, 10)
  const label =
    mode === "single" && "ticker" in report ? report.ticker : `portfolio-${report.symbols?.length ?? 0}`
  triggerDownload(`bharat-desk-backtest-${label}-${stamp}.json`, new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }))
}

export function downloadBacktestCsv(report: ExportableBacktest, mode: "single" | "portfolio") {
  const benchMap = new Map(report.benchmark.equity_curve.map((point) => [point.time, point.equity]))
  const lines = ["date,strategy_equity,benchmark_equity"]
  for (const point of report.equity_curve) {
    const bench = benchMap.get(point.time)
    lines.push(`${point.time},${point.equity},${bench ?? ""}`)
  }
  const stamp = new Date().toISOString().slice(0, 10)
  const label =
    mode === "single" && "ticker" in report ? report.ticker : `portfolio-${report.symbols?.length ?? 0}`
  triggerDownload(`bharat-desk-backtest-${label}-${stamp}.csv`, new Blob([lines.join("\n") + "\n"], { type: "text/csv;charset=utf-8" }))
}
