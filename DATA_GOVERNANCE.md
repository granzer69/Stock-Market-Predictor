# Data governance

## Providers

| Mode | Env | Use |
|------|-----|-----|
| Yahoo (default) | `MARKET_DATA_PROVIDER=yahoo` | Development and demos |
| NSE CSV bundle | `MARKET_DATA_PROVIDER=nse_csv`, `NSE_CSV_DIR` | Licensed or curated daily files |

`MARKET_DATA_FAILOVER=true` (default) fills missing symbols from the alternate provider when possible.

## Quality checks

Run before training:

```bash
python backend/scripts/validate_market_data.py --symbol RELIANCE.NS --period 2y
```

Implementation: [`backend/data_quality.py`](backend/data_quality.py).

## Corporate actions

See [CORPORATE_ACTIONS.md](CORPORATE_ACTIONS.md). Training and backtests use **unadjusted** Yahoo/CSV closes unless you preprocess files.

## Universe

See [UNIVERSE_MAINTENANCE.md](UNIVERSE_MAINTENANCE.md) when Nifty 50 constituents change.
