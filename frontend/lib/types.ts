export type PredictionSummary = {
  predicted_close: number
  predicted_return: number
  direction: "up" | "down" | "flat"
  signal: "BUY" | "HOLD" | "SELL"
  confidence: number | null
}

export type ModelSummary = {
  directional_accuracy: number | null
  mae_log_return: number | null
  naive_mae_log_return: number | null
  trained_at: string | null
  symbols: number | null
  window: number
  signal_threshold: number
}

export type Quote = {
  symbol: string
  ticker: string
  name: string
  sector: string
  unit: string
  kind: string
  price: number
  previous_close: number
  change: number
  change_percent: number
  open: number
  high: number
  low: number
  volume: number
  as_of: string
  prediction?: PredictionSummary | null
}

export type Bar = {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type LinePoint = {
  time: string
  value: number
}

export type History = {
  symbol: string
  ticker: string
  name: string
  sector: string
  unit: string
  kind: string
  period: string
  quote: {
    price: number
    previous_close: number
    change: number
    change_percent: number
    open: number
    high: number
    low: number
    volume: number
    as_of: string
  }
  bars: Bar[]
  sma20: LinePoint[]
  sma50: LinePoint[]
}

export type ComparisonPoint = {
  date: string
  actual: number
  predicted: number
}

export type PredictionDetail = PredictionSummary & {
  symbol: string
  ticker: string
  name: string
  as_of: string
  last_close: number
  signal_threshold: number
  comparison: ComparisonPoint[]
  model: ModelSummary | null
}

export type Position = {
  symbol: string
  ticker: string
  name: string
  qty: number
  avg_cost: number
  last: number
  market_value: number
  unrealized_pnl: number
  stale: boolean
}

export type EquityPoint = {
  time: string
  equity: number
  cash: number
}

export type Portfolio = {
  cash: number
  starting_cash: number
  realized_pnl: number
  unrealized_pnl: number
  market_value: number
  equity: number
  positions: Position[]
  equity_curve: EquityPoint[]
}

export type Order = {
  id: number
  symbol: string
  ticker: string
  name: string
  side: "BUY" | "SELL"
  qty: number
  price: number
  notional: number
  created_at: string
}
