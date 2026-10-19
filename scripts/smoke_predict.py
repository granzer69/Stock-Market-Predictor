#!/usr/bin/env python3
"""Print one RELIANCE prediction when trained artifacts are present."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MODEL_PATH = BACKEND / "models" / "nifty_lstm.keras"
SCALERS_PATH = BACKEND / "models" / "scalers.joblib"
METRICS_PATH = BACKEND / "models" / "metrics.json"
DATA_CSV = BACKEND / "data" / "nifty50_closes.csv"
SYMBOL = "RELIANCE.NS"
WINDOW = 60


def main() -> int:
    required = [MODEL_PATH, SCALERS_PATH, METRICS_PATH, DATA_CSV]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("Artifacts missing (run fetch_nifty.py and train.py):")
        for p in missing:
            print(f"  - {p.relative_to(ROOT)}")
        return 1

    model = load_model(MODEL_PATH)
    scalers = joblib.load(SCALERS_PATH)
    metrics = json.loads(METRICS_PATH.read_text())
    df = pd.read_csv(DATA_CSV)

    stock = df[df["Symbol"] == SYMBOL].sort_values("Date")
    if len(stock) < WINDOW:
        print(f"Not enough rows for {SYMBOL} ({len(stock)} < {WINDOW})")
        return 1
    if SYMBOL not in scalers:
        print(f"No scaler for {SYMBOL}")
        return 1

    scaler = scalers[SYMBOL]
    window = stock["Close"].values[-WINDOW:].reshape(-1, 1)
    scaled = scaler.transform(window)
    x = np.reshape(scaled, (1, WINDOW, 1))
    pred_scaled = model.predict(x, verbose=0)
    pred = float(scaler.inverse_transform(pred_scaled)[0][0])
    confidence = float(metrics.get("symbols", {}).get(SYMBOL, {}).get("confidence", 0.5))
    as_of = stock.iloc[-1]["Date"]

    print(f"RELIANCE predicted next close: ₹{pred:,.2f} (confidence {confidence:.4f}, as_of {as_of})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
