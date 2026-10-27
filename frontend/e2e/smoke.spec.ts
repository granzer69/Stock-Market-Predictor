import { test, expect } from "@playwright/test"
import { mockBacktest, mockConfig, mockGlobals, mockHistory, mockOrders, mockOverview, mockPortfolio, mockPortfolioBacktest, mockPredict, mockUniverse } from "./mocks"

async function mockApi(page: import("@playwright/test").Page) {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith("/api/market/overview")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockOverview) })
      return
    }
    if (path.endsWith("/api/market/globals")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockGlobals) })
      return
    }
    if (path.endsWith("/api/portfolio")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockPortfolio) })
      return
    }
    if (path.endsWith("/api/orders")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockOrders) })
      return
    }
    if (path.includes("/api/research/backtest/portfolio")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockPortfolioBacktest) })
      return
    }
    if (path.includes("/api/research/backtest/")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockBacktest) })
      return
    }
    if (path.endsWith("/api/config")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockConfig) })
      return
    }
    if (path.endsWith("/api/universe/nifty50")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockUniverse) })
      return
    }
    if (path.includes("/api/market/history/")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockHistory) })
      return
    }
    if (path.includes("/api/predict/")) {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(mockPredict) })
      return
    }
    await route.fulfill({ status: 404, body: "not mocked" })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test("home shows Nifty table from mocked overview", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Nifty 50" })).toBeVisible()
  await expect(page.getByRole("link", { name: "RELIANCE" })).toBeVisible()
  await expect(page.getByText(/Production:/i)).toBeVisible()
  await expect(page.getByRole("button", { name: "LSTM next" })).toHaveCount(0)
  await expect(page.getByRole("button", { name: "lightgbm next" })).toBeVisible()
  await expect(page.getByText(/lightgbm forecast bar 2026-10-16/)).toBeVisible()
  await expect(page.getByText(/Quote session 2026-10-27/)).toBeVisible()
})

test("symbol page names the lightgbm forecast bar", async ({ page }) => {
  await page.goto("/stock/RELIANCE")
  await expect(page.getByRole("heading", { name: "RELIANCE" })).toBeVisible()
  await expect(page.getByText("one-step LSTM close")).toHaveCount(0)
  await expect(page.getByText("LSTM next")).toHaveCount(0)
  await expect(page.getByRole("heading", { name: "Next-session lightgbm forecast" })).toBeVisible()
  await expect(page.getByText(/Forecast as of 2026-10-16/).first()).toBeVisible()
  await expect(page.getByText(/Close on 2026-10-27/)).toBeVisible()
})

test("portfolio page loads paper book", async ({ page }) => {
  await page.goto("/portfolio")
  await expect(page.getByRole("heading", { name: "Paper portfolio" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Equity" })).toBeVisible()
})

test("research page shows backtest metrics", async ({ page }) => {
  await page.goto("/research")
  await expect(page.getByRole("heading", { name: "Research backtest" })).toBeVisible()
  await expect(page.getByText("Strategy equity")).toBeVisible()
  await expect(page.getByRole("button", { name: "Export JSON" })).toBeVisible()
})

test("evaluation page loads its report from /api/evaluation", async ({ page }) => {
  await page.route("**/api/evaluation", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        champion_model: "arima_111",
        production_model: "lightgbm",
        methodology: {
          honest_note:
            "Metrics are in-sample walk-forward on Yahoo EOD data. They do NOT imply superiority over professional quant models.",
        },
        pooled_model_comparison: {
          momentum: { directional_accuracy: 1, mape_pct: null, rmse: null, n_symbols: 50 },
          lightgbm: { directional_accuracy: 0.4707, mape_pct: 1.4153, rmse: 47.4909, n_symbols: 50 },
          arima_111: { directional_accuracy: 0.5066, mape_pct: 11.8258, rmse: 332.2357, n_symbols: 50 },
          persistence: { directional_accuracy: 0, mape_pct: 1.225, rmse: 42.6031, n_symbols: 50 },
          gru_reliance_sample: { directional_accuracy: 0.5251, mape_pct: 1018.7255, rmse: 0.0531, n_samples: 221 },
        },
      }),
    })
  })
  const reportRequest = page.waitForRequest((request) => new URL(request.url()).pathname === "/api/evaluation")
  await page.goto("/evaluation")
  expect(new URL((await reportRequest).url()).pathname).toBe("/api/evaluation")
  await expect(page.getByRole("heading", { name: "Model evaluation" })).toBeVisible()
  await expect(page.getByText("Stored comparison from the evaluation report. The rows were not all produced by one split.")).toBeVisible()
  await expect(page.getByText("arima_111 is the stored directional-accuracy pick. The desk hint is lightgbm. This row's MAPE is 11.8258, much worse than persistence at 1.225.")).toBeVisible()
  await expect(page.getByText("Single-symbol sample, not a Nifty-wide champion.")).toBeVisible()
  await expect(page.getByText("Pre-fix same-return score: the sign of the return being graded. Not a lagged baseline and not a champion.")).toBeVisible()
  await expect(page.getByText("Walk-forward holdout")).toHaveCount(0)
  await expect(page.getByText("same split for all baselines")).toHaveCount(0)
  await expect(
    page.getByText(
      "File's original wording: Metrics are in-sample walk-forward on Yahoo EOD data. They do NOT imply superiority over professional quant models. The report records one chronological split, not a walk-forward.",
    ),
  ).toBeVisible()
  const visible = await page.locator("body").innerText()
  if (/walk-forward/i.test(visible)) {
    expect(visible).toContain("The report records one chronological split, not a walk-forward.")
  }
})

test("backtest page loads its report from /api/legacy/backtest", async ({ page }) => {
  await page.route("**/api/legacy/backtest**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        symbol: "RELIANCE",
        paper_trading_only: true,
        metrics: {
          cagr: -0.1164,
          buy_hold_cagr: 0.01,
          sharpe: -0.65,
          buy_hold_sharpe: 0.2,
          max_drawdown: -0.2,
          win_rate: 0.4,
        },
      }),
    })
  })
  const reportRequest = page.waitForRequest((request) => new URL(request.url()).pathname === "/api/legacy/backtest")
  await page.goto("/backtest")
  expect(new URL((await reportRequest).url()).pathname).toBe("/api/legacy/backtest")
  await expect(page.getByRole("heading", { name: "Paper backtest" })).toBeVisible()
})

test("header shows product name and disclaimer", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("link", { name: "Bharat Desk" })).toBeVisible()
  await expect(page.getByText(/Paper trading only/i)).toBeVisible()
})
