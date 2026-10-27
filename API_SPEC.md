# API specification — Bharat Desk

**Source of truth:** [backend/main.py](backend/main.py).  
**Machine-readable schema:** [openapi.json](openapi.json) (regenerated in CI via `backend/scripts/export_openapi.py`).  
**Base URL (dev):** `http://localhost:8000` or same-origin `http://localhost:3000/api` via Next.js rewrite.

All successful JSON responses use `application/json`. Errors use FastAPI `{"detail": ...}`.

---

## `GET /api/health`

**Response 200**

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Always `true` when handler runs |
| `model` | boolean | `predictor.ready` (artifacts loaded) |

---

## `GET /api/market/overview`

Nifty 50 listings with latest quote and batch LSTM summary per symbol.

**Response 200**

| Field | Type | Description |
|-------|------|-------------|
| `stocks` | array | One object per symbol with data available |
| `model` | object \| null | `predictor.summary()` or null if model not ready |

**Stock object** (merge of `Series.as_dict()`, quote fields, optional `prediction`):

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | string | e.g. `RELIANCE.NS` |
| `ticker` | string | e.g. `RELIANCE` |
| `name` | string | Display name |
| `sector` | string | |
| `unit` | string | `INR` for equities |
| `kind` | string | `equity` |
| `price` | number | Last close from quote |
| `previous_close` | number | |
| `change` | number | |
| `change_percent` | number | |
| `open` | number | |
| `high` | number | |
| `low` | number | |
| `volume` | number | |
| `as_of` | string | Quote date |
| `prediction` | object | See prediction summary below |

**Prediction summary**

| Field | Type |
|-------|------|
| `predicted_close` | number |
| `predicted_return` | number | Fractional move (not percent) |
| `direction` | string | `up` \| `down` \| `flat` |
| `signal` | string | `BUY` \| `HOLD` \| `SELL` |
| `confidence` | number \| null | When present on a LightGBM hint, the evaluation report's pooled directional accuracy across per-symbol LightGBM fits. Not the saved booster's own holdout and not a per-name rate |
| `confidence_source` | string \| null | Where `confidence` was copied from. LightGBM desk hints use `evaluation_report.pooled_model_comparison.lightgbm.directional_accuracy` |
| `model` | string | Id of the model that produced the hint (`lightgbm` when the champion booster ran, `lstm` when that stack cannot run) |
| `as_of` | string | Date of the bar the forecast was scored on. Not the live quote date |
| `last_close` | number | Close of that forecast bar. Not the live quote |

**Model summary object** (when present)

| Field | Type |
|-------|------|
| `directional_accuracy` | number \| null |
| `mae_log_return` | number \| null |
| `naive_mae_log_return` | number \| null |
| `trained_at` | string \| null | ISO timestamp |
| `symbols` | number \| null |
| `window` | number |
| `signal_threshold` | number |

Symbols without quotes are omitted from `stocks`.

---

## `GET /api/market/globals`

Macro and index tape (see [backend/universe.py](backend/universe.py) `GLOBALS`).

**Response 200**

| Field | Type |
|-------|------|
| `series` | array | Same shape as overview stock objects without `prediction` |

---

## `GET /api/market/history/{symbol}`

**Query parameters**

| Name | Default | Allowed |
|------|---------|---------|
| `period` | `2y` | `6mo`, `1y`, `2y`, `5y` |

**Path:** `symbol` — Nifty ticker (`RELIANCE`) or full symbol (`RELIANCE.NS`).

**Response 200**

| Field | Type |
|-------|------|
| `symbol`, `ticker`, `name`, `sector`, `unit`, `kind` | metadata |
| `period` | string |
| `quote` | object | `price`, `previous_close`, `change`, `change_percent`, `open`, `high`, `low`, `volume`, `as_of` |
| `bars` | array | `{ time, open, high, low, close, volume }` |
| `sma20` | array | `{ time, value }` |
| `sma50` | array | `{ time, value }` |

**Errors:** `400` invalid period; `404` unknown symbol or no history.

---

## `GET /api/universe/nifty50`

Static Nifty 50 listing (no quotes).

**Response 200:** `{ "names": [ { "symbol", "ticker", "name", "sector" }, ... ] }` (50 rows).

---

## `GET /api/config`

Public runtime flags (no secrets).

**Response 200:** `market_data_provider` (`yahoo` | `nse_csv`), `market_data_label`, `research_portfolio_max_symbols`.

Set `MARKET_DATA_PROVIDER` / `NSE_CSV_DIR` on the API host (see `.env.example`).

---

## `GET /api/research/backtest/{symbol}`

Offline long-only backtest of LSTM signals on cached daily history (India delivery costs). Does not mutate the paper book.

**Query:** `period` — same set as history (`6mo`, `1y`, `2y`, `5y`); default `2y`.

**Response 200**

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | NSE symbol |
| `ticker` | string | Short ticker |
| `name` | string | Company name |
| `period` | string | History window used |
| `strategy` | object | `ending_equity`, `total_return`, `cagr`, `max_drawdown`, `sharpe`, `hit_rate`, `trade_count`, `total_costs_inr`, … |
| `equity_curve` | array | `{ time, equity }[]` (downsampled) |
| `benchmark` | object | `kind` = `buy_and_hold`, `ending_equity`, `total_return`, `max_drawdown`, `equity_curve` |
| `disclaimer` | string | Research-only notice |

**Errors:** `400` (bad period / short history), `404` (unknown symbol / no data), `503` (model not loaded).

---

## `GET /api/research/backtest/portfolio`

Shared-cash backtest across multiple Nifty 50 names (max 10).

**Query:** `period` (default `2y`), `symbols` comma-separated tickers (default `RELIANCE,TCS,HDFCBANK,INFY,ITC`).

**Response 200:** `kind` = `portfolio`, `symbols`, `strategy`, `equity_curve`, `benchmark` (`equal_weight_buy_hold`), `disclaimer`.

---

## `GET /api/predict/{symbol}`

Nifty 50 **equity** only.

**Response 200:** Equity metadata plus:

| Field | Type |
|-------|------|
| `as_of` | string | Forecast bar date from `predict_symbol` when the LightGBM booster ran. Live quote date on the LSTM artifact path |
| `last_close` | number | Close of that forecast bar. Not overwritten with the live quote when the booster ran |
| `predicted_close` | number |
| `predicted_return` | number |
| `direction` | string |
| `signal` | string |
| `confidence` | number \| null | Evaluation report's pooled directional accuracy across per-symbol LightGBM fits, when the champion booster ran. Not that booster's own holdout |
| `confidence_source` | string \| null | Names the report field above when `confidence` is that pooled figure |
| `signal_threshold` | number |
| `comparison` | array | `{ date, actual, predicted }`. Empty when the hint is the panel booster |
| `model` | string | `lightgbm` when the booster ran. `lstm` when that stack cannot run. A name with no panel forecast is a 404, not an LSTM label |

**Errors:** `404` unknown or non-equity, or `No champion forecast for this symbol` when the booster is up and this name has no panel forecast; `503` model not trained; `400` insufficient history on the LSTM path.

---

## `GET /api/portfolio`

**Response 200**

| Field | Type |
|-------|------|
| `cash` | number |
| `starting_cash` | number | `1000000` |
| `realized_pnl` | number |
| `unrealized_pnl` | number |
| `market_value` | number |
| `equity` | number |
| `positions` | array | See below |
| `equity_curve` | array | `{ time, equity, cash }` |

**Position** (after enrichment)

| Field | Type |
|-------|------|
| `symbol` | string |
| `ticker` | string |
| `name` | string |
| `qty` | integer |
| `avg_cost` | number |
| `last` | number |
| `market_value` | number |
| `unrealized_pnl` | number |
| `stale` | boolean | `true` if no live quote for mark |

---

## `GET /api/orders`

**Response 200**

| Field | Type |
|-------|------|
| `orders` | array | Newest first, max 100 |

**Order object**

| Field | Type |
|-------|------|
| `id` | integer |
| `symbol` | string |
| `ticker` | string |
| `name` | string |
| `side` | string | `BUY` \| `SELL` |
| `qty` | integer |
| `price` | number |
| `notional` | number |
| `created_at` | string | ISO UTC |

---

## `POST /api/orders`

**Request body (JSON)**

| Field | Type | Required |
|-------|------|----------|
| `symbol` | string | Yes — ticker or `.NS` symbol |
| `side` | string | Yes — `BUY` or `SELL` |
| `qty` | integer | Yes — positive whole shares |

**Response 200:** Order object (enriched).

**Errors**

| Status | Condition |
|--------|-----------|
| `400` | Not Nifty 50 equity, validation error, insufficient cash/shares |
| `503` | No quote for symbol |

Fill price is the latest cached quote `price` (last close), not a live exchange order.
