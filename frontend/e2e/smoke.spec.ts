import { test, expect } from "@playwright/test"
import { mockBacktest, mockConfig, mockGlobals, mockOrders, mockOverview, mockPortfolio, mockPortfolioBacktest, mockUniverse } from "./mocks"

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

test("header shows product name and disclaimer", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("link", { name: "Bharat Desk" })).toBeVisible()
  await expect(page.getByText(/Paper trading only/i)).toBeVisible()
})
