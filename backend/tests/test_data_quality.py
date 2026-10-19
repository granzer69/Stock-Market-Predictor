import pandas as pd

from data_quality import validate_ohlcv_frame


def test_validate_ok_frame():
    frame = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Close": [100.0, 101.0],
        }
    )
    assert validate_ohlcv_frame(frame, "TEST") == []


def test_validate_rejects_empty():
    assert "empty" in validate_ohlcv_frame(pd.DataFrame(), "X")[0]
