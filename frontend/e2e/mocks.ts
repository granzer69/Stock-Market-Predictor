import type { Order, Portfolio, Quote } from "@/lib/types"

export const mockStock: Quote = {
  symbol: "RELIANCE.NS",
  ticker: "RELIANCE",
  name: "Reliance Industries",
  sector: "Energy",
  unit: "INR",
  kind: "equity",
  price: 2500,
  previous_close: 2480,
  change: 20,
  change_percent: 0.8064516129032258,
  open: 2490,
  high: 2510,
  low: 2485,
  volume: 1_000_000,
  as_of: "2026-10-27",
  prediction: {
    predicted_close: 2410,
    predicted_return: 2410 / 2400 - 1,
    direction: "up",
    signal: "BUY",
    confidence: 0.4707,
    confidence_source: "evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy",
    model: "lightgbm",
    as_of: "2026-10-16",
    last_close: 2400,
  },
}

export const mockOverview = {
  stocks: [mockStock],
  model: {
    directional_accuracy: 0.487,
    mae_log_return: 0.01205,
    naive_mae_log_return: 0.01199,
    trained_at: "2026-10-19T06:34:07Z",
    symbols: 50,
    window: 60,
    signal_threshold: 0.003,
    production_model: "lightgbm",
    champion_model: "ARIMA(1,1,1)",
    champion_directional_accuracy: 0.507,
    baselines: {
      lightgbm_directional_accuracy: 0.471,
      arima_directional_accuracy: 0.507,
      persistence_mape_pct: 1.23,
      legacy_lstm_mape_pct: 1.39,
    },
  },
}

export const mockHistory = {
  symbol: "RELIANCE.NS",
  ticker: "RELIANCE",
  name: "Reliance Industries",
  sector: "Energy",
  unit: "INR",
  kind: "equity",
  period: "1y",
  quote: {
    price: 2500,
    previous_close: 2480,
    change: 20,
    change_percent: 0.8,
    open: 2490,
    high: 2510,
    low: 2485,
    volume: 1_000_000,
    as_of: "2026-10-27",
  },
  bars: [] as { time: string; open: number; high: number; low: number; close: number; volume: number }[],
  sma20: [] as { time: string; value: number }[],
  sma50: [] as { time: string; value: number }[],
}

export const mockPredict = {
  symbol: "RELIANCE.NS",
  ticker: "RELIANCE",
  name: "Reliance Industries",
  sector: "Energy",
  unit: "INR",
  kind: "equity",
  as_of: "2026-10-16",
  last_close: 2400,
  predicted_close: 2410,
  predicted_return: 2410 / 2400 - 1,
  direction: "up",
  signal: "BUY",
  confidence: 0.4707,
  confidence_source: "evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy",
  signal_threshold: 0.003,
  comparison: [] as { date: string; actual: number; predicted: number }[],
  model: "lightgbm",
}

export const mockGlobals = { series: [] as Quote[] }

export const mockPortfolio: Portfolio = {
  cash: 900_000,
  starting_cash: 1_000_000,
  realized_pnl: 0,
  unrealized_pnl: 10_000,
  market_value: 110_000,
  equity: 1_010_000,
  positions: [],
  equity_curve: [{ time: "2026-01-01", equity: 1_000_000, cash: 1_000_000 }],
}

export const mockOrders: { orders: Order[] } = { orders: [] }

export const mockUniverse = {
  names: [
    { symbol: "RELIANCE.NS", ticker: "RELIANCE", name: "Reliance Industries", sector: "Energy" },
    { symbol: "TCS.NS", ticker: "TCS", name: "Tata Consultancy Services", sector: "IT" },
  ],
}

export const mockConfig = {
  market_data_provider: "yahoo",
  market_data_label: "Yahoo Finance",
  research_portfolio_max_symbols: 10,
  backtest_default_fill: "close",
  model_card_url: "/MODEL_CARD.md",
}

const mockCurve = [
  { time: "2024-01-01", equity: 1_000_000 },
  { time: "2024-06-01", equity: 1_020_000 },
  { time: "2024-12-01", equity: 1_010_000 },
]

export const mockBacktest = {
  symbol: "RELIANCE.NS",
  ticker: "RELIANCE",
  name: "Reliance Industries",
  period: "2y",
  strategy: {
    starting_cash: 1_000_000,
    ending_equity: 1_010_000,
    total_return: 0.01,
    cagr: 0.005,
    max_drawdown: -0.02,
    sharpe: 0.4,
    hit_rate: 0.5,
    trade_count: 4,
    total_costs_inr: 1200,
    turnover_ratio: 0.1,
  },
  equity_curve: mockCurve,
  benchmark: {
    kind: "buy_and_hold",
    ending_equity: 1_020_000,
    total_return: 0.02,
    max_drawdown: -0.015,
    equity_curve: mockCurve.map((p) => ({ ...p, equity: p.equity + 10_000 })),
  },
  disclaimer: "Offline simulation with India delivery costs; not investment advice.",
}

export const mockPortfolioBacktest = {
  kind: "portfolio",
  symbols: ["RELIANCE.NS", "TCS.NS"],
  period: "2y",
  strategy: mockBacktest.strategy,
  equity_curve: mockCurve,
  benchmark: mockBacktest.benchmark,
  disclaimer: "Shared-cash multi-name simulation; not investment advice.",
}
