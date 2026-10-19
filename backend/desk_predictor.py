"""Bharat Desk predictor: LightGBM champion when available, else LSTM artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features import SIGNAL_THRESHOLD, signal_from_move  # noqa: E402
from predictor import Predictor  # noqa: E402

EVAL_REPORT = Path(__file__).resolve().parent / "models" / "evaluation_report.json"


class DeskPredictor:
    def __init__(self, lstm: Predictor):
        self.lstm = lstm
        self._inf = None

    def _inference(self):
        if self._inf is None:
            import importlib

            try:
                self._inf = importlib.import_module("inference")
            except ModuleNotFoundError:
                self._inf = importlib.import_module("backend.inference")
        return self._inf

    @property
    def ready(self) -> bool:
        try:
            if self._inference().champion_available():
                return True
        except Exception:  # noqa: BLE001
            pass
        return self.lstm.ready

    def _evaluation(self) -> dict:
        if not EVAL_REPORT.exists():
            return {}
        return json.loads(EVAL_REPORT.read_text())

    def summary(self) -> dict | None:
        ev = self._evaluation()
        pooled = ev.get("pooled_model_comparison", {})
        prod = pooled.get("lightgbm", {})
        naive = pooled.get("persistence", {})
        lstm_metrics = self.lstm.summary()

        return {
            "directional_accuracy": prod.get("directional_accuracy")
            or (lstm_metrics or {}).get("directional_accuracy"),
            "mae_log_return": (lstm_metrics or {}).get("mae_log_return"),
            "naive_mae_log_return": (lstm_metrics or {}).get("naive_mae_log_return"),
            "trained_at": ev.get("generated_at") or (lstm_metrics or {}).get("trained_at"),
            "symbols": prod.get("n_symbols") or (lstm_metrics or {}).get("symbols"),
            "window": (lstm_metrics or {}).get("window", 60),
            "signal_threshold": SIGNAL_THRESHOLD,
            "production_model": ev.get("production_model", "lightgbm"),
            "champion_model": ev.get("champion_model"),
            "champion_directional_accuracy": ev.get("champion_directional_accuracy"),
            "baselines": {
                "persistence_mape_pct": naive.get("mape_pct"),
                "lightgbm_mape_pct": prod.get("mape_pct"),
                "lightgbm_directional_accuracy": prod.get("directional_accuracy"),
                "arima_directional_accuracy": pooled.get("arima_111", {}).get("directional_accuracy"),
                "ma20_directional_accuracy": pooled.get("ma20", {}).get("directional_accuracy"),
                "legacy_lstm_mape_pct": ev.get("pooled_model_comparison", {})
                .get("legacy_lstm_trained", {})
                .get("pooled_test_mape_pct"),
            },
            "honest_note": ev.get("methodology", {}).get("honest_note"),
        }

    def _champion_payload(self, symbol: str, last_close: float) -> dict | None:
        try:
            inf = self._inference()
            if not inf.champion_available():
                return None
            out = inf.predict_symbol(symbol)
        except Exception:  # noqa: BLE001
            return None
        move = float(out["predicted_return"])
        q = out.get("quantiles", {})
        return {
            "predicted_close": float(out["predicted_price"]),
            "predicted_return": move,
            "direction": out.get("direction", "flat"),
            "signal": signal_from_move(move),
            "confidence": float(out.get("confidence", 0.5)),
            "interval_p10": (q.get("0.1") or {}).get("price"),
            "interval_p90": (q.get("0.9") or {}).get("price"),
            "model": out.get("model", "lightgbm"),
        }

    def summaries(self, frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
        if self._inference().champion_available():
            out: dict[str, dict] = {}
            for symbol, frame in frames.items():
                if frame is None or frame.empty:
                    continue
                last_close = float(frame.iloc[-1]["Close"])
                payload = self._champion_payload(symbol, last_close)
                if payload:
                    out[symbol] = payload
            if out:
                return out
        return self.lstm.summaries(frames)

    def _predict_scaled(self, windows):
        """Backtest path uses pooled LSTM windows (LightGBM is point-in-time only)."""
        return self.lstm._predict_scaled(windows)

    def detail(self, symbol: str, frame: pd.DataFrame) -> dict | None:
        payload = None
        if frame is not None and not frame.empty:
            payload = self._champion_payload(symbol, float(frame.iloc[-1]["Close"]))
        if payload:
            dates = [str(v) for v in frame["Date"].tolist()]
            return {
                "symbol": symbol,
                "as_of": dates[-1],
                "last_close": float(frame.iloc[-1]["Close"]),
                "predicted_close": payload["predicted_close"],
                "predicted_return": payload["predicted_return"],
                "direction": payload["direction"],
                "signal": payload["signal"],
                "confidence": payload["confidence"],
                "signal_threshold": SIGNAL_THRESHOLD,
                "comparison": [],
                "model": self.summary(),
            }
        return self.lstm.detail(symbol, frame)
