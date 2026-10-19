# Corporate actions policy

Bharat Desk does **not** automatically adjust historical prices for splits, bonuses, or demergers.

## Current behavior

- Yahoo `auto_adjust=False` in [`market_data.py`](backend/market_data.py) downloads.
- CSV loader uses vendor-supplied closes as-is.
- LSTM trains on log returns with clip ±0.2; large unadjusted jumps may be clipped but not removed.

## Recommended practice

1. Prefer **adjusted close** from a licensed vendor when building `NSE_CSV_DIR` files.
2. Document adjustment version in CSV README per symbol batch.
3. Retrain after major index constituent changes ([UNIVERSE_MAINTENANCE.md](UNIVERSE_MAINTENANCE.md)).

## Out of scope

Dividend reinvestment modeling, rights issues, and F&O corporate action schedules.
