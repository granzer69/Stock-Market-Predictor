"""Train a next-day log-return LSTM on Nifty 50 daily closes.

Run from the repo root:

    python backend/train_lstm.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

from features import SIGNAL_THRESHOLD, WINDOW, log_returns
from market_data import yfinance_fetcher
from universe import NIFTY_50

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def build_samples(frames: dict, window: int = WINDOW, holdout: float = 0.2):
    train_x = []
    train_y = []
    held = {}
    for symbol, frame in frames.items():
        closes = frame["Close"].to_numpy(dtype=np.float64)
        if np.any(closes <= 0) or len(closes) < window + 80:
            continue
        returns = log_returns(closes)
        xs = []
        ys = []
        for index in range(window, len(returns)):
            xs.append(returns[index - window : index])
            ys.append(returns[index])
        xs = np.asarray(xs, dtype=np.float64)
        ys = np.asarray(ys, dtype=np.float64)
        cut = int(len(xs) * (1.0 - holdout))
        if cut < 40 or cut >= len(xs):
            continue
        train_x.append(xs[:cut])
        train_y.append(ys[:cut])
        held[symbol] = (xs[cut:], ys[cut:])
    if not train_x:
        raise RuntimeError("No symbol had enough history to train")
    return np.concatenate(train_x), np.concatenate(train_y), held


def directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = (actual != 0) & (predicted != 0)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.sign(actual[mask]) == np.sign(predicted[mask])))


def train_and_save(frames: dict, artifact_dir: str | os.PathLike | None = None) -> dict:
    """Train on pre-fetched frames and write keras/scaler/metrics. Returns metrics dict."""
    import tensorflow as tf
    from tensorflow import keras

    tf.random.set_seed(7)
    np.random.seed(7)

    x_train, y_train, held = build_samples(frames)
    print(f"Training rows: {len(x_train)} across {len(held)} symbols")

    scaler = StandardScaler()
    scaler.fit(x_train.reshape(-1, 1))
    x_scaled = scaler.transform(x_train.reshape(-1, 1)).reshape(len(x_train), WINDOW, 1).astype(np.float32)
    y_scaled = scaler.transform(y_train.reshape(-1, 1)).astype(np.float32)

    model = keras.Sequential(
        [
            keras.Input(shape=(WINDOW, 1)),
            keras.layers.LSTM(32, return_sequences=True),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(16),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(8, activation="relu"),
            keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    epochs = int(os.environ.get("LSTM_EPOCHS", "8"))
    # Keep time order: last 10% of pooled rows is validation; no shuffle.
    model.fit(
        x_scaled,
        y_scaled,
        epochs=epochs,
        batch_size=512,
        validation_split=0.1,
        shuffle=False,
        verbose=2,
        callbacks=[
            keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=2,
                restore_best_weights=True,
            )
        ],
    )

    per_symbol = {}
    holdout_actual = []
    holdout_pred = []
    for symbol, (x_hold, y_hold) in held.items():
        scaled = scaler.transform(x_hold.reshape(-1, 1)).reshape(len(x_hold), WINDOW, 1).astype(np.float32)
        pred = scaler.inverse_transform(model.predict(scaled, verbose=0)).reshape(-1)
        holdout_actual.append(y_hold)
        holdout_pred.append(pred)
        per_symbol[symbol] = {
            "directional_accuracy": directional_accuracy(y_hold, pred),
            "mae_log_return": float(np.mean(np.abs(y_hold - pred))),
            "n": int(len(y_hold)),
        }

    actual = np.concatenate(holdout_actual)
    predicted = np.concatenate(holdout_pred)
    metrics = {
        "window": WINDOW,
        "holdout_fraction": 0.2,
        "training_shuffle": False,
        "fit_validation_split": 0.1,
        "mae_log_return": float(np.mean(np.abs(actual - predicted))),
        "naive_mae_log_return": float(np.mean(np.abs(actual))),
        "directional_accuracy": directional_accuracy(actual, predicted),
        "signal_threshold": SIGNAL_THRESHOLD,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "symbols": len(held),
        "train_rows": int(len(x_train)),
        "per_symbol": per_symbol,
    }

    out_dir = artifact_dir or os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    model.save(os.path.join(out_dir, "model.keras"))
    joblib.dump(scaler, os.path.join(out_dir, "scaler.joblib"))
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    return metrics


def main() -> None:
    symbols = [item.symbol for item in NIFTY_50]
    print(f"Downloading 5y daily bars for {len(symbols)} symbols...")
    frames = yfinance_fetcher(symbols, "5y")
    print(f"Received history for {len(frames)} symbols")
    metrics = train_and_save(frames)
    print(
        "Saved model. Holdout directional accuracy "
        f"{metrics['directional_accuracy']:.3f}, MAE {metrics['mae_log_return']:.5f} "
        f"vs naive {metrics['naive_mae_log_return']:.5f}"
    )


if __name__ == "__main__":
    main()
