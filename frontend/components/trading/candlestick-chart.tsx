"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export type OhlcBar = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  rsi_14?: number | null;
};

type Props = {
  bars: OhlcBar[];
  prediction?: { p10?: number; p50?: number; p90?: number };
};

export function CandlestickChart({ bars, prediction }: Props) {
  const data = bars.map((b) => ({
    ...b,
    body: [Math.min(b.open, b.close), Math.max(b.open, b.close)],
    wick: [b.low, b.high],
    up: b.close >= b.open,
  }));

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 10 }} minTickGap={24} />
          <YAxis stroke="#9CA3AF" domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ backgroundColor: "#1F2937", borderColor: "#374151", color: "#F9FAFB" }}
          />
          <Bar dataKey="wick" fill="#6B7280" barSize={1} />
          <Bar
            dataKey="body"
            barSize={6}
            shape={(props: unknown) => {
              const p = props as {
                x: number;
                y: number;
                width: number;
                height: number;
                payload: { up: boolean; body: number[] };
              };
              const color = p.payload.up ? "#22c55e" : "#ef4444";
              const [lo, hi] = p.payload.body;
              const range = hi - lo || 0.01;
              const h = Math.max(2, (range / (hi || 1)) * 80);
              return (
                <rect x={p.x + 2} y={p.y} width={p.width - 4} height={h} fill={color} />
              );
            }}
          />
          <Line type="monotone" dataKey="close" stroke="#3B82F6" dot={false} strokeWidth={1} />
          {prediction?.p50 != null && (
            <ReferenceLine y={prediction.p50} stroke="#a855f7" strokeDasharray="4 4" label="P50" />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
