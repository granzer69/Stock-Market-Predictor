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


class ForecastUnavailable(Exception):
    """The champion stack is up, and this symbol has no forecast from it."""


class ChampionStackUnavailable(Exception):
    """The champion booster cannot run. Callers should use the LSTM."""


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

    def _champion_ready(self) -> bool:
        try:
            return bool(self._inference().champion_available())
        except Exception:  # noqa: BLE001
            return False

    def _label_lstm(self, payload: dict | None) -> dict | None:
        if payload is None:
            return None
        labeled = dict(payload)
        labeled["model"] = "lstm"
        return labeled

    def _lstm_summaries(self, frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
        raw = self.lstm.summaries(frames)
        return {symbol: {**row, "model": "lstm"} for symbol, row in raw.items()}

    def _champion_payload(self, symbol: str, _live_close: float) -> dict:
        """Forecast fields come from predict_symbol. The live quote close is not copied onto them.

        A per-symbol failure raises ForecastUnavailable. It is not labeled lstm.
        A failure to run the booster raises ChampionStackUnavailable.
        """
        inf = self._inference()
        try:
            out = inf.predict_symbol(symbol)
        except (ImportError, ModuleNotFoundError, OSError) as exc:
            raise ChampionStackUnavailable(str(exc)) from exc
        except ForecastUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 — this name has no champion row
            raise ForecastUnavailable(symbol) from exc
        move = float(out["predicted_return"])
        q = out.get("quantiles", {})
        confidence = out.get("confidence")
        return {
            "predicted_close": float(out["predicted_price"]),
            "predicted_return": move,
            "direction": out.get("direction", "flat"),
            "signal": signal_from_move(move),
            "confidence": None if confidence is None else float(confidence),
            "confidence_source": out.get("confidence_source"),
            "interval_p10": (q.get("0.1") or {}).get("price"),
            "interval_p90": (q.get("0.9") or {}).get("price"),
            "as_of": out.get("as_of"),
            "last_close": out.get("last_close"),
            "model": out.get("model") or "lightgbm",
        }

    def summaries(self, frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
        # Stack cannot run: one LSTM batch, each row labeled lstm.
        # Stack is up: a symbol with no champion row stays out of this dict. It is not labeled lstm.
        if not self._champion_ready():
            return self._lstm_summaries(frames)
        out: dict[str, dict] = {}
        for symbol, frame in frames.items():
            if frame is None or frame.empty:
                continue
            try:
                payload = self._champion_payload(symbol, float(frame.iloc[-1]["Close"]))
            except ForecastUnavailable:
                continue
            except ChampionStackUnavailable:
                if out:
                    continue
                return self._lstm_summaries(frames)
            out[symbol] = payload
        return out

    def _predict_scaled(self, windows):
        """Backtest path uses pooled LSTM windows (LightGBM is point-in-time only)."""
        return self.lstm._predict_scaled(windows)

    def detail(self, symbol: str, frame: pd.DataFrame) -> dict | None:
        if not self._champion_ready():
            return self._label_lstm(self.lstm.detail(symbol, frame))
        if frame is None or frame.empty:
            return None
        try:
            payload = self._champion_payload(symbol, float(frame.iloc[-1]["Close"]))
        except ForecastUnavailable:
            raise
        except ChampionStackUnavailable:
            return self._label_lstm(self.lstm.detail(symbol, frame))
        return {
            "symbol": symbol,
            "as_of": payload["as_of"],
            "last_close": payload["last_close"],
            "predicted_close": payload["predicted_close"],
            "predicted_return": payload["predicted_return"],
            "direction": payload["direction"],
            "signal": payload["signal"],
            "confidence": payload["confidence"],
            "confidence_source": payload.get("confidence_source"),
            "signal_threshold": SIGNAL_THRESHOLD,
            "comparison": [],
            "model": payload["model"],
        }
