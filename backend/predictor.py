"""Load the returns LSTM and score one symbol or a batch."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from features import (
    COMPARE_POINTS,
    SIGNAL_THRESHOLD,
    WINDOW,
    build_inference_batch,
    price_from_log_return,
    scale_windows,
    signal_from_move,
)


class Predictor:
    def __init__(self, artifact_dir: Path):
        self.artifact_dir = Path(artifact_dir)
        self.model_path = self.artifact_dir / "model.keras"
        self.scaler_path = self.artifact_dir / "scaler.joblib"
        self.metrics_path = self.artifact_dir / "metrics.json"
        self.model = None
        self.scaler = None
        self.metrics: dict = {}
        self.ready = False
        self._summary_key: tuple | None = None
        self._summary_cache: dict[str, dict] = {}

    def load(self) -> None:
        self.ready = False
        if not self.model_path.exists() or not self.scaler_path.exists():
            return
        import joblib
        from tensorflow import keras

        self.model = keras.models.load_model(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        if self.metrics_path.exists():
            self.metrics = json.loads(self.metrics_path.read_text())
        self.ready = True

    def summary(self) -> dict | None:
        if not self.ready:
            return None
        return {
            "directional_accuracy": self.metrics.get("directional_accuracy"),
            "mae_log_return": self.metrics.get("mae_log_return"),
            "naive_mae_log_return": self.metrics.get("naive_mae_log_return"),
            "trained_at": self.metrics.get("trained_at"),
            "symbols": self.metrics.get("symbols"),
            "window": self.metrics.get("window", WINDOW),
            "signal_threshold": self.metrics.get("signal_threshold", SIGNAL_THRESHOLD),
        }

    def _confidence(self, symbol: str) -> float | None:
        per_symbol = self.metrics.get("per_symbol", {})
        entry = per_symbol.get(symbol)
        if entry and entry.get("directional_accuracy") is not None:
            return float(entry["directional_accuracy"])
        overall = self.metrics.get("directional_accuracy")
        return float(overall) if overall is not None else None

    def _predict_scaled(self, windows: np.ndarray) -> np.ndarray:
        scaled = scale_windows(windows, self.scaler)
        raw = self.model.predict(scaled, verbose=0)
        return self.scaler.inverse_transform(np.asarray(raw).reshape(-1, 1)).reshape(-1)

    def summaries(self, frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
        if not self.ready:
            return {}
        key_parts = []
        usable: list[tuple[str, pd.DataFrame]] = []
        for symbol, frame in frames.items():
            if frame is None or len(frame) < WINDOW + 1:
                continue
            last = frame.iloc[-1]
            key_parts.append((symbol, str(last["Date"]), float(last["Close"])))
            usable.append((symbol, frame))
        key = tuple(key_parts)
        if key == self._summary_key:
            return self._summary_cache
        if not usable:
            self._summary_key = key
            self._summary_cache = {}
            return {}

        windows = []
        meta = []
        for symbol, frame in usable:
            closes = frame["Close"].to_numpy(dtype=np.float64)
            batch, _align = build_inference_batch(closes, compare=1)
            windows.append(batch[-1])
            meta.append((symbol, float(closes[-1])))
        predicted = self._predict_scaled(np.stack(windows))
        result = {}
        for (symbol, last_close), log_return in zip(meta, predicted):
            move = float(np.exp(log_return) - 1.0)
            result[symbol] = {
                "predicted_close": price_from_log_return(last_close, float(log_return)),
                "predicted_return": move,
                "direction": "up" if log_return > 0 else "down" if log_return < 0 else "flat",
                "signal": signal_from_move(move),
                "confidence": self._confidence(symbol),
            }
        self._summary_key = key
        self._summary_cache = result
        return result

    def detail(self, symbol: str, frame: pd.DataFrame) -> dict | None:
        if not self.ready or frame is None or len(frame) < WINDOW + 1:
            return None
        closes = frame["Close"].to_numpy(dtype=np.float64)
        dates = [str(value) for value in frame["Date"].tolist()]
        windows, align = build_inference_batch(closes, compare=COMPARE_POINTS)
        predicted = self._predict_scaled(windows)
        history = predicted[:-1]
        next_log = float(predicted[-1])
        comparison = []
        for log_return, (base_i, actual_i) in zip(history, align):
            comparison.append(
                {
                    "date": dates[actual_i],
                    "actual": float(closes[actual_i]),
                    "predicted": price_from_log_return(float(closes[base_i]), float(log_return)),
                }
            )
        last_close = float(closes[-1])
        move = float(np.exp(next_log) - 1.0)
        return {
            "symbol": symbol,
            "as_of": dates[-1],
            "last_close": last_close,
            "predicted_close": price_from_log_return(last_close, next_log),
            "predicted_return": move,
            "direction": "up" if next_log > 0 else "down" if next_log < 0 else "flat",
            "signal": signal_from_move(move),
            "confidence": self._confidence(symbol),
            "signal_threshold": SIGNAL_THRESHOLD,
            "comparison": comparison,
            "model": self.summary(),
        }
