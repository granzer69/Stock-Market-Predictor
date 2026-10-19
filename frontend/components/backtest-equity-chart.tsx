"use client"

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { formatInr, formatWhen } from "@/lib/format"

type Point = { time: string; equity: number }

export function BacktestEquityChart({
  strategy,
  benchmark,
  benchmarkLabel = "Benchmark",
}: {
  strategy: Point[]
  benchmark: Point[]
  benchmarkLabel?: string
}) {
  const benchMap = new Map(benchmark.map((point) => [point.time, point.equity]))
  const data = strategy.map((point) => ({
    time: point.time,
    strategy: point.equity,
    benchmark: benchMap.get(point.time) ?? null,
  }))

  return (
    <section className="rounded-lg border border-white/10 bg-[#10151c] p-4">
      <h2 className="mb-3 text-sm font-medium">Equity curve</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="time" tickFormatter={(value) => formatWhen(String(value))} tick={{ fill: "#8b9bb0", fontSize: 11 }} minTickGap={32} />
            <YAxis tickFormatter={(value) => formatInr(Number(value))} tick={{ fill: "#8b9bb0", fontSize: 11 }} width={96} domain={["auto", "auto"]} />
            <Tooltip
              formatter={(value) => formatInr(Number(value))}
              labelFormatter={(value) => formatWhen(String(value))}
              contentStyle={{ background: "#10151c", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#8b9bb0" }} />
            <Area type="monotone" dataKey="strategy" name="LSTM strategy" stroke="#e3b341" fill="rgba(227,179,65,0.12)" />
            <Area type="monotone" dataKey="benchmark" name={benchmarkLabel} stroke="#5b8def" fill="rgba(91,141,239,0.08)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
