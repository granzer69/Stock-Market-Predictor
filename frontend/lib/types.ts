export type PredictionSummary = {
  predicted_close: number
  predicted_return: number
  direction: "up" | "down" | "flat"
  signal: "BUY" | "HOLD" | "SELL"
  confidence: number | null
  /** Id of the model that produced this forecast, when the payload names one. */
  model?: string
  /** Panel or history date the forecast was scored on. Not the live quote date. */
  as_of?: string
  /** Close of the bar the forecast was scored on. Not the live quote. */
  last_close?: number
  /** Where `confidence` was copied from, when it is a published hit rate. */
  confidence_source?: string | null
}

export type ModelSummary = {
  directional_accuracy: number | null
  mae_log_return: number | null
  naive_mae_log_return: number | null
  trained_at: string | null
  symbols: number | null
  window: number
  signal_threshold: number
  production_model?: string
  champion_model?: string
  champion_directional_accuracy?: number
  baselines?: {
    persistence_mape_pct?: number
    lightgbm_mape_pct?: number
    lightgbm_directional_accuracy?: number
    arima_directional_accuracy?: number
    ma20_directional_accuracy?: number
    legacy_lstm_mape_pct?: number
  }
  honest_note?: string
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

export type PredictionDetail = Omit<PredictionSummary, "model" | "as_of" | "last_close"> & {
  symbol: string
  ticker: string
  name: string
  as_of: string
  last_close: number
  signal_threshold: number
  comparison: ComparisonPoint[]
  /** Served model id, or the LSTM summary object on the artifact path. */
  model: string | ModelSummary | null
  confidence_source?: string | null
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

export type BacktestSummary = {
  starting_cash: number
  ending_equity: number
  total_return: number
  cagr: number
  max_drawdown: number
  sharpe: number
  hit_rate: number
  trade_count: number
  total_costs_inr: number
  turnover_ratio: number
}

export type EquityCurvePoint = {
  time: string
  equity: number
}

export type BacktestBenchmark = {
  kind: string
  ending_equity: number
  total_return: number
  max_drawdown: number
  equity_curve: EquityCurvePoint[]
}

export type BacktestReport = {
  symbol: string
  ticker: string
  name: string
  period: string
  fill?: string
  strategy: BacktestSummary
  equity_curve: EquityCurvePoint[]
  benchmark: BacktestBenchmark
  disclaimer: string
}

export type PortfolioBacktestReport = {
  kind: "portfolio"
  symbols: string[]
  period: string
  fill?: string
  strategy: BacktestSummary
  equity_curve: EquityCurvePoint[]
  benchmark: BacktestBenchmark
  disclaimer: string
}

export type NiftyListing = {
  symbol: string
  ticker: string
  name: string
  sector: string
}

export type RuntimeConfig = {
  market_data_provider: "yahoo" | "nse_csv"
  market_data_label: string
  market_data_failover?: boolean
  research_portfolio_max_symbols: number
  paper_apply_india_costs?: boolean
  backtest_default_fill?: "close" | "next_close"
  model_card_url?: string
}
