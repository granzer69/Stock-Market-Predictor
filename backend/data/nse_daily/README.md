# NSE daily CSV bundle

Point `NSE_CSV_DIR` here (or set `MARKET_DATA_PROVIDER=nse_csv`) to serve history from licensed/vendor files instead of Yahoo.

## File naming

- `SYMBOL.NS.csv` (preferred), e.g. `RELIANCE.NS.csv`
- or `SYMBOL.csv` for the bare ticker

## Columns

`Date`, `Open`, `High`, `Low`, `Close`, `Volume` (header case-insensitive).

Dates are `YYYY-MM-DD`. The loader normalizes rows the same way as `market_data._normalize_ohlcv`.

## Sample

`RELIANCE.NS.csv` in this folder is **synthetic** for tests and local demos only—not exchange data.
