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
  as_of: "2026-01-15T00:00:00Z",
  prediction: {
    predicted_close: 2510,
    predicted_return: 0.004,
    direction: "up",
    signal: "BUY",
    confidence: 0.487,
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
  },
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

export const mockConfig = {
  market_data_provider: "yahoo",
  market_data_label: "Yahoo Finance",
  research_portfolio_max_symbols: 10,
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
