#!/usr/bin/env python3
"""Train pooled LSTM on Nifty 50 per-symbol scaled windows."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "backend" / "data" / "nifty50_closes.csv"
MODEL_DIR = ROOT / "backend" / "models"
MODEL_PATH = MODEL_DIR / "nifty_lstm.keras"
SCALERS_PATH = MODEL_DIR / "scalers.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"

WINDOW = 60
TRAIN_RATIO = 0.8
EPOCHS = 15
BATCH_SIZE = 32
SEED = 42


def set_seeds() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    import tensorflow as tf

    tf.random.set_seed(SEED)


def build_model() -> Sequential:
    model = Sequential(
        [
            LSTM(50, return_sequences=True, input_shape=(WINDOW, 1)),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(1),
        ]
    )
    model.compile(optimizer=Adam(), loss="mse")
    return model


def make_windows(scaled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x, y = [], []
    for i in range(WINDOW, len(scaled)):
        x.append(scaled[i - WINDOW : i, 0])
        y.append(scaled[i, 0])
    return np.array(x), np.array(y)


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    mask = actual != 0
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100)


def train_symbol(
    symbol: str, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, MinMaxScaler, dict]:
    split = int(len(closes) * TRAIN_RATIO)
    train_closes = closes[:split]
    test_closes = closes[split:]

    scaler = MinMaxScaler(feature_range=(0, 1))
    train_scaled = scaler.fit_transform(train_closes.reshape(-1, 1))
    test_scaled = scaler.transform(test_closes.reshape(-1, 1))

    bridge = np.vstack([train_scaled[-WINDOW:], test_scaled])
    x_all, y_all = make_windows(bridge)
    test_len = len(test_closes)
    x_test = x_all[-test_len:]
    y_test = y_all[-test_len:]

    train_only = train_scaled.flatten()
    x_train, y_train = make_windows(train_only.reshape(-1, 1))

    x_train = x_train.reshape((x_train.shape[0], x_train.shape[1], 1))
    x_test = x_test.reshape((x_test.shape[0], x_test.shape[1], 1))

    return x_train, y_train, x_test, y_test, scaler, {"train_rows": split, "test_rows": test_len}


def main() -> None:
    set_seeds()
    if not DATA_CSV.exists():
        raise SystemExit(f"Missing {DATA_CSV}. Run scripts/fetch_nifty.py first.")

    df = pd.read_csv(DATA_CSV)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    x_train_all: list[np.ndarray] = []
    y_train_all: list[np.ndarray] = []
    x_test_all: list[np.ndarray] = []
    y_test_all: list[np.ndarray] = []
    scalers: dict[str, MinMaxScaler] = {}
    per_symbol_meta: dict[str, dict] = {}

    for symbol, group in df.groupby("Symbol"):
        group = group.sort_values("Date")
        closes = group["Close"].astype(float).values
        if len(closes) < WINDOW + 10:
            continue

        x_tr, y_tr, x_te, y_te, scaler, meta = train_symbol(symbol, closes)
        x_train_all.append(x_tr)
        y_train_all.append(y_tr)
        x_test_all.append(x_te)
        y_test_all.append(y_te)
        scalers[symbol] = scaler
        per_symbol_meta[symbol] = meta

    if not x_train_all:
        raise SystemExit("No training data produced.")

    x_train = np.concatenate(x_train_all, axis=0)
    y_train = np.concatenate(y_train_all, axis=0)
    x_test = np.concatenate(x_test_all, axis=0)
    y_test = np.concatenate(y_test_all, axis=0)

    model = build_model()
    model.fit(x_train, y_train, batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=1)

    pred_scaled = model.predict(x_test, verbose=0).flatten()
    # Map each test row back to its symbol for inverse transform
    per_symbol_metrics: dict[str, dict] = {}
    offset = 0
    pooled_actual: list[float] = []
    pooled_pred: list[float] = []

    for symbol in scalers:
        n = per_symbol_meta[symbol]["test_rows"]
        sym_pred_scaled = pred_scaled[offset : offset + n]
        sym_y_scaled = y_test[offset : offset + n]
        offset += n

        scaler = scalers[symbol]
        actual = scaler.inverse_transform(sym_y_scaled.reshape(-1, 1)).flatten()
        pred = scaler.inverse_transform(sym_pred_scaled.reshape(-1, 1)).flatten()

        sym_mape = mape(actual, pred)
        confidence = max(0.0, min(0.99, 1.0 - sym_mape / 100.0))
        per_symbol_metrics[symbol] = {
            "mape_pct": round(sym_mape, 4),
            "confidence": round(confidence, 4),
            **per_symbol_meta[symbol],
        }
        pooled_actual.extend(actual.tolist())
        pooled_pred.extend(pred.tolist())

    pooled_mape = mape(np.array(pooled_actual), np.array(pooled_pred))
    print(f"Pooled test MAPE: {pooled_mape:.4f}%")

    model.save(MODEL_PATH)
    joblib.dump(scalers, SCALERS_PATH)

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW,
        "epochs": EPOCHS,
        "pooled_test_mape_pct": round(float(pooled_mape), 4),
        "symbols": per_symbol_metrics,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(f"Saved model → {MODEL_PATH}")
    print(f"Saved scalers → {SCALERS_PATH}")
    print(f"Saved metrics → {METRICS_PATH}")


if __name__ == "__main__":
    main()
