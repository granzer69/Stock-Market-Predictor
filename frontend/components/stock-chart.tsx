"use client"

import { useEffect, useRef } from "react"
import type { Bar, LinePoint } from "@/lib/types"

type StockChartProps = {
  bars: Bar[]
  sma20: LinePoint[]
  sma50: LinePoint[]
  predicted: number | null
  forecastLabel?: string
}

export function StockChart({ bars, sma20, sma50, predicted, forecastLabel = "LSTM" }: StockChartProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = ref.current
    if (!container || bars.length === 0) return
    let chart: { remove: () => void } | null = null
    let alive = true

    ;(async () => {
      const lc = await import("lightweight-charts")
      if (!alive || !ref.current) return
      const created = lc.createChart(ref.current, {
        autoSize: true,
        layout: {
          background: { type: lc.ColorType.Solid, color: "transparent" },
          textColor: "#8b9bb0",
          fontFamily: "Inter, sans-serif",
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.04)" },
          horzLines: { color: "rgba(255,255,255,0.04)" },
        },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
        timeScale: { borderColor: "rgba(255,255,255,0.08)" },
        crosshair: { mode: lc.CrosshairMode.Normal },
      })
      chart = created
      if (!alive) {
        created.remove()
        return
      }

      const candles = created.addSeries(lc.CandlestickSeries, {
        upColor: "#1fbf75",
        downColor: "#f0434c",
        borderVisible: false,
        wickUpColor: "#1fbf75",
        wickDownColor: "#f0434c",
      })
      candles.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.28 } })
      candles.setData(
        bars.map((bar) => ({
          time: bar.time,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        })),
      )

      const volume = created.addSeries(lc.HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
      })
      volume.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } })
      volume.setData(
        bars.map((bar) => ({
          time: bar.time,
          value: bar.volume,
          color: bar.close >= bar.open ? "rgba(31,191,117,0.45)" : "rgba(240,67,76,0.45)",
        })),
      )

      const addLine = (points: LinePoint[], color: string) => {
        if (points.length === 0) return
        const series = created.addSeries(lc.LineSeries, {
          color,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        })
        series.setData(points.map((point) => ({ time: point.time, value: point.value })))
      }
      addLine(sma20, "#7aa2f7")
      addLine(sma50, "#e3b341")

      if (predicted != null) {
        candles.createPriceLine({
          price: predicted,
          color: "#e3b341",
          lineWidth: 2,
          lineStyle: lc.LineStyle.Dashed,
          axisLabelVisible: true,
          title: forecastLabel,
        })
      }
      created.timeScale().fitContent()
    })()

    return () => {
      alive = false
      chart?.remove()
    }
  }, [bars, sma20, sma50, predicted, forecastLabel])

  if (bars.length === 0) {
    return <div className="flex h-[460px] items-center justify-center text-sm text-[#8b9bb0]">No candles for this range.</div>
  }

  return <div ref={ref} className="h-[460px] w-full" />
}
