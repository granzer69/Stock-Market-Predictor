import { formatPercent, formatPrice, tone } from "@/lib/format"
import type { Quote } from "@/lib/types"

export function MarketTape({ series }: { series: Quote[] }) {
  if (series.length === 0) {
    return (
      <div className="border-b border-white/10 px-4 py-3 text-sm text-[#8b9bb0]">
        World tape is unavailable right now.
      </div>
    )
  }

  return (
    <div className="scrollbar-tape flex gap-2 overflow-x-auto bg-[#0c1118] px-4 pb-1 pt-2">
      {series.map((item) => (
        <div key={item.symbol} className="min-w-[150px] shrink-0 rounded-md border border-white/5 px-3 py-2">
          <div className="truncate text-[11px] uppercase tracking-wide text-[#8b9bb0]">{item.name}</div>
          <div className="mt-0.5 font-medium tabular-nums">{formatPrice(item.price, item.unit)}</div>
          <div className={`text-xs tabular-nums ${tone(item.change)}`}>
            {formatPercent(item.change_percent)}
          </div>
        </div>
      ))}
    </div>
  )
}
