import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from features import build_inference_batch, log_returns, scale_windows
from market_data import PriceCache, frames_from_download


def _frame(symbol_prices):
    rows = []
    for index, price in enumerate(symbol_prices, start=1):
        rows.append(
            {
                "Date": f"2024-01-{index:02d}",
                "Open": price - 1,
                "High": price + 1,
                "Low": price - 2,
                "Close": price,
                "Volume": 1000 + index,
            }
        )
    return pd.DataFrame(rows)


def test_disk_cache_hit(tmp_path):
    calls = {"n": 0}

    def fetcher(symbols, period):
        calls["n"] += 1
        return {symbols[0]: _frame([100, 101, 102, 103])}

    first = PriceCache(tmp_path, history_ttl=1000, quote_ttl=1000, fetcher=fetcher, now=lambda: 1000)
    first.get_history("RELIANCE.NS", "1y")
    second = PriceCache(tmp_path, history_ttl=1000, quote_ttl=1000, fetcher=fetcher, now=lambda: 1100)
    frame = second.get_history("RELIANCE.NS", "1y")

    assert calls["n"] == 1
    assert frame is not None
    assert list(frame["Close"]) == [100, 101, 102, 103]


def test_quote_cache_hit(tmp_path):
    calls = {"n": 0}

    def fetcher(symbols, period):
        calls["n"] += 1
        assert period == "5d"
        return {symbol: _frame([10, 12]) for symbol in symbols}

    cache = PriceCache(tmp_path, fetcher=fetcher, now=lambda: 50)
    first = cache.get_quotes(["TCS.NS", "INFY.NS"])
    second = cache.get_quotes(["TCS.NS", "INFY.NS"])

    assert calls["n"] == 1
    assert first["TCS.NS"]["price"] == 12
    assert second["INFY.NS"]["change"] == 2


def test_frames_from_multiindex_download():
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "RELIANCE.NS"),
            ("High", "RELIANCE.NS"),
            ("Low", "RELIANCE.NS"),
            ("Close", "RELIANCE.NS"),
            ("Volume", "RELIANCE.NS"),
        ],
        names=["Price", "Ticker"],
    )
    raw = pd.DataFrame(
        [[10, 12, 9, 11, 100], [11, 13, 10, 12, 110]],
        index=index,
        columns=columns,
    )
    frames = frames_from_download(raw, ["RELIANCE.NS", "MISSING.NS"])
    assert list(frames) == ["RELIANCE.NS"]
    assert frames["RELIANCE.NS"]["Close"].tolist() == [11, 12]


def test_prediction_window_shape():
    closes = np.linspace(100, 180, 90)
    windows, align = build_inference_batch(closes, window=60, compare=10)
    assert windows.shape == (11, 60)
    assert len(align) == 10
    np.testing.assert_allclose(windows[-1], log_returns(closes)[-60:])

    scaler = StandardScaler()
    scaler.fit(log_returns(closes).reshape(-1, 1))
    model_input = scale_windows(windows[-1], scaler)
    assert model_input.shape == (1, 60, 1)
