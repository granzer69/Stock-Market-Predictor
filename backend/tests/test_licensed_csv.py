"""Licensed NSE CSV provider."""

from pathlib import Path

import pandas as pd

from data_providers import LicensedIndiaDailyProvider


def _write_csv(path: Path, rows: int = 90):
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    frame = pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": 100.0,
            "High": 101.0,
            "Low": 99.0,
            "Close": 100.0 + (pd.Series(range(rows)) * 0.1),
            "Volume": 1_000,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_licensed_provider_loads_symbol_file(tmp_path):
    _write_csv(tmp_path / "RELIANCE.NS.csv")
    provider = LicensedIndiaDailyProvider(tmp_path)
    frames = provider.fetch(["RELIANCE.NS"], "1y")
    assert "RELIANCE.NS" in frames
    assert len(frames["RELIANCE.NS"]) <= 252


def test_missing_directory_raises(tmp_path):
    provider = LicensedIndiaDailyProvider(tmp_path / "missing")
    try:
        provider.fetch(["RELIANCE.NS"], "1y")
        assert False
    except FileNotFoundError as err:
        assert "NSE CSV" in str(err)
