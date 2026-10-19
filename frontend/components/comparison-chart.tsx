"use client"

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { ComparisonPoint } from "@/lib/types"

export function ComparisonChart({ points }: { points: ComparisonPoint[] }) {
  if (points.length === 0) return null
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="date" tick={{ fill: "#8b9bb0", fontSize: 11 }} minTickGap={28} />
          <YAxis tick={{ fill: "#8b9bb0", fontSize: 11 }} domain={["auto", "auto"]} width={72} />
          <Tooltip
            contentStyle={{ background: "#10151c", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }}
            labelStyle={{ color: "#8b9bb0" }}
          />
          <Legend />
          <Line type="monotone" dataKey="actual" name="Actual close" stroke="#e7eef7" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="predicted" name="LSTM close" stroke="#e3b341" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
