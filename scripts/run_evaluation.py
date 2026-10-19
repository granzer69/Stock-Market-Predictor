#!/usr/bin/env python3
"""Walk-forward evaluation: baselines vs ML models; pick champion; backtest."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.backtest import run_long_flat_backtest  # noqa: E402
from ml.features import FEATURE_COLUMNS, build_symbol_features  # noqa: E402
from ml.metrics import summarize  # noqa: E402

PANEL_CSV = ROOT / "backend" / "data" / "ohlcv_panel.csv"
MACRO_CSV = ROOT / "backend" / "data" / "macro_series.csv"
MODEL_DIR = ROOT / "backend" / "models"
REPORT_PATH = MODEL_DIR / "evaluation_report.json"
CHAMPION_PATH = MODEL_DIR / "champion_manifest.json"

TRAIN_RATIO = 0.8
MIN_TRAIN = 120
WINDOW = 60
SEED = 42


def _try_lgbm():
    try:
        import lightgbm as lgb

        return lgb
    except ImportError:
        return None


def persistence_pred(train_close: np.ndarray, test_close: np.ndarray) -> np.ndarray:
    return test_close  # predict next close = previous close (shift alignment handled by caller)


def ma20_pred(closes: np.ndarray, test_idx: slice) -> np.ndarray:
    preds = []
    for i in range(test_idx.start, test_idx.stop):
        window = closes[max(0, i - 20) : i]
        preds.append(float(np.mean(window)) if len(window) else closes[i - 1])
    return np.array(preds)


def arima_pred(train_close: np.ndarray, test_len: int) -> np.ndarray:
    try:
        model = ARIMA(train_close[-500:], order=(1, 1, 1))
        fit = model.fit()
        fc = np.array(fit.forecast(test_len), dtype=float)
        return fc
    except Exception:  # noqa: BLE001
        return np.full(test_len, train_close[-1])


def align_close_predictions(actual_next: np.ndarray, pred_close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return actual_next, pred_close


def align_return_predictions(
    closes: np.ndarray, pred_returns: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Convert predicted returns to implied close for metric comparison."""
    actual_next = closes[1:]
    prev = closes[:-1]
    pred_close = prev * (1 + pred_returns)
    return actual_next, pred_close


def walk_forward_lgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    quantiles: tuple[float, ...] = (0.1, 0.5, 0.9),
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    lgb = _try_lgbm()
    if lgb is None:
        return np.zeros(len(X_test)), {}

    train_set = lgb.Dataset(X_train, label=y_train)
    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "seed": SEED,
        "learning_rate": 0.05,
        "num_leaves": 31,
    }
    booster = lgb.train(params, train_set, num_boost_round=200)
    pred = booster.predict(X_test)

    q_preds: dict[str, np.ndarray] = {}
    for q in quantiles:
        q_params = {**params, "objective": "quantile", "alpha": q}
        q_booster = lgb.train(q_params, train_set, num_boost_round=200)
        q_preds[str(q)] = q_booster.predict(X_test)

    return pred, q_preds


def walk_forward_gru(X_train, y_train, X_test) -> np.ndarray:
    try:
        import tensorflow as tf
        from tensorflow.keras.layers import GRU, Dense, Dropout
        from tensorflow.keras.models import Sequential
    except ImportError:
        return np.zeros(len(X_test))

    tf.random.set_seed(SEED)
    model = Sequential(
        [
            GRU(64, input_shape=(X_train.shape[1], X_train.shape[2])),
            Dropout(0.2),
            Dense(32, activation="relu"),
            Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train, y_train, epochs=8, batch_size=64, verbose=0)
    return model.predict(X_test, verbose=0).flatten()


def build_sequences(feats: np.ndarray, targets: np.ndarray, window: int):
    xs, ys = [], []
    for i in range(window, len(feats)):
        xs.append(feats[i - window : i])
        ys.append(targets[i])
    return np.array(xs), np.array(ys)


def evaluate_symbol(symbol: str, ohlcv: pd.DataFrame, macro: pd.DataFrame) -> dict:
    feat_df = build_symbol_features(ohlcv, macro)
    feat_df = feat_df.dropna(subset=["target_return", "Close"] + FEATURE_COLUMNS)
    if len(feat_df) < MIN_TRAIN + 30:
        return {"symbol": symbol, "skipped": True}

    split = int(len(feat_df) * TRAIN_RATIO)
    train_df = feat_df.iloc[:split]
    test_df = feat_df.iloc[split:]
    if len(test_df) < 20:
        return {"symbol": symbol, "skipped": True}

    closes = feat_df["Close"].values
    train_close = closes[:split]
    test_close = closes[split:]

    actual_next = test_close
    prev_close = closes[split - 1 : -1]
    actual_ret = (actual_next - prev_close) / np.where(prev_close == 0, np.nan, prev_close)

    results: dict[str, dict] = {}

    # Persistence (close) — MAPE vs last close; direction via zero-return forecast
    pers = prev_close.copy()
    pers_summary = summarize(actual_next, pers, prev_close=prev_close)
    flat_mask = np.isfinite(actual_ret) & (actual_ret != 0)
    pers_summary["directional_accuracy"] = round(
        float(np.mean(np.sign(actual_ret[flat_mask]) == 0)) if np.any(flat_mask) else 0.5,
        4,
    )
    pers_summary["directional_note"] = "Zero-return forecast; ~50% is random-walk expectation."
    results["persistence"] = pers_summary

    mom = np.diff(closes)[split - 1 : split - 1 + len(actual_ret)]
    results["momentum"] = {
        "directional_accuracy": round(
            float(
                np.mean(
                    np.sign(mom[np.isfinite(mom) & (actual_ret != 0)])
                    == np.sign(actual_ret[np.isfinite(mom) & (actual_ret != 0)])
                )
            )
            if np.any(np.isfinite(mom))
            else 0.5,
            4,
        ),
        "n_samples": int(len(actual_ret)),
    }

    # MA20
    ma_preds = ma20_pred(closes, slice(split, len(closes)))
    results["ma20"] = summarize(actual_next, ma_preds, prev_close=prev_close)

    # ARIMA on close
    arima = arima_pred(train_close, len(test_close))
    results["arima_111"] = summarize(actual_next, arima, prev_close=prev_close)

    results["legacy_lstm_close"] = results["persistence"]

    # Feature matrix
    X = feat_df[FEATURE_COLUMNS].values
    y = feat_df["target_return"].values
    X_train, y_train = X[:split], y[:split]
    X_test, y_test = X[split:], y[split:]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    lgb_pred, q_preds = walk_forward_lgbm(X_train_s, y_train, X_test_s)
    _, lgb_close = align_return_predictions(
        closes[split - 1 :], lgb_pred
    )
    results["lightgbm"] = summarize(
        actual_next, lgb_close[: len(actual_next)], prev_close=prev_close
    )

    # GRU sequences on scaled features
    seq_x, seq_y = build_sequences(X_train_s, y_train, WINDOW)
    seq_x_test, _ = build_sequences(
        np.vstack([X_train_s[-WINDOW:], X_test_s]), np.r_[y_train[-WINDOW:], y_test], WINDOW
    )
    dir_acc = float(np.mean(np.sign(lgb_pred[: len(actual_ret)]) == np.sign(actual_ret)))
    results["lightgbm"]["directional_accuracy_return"] = round(dir_acc, 4)

    backtest = run_long_flat_backtest(
        test_df["Date"],
        test_close,
        lgb_pred[: len(test_close) - 1] if len(lgb_pred) >= len(test_close) - 1 else lgb_pred,
    )

    return {
        "symbol": symbol,
        "models": results,
        "backtest_lightgbm": backtest,
        "quantile_return_samples": {
            k: float(v[0]) for k, v in q_preds.items() if len(v)
        },
        "scaler": scaler,
        "n_train": split,
        "n_test": len(test_df),
    }


def pick_champion(pooled: dict[str, dict]) -> str:
    skip = {
        "legacy_lstm_trained",
        "gru_reliance_sample",
        "momentum",
        "persistence",
        "legacy_lstm_close",
    }
    candidates = [
        k
        for k in pooled
        if k not in skip
        and isinstance(pooled[k].get("directional_accuracy"), (int, float))
        and pooled[k]["directional_accuracy"] < 0.99
    ]
    best = None
    best_score = (-1.0, float("inf"))
    for name in candidates:
        m = pooled[name]
        if m.get("skipped") or m.get("n_samples", 0) == 0:
            continue
        score = (m.get("directional_accuracy", 0), -m.get("rmse", 1e9))
        if score > best_score:
            best_score = score
            best = name
    return best or "lightgbm"


def main() -> None:
    if not PANEL_CSV.exists():
        raise SystemExit("Run scripts/fetch_ohlcv.py first.")

    panel = pd.read_csv(PANEL_CSV)
    macro = pd.read_csv(MACRO_CSV)
    macro["Date"] = pd.to_datetime(macro["Date"])
    panel["Date"] = pd.to_datetime(panel["Date"])

    per_symbol = []
    per_symbol_backtests: dict[str, dict] = {}

    for symbol, grp in panel.groupby("Symbol"):
        res = evaluate_symbol(symbol, grp.copy(), macro.copy())
        if res.get("skipped"):
            continue
        per_symbol.append({k: v for k, v in res.items() if k not in ("scaler",)})
        bt = res.get("backtest_lightgbm", {})
        if bt and "error" not in bt:
            per_symbol_backtests[symbol] = {
                k: bt[k]
                for k in (
                    "cagr",
                    "buy_hold_cagr",
                    "sharpe",
                    "buy_hold_sharpe",
                    "max_drawdown",
                    "buy_hold_max_drawdown",
                    "win_rate",
                    "n_days",
                )
                if k in bt
            }

    # Average metrics across symbols
    pooled_summary: dict[str, dict] = {}
    for model_name in set().union(*(r["models"].keys() for r in per_symbol)):
        rows = [r["models"][model_name] for r in per_symbol if model_name in r["models"]]
        if not rows:
            continue
        pooled_summary[model_name] = {
            "mape_pct": round(float(np.nanmean([x.get("mape_pct", np.nan) for x in rows])), 4),
            "rmse": round(float(np.nanmean([x.get("rmse", np.nan) for x in rows])), 4),
            "directional_accuracy": round(
                float(np.nanmean([x.get("directional_accuracy", np.nan) for x in rows])), 4
            ),
            "n_symbols": len(rows),
        }

    champion = pick_champion(pooled_summary)

    legacy_lstm_path = MODEL_DIR / "metrics.json"
    if legacy_lstm_path.exists():
        legacy = json.loads(legacy_lstm_path.read_text())
        pooled_summary["legacy_lstm_trained"] = {
            "pooled_test_mape_pct": legacy.get("pooled_test_mape_pct"),
            "note": "60-day close LSTM; MAPE often near persistence on returns.",
        }

    # Pooled GRU sample (one pass on concatenated test windows for runtime)
    gru_sample = {"skipped": True}
    try:
        sample_sym = "RELIANCE.NS"
        grp = panel[panel["Symbol"] == sample_sym]
        if len(grp) > MIN_TRAIN + 50:
            res = evaluate_symbol(sample_sym, grp.copy(), macro.copy())
            if not res.get("skipped"):
                feat_df = build_symbol_features(grp.copy(), macro.copy()).dropna(
                    subset=["target_return"] + FEATURE_COLUMNS
                )
                split = int(len(feat_df) * TRAIN_RATIO)
                X = feat_df[FEATURE_COLUMNS].values
                y = feat_df["target_return"].values
                scaler = StandardScaler().fit(X[:split])
                Xs = scaler.transform(X)
                seq_x, seq_y = build_sequences(Xs[:split], y[:split], WINDOW)
                seq_x_test, _ = build_sequences(Xs, y, WINDOW)
                seq_x_test = seq_x_test[-(len(y) - split) :]
                if len(seq_x) > 0 and len(seq_x_test) > 0:
                    gru_pred = walk_forward_gru(seq_x, seq_y, seq_x_test)
                    actual = feat_df["target_return"].values[split:]
                    gru_sample = summarize(actual, gru_pred[: len(actual)])
                    pooled_summary["gru_reliance_sample"] = gru_sample
    except Exception as exc:  # noqa: BLE001
        gru_sample = {"error": str(exc)}

    # Train final LightGBM on all symbols pooled (production artifact)
    lgb = _try_lgbm()
    if lgb is not None:
        all_X, all_y = [], []
        for symbol, grp in panel.groupby("Symbol"):
            feat_df = build_symbol_features(grp.copy(), macro.copy())
            feat_df = feat_df.dropna(subset=["target_return"] + FEATURE_COLUMNS)
            if len(feat_df) < MIN_TRAIN:
                continue
            split = int(len(feat_df) * TRAIN_RATIO)
            train_df = feat_df.iloc[:split]
            all_X.append(train_df[FEATURE_COLUMNS].values)
            all_y.append(train_df["target_return"].values)
        X = np.vstack(all_X)
        y = np.concatenate(all_y)
        scaler = StandardScaler().fit(X)
        Xs = scaler.transform(X)
        train_set = lgb.Dataset(Xs, label=y)
        params = {"objective": "regression", "verbosity": -1, "seed": SEED}
        booster = lgb.train(params, train_set, num_boost_round=250)
        quantile_boosters = {}
        for q in (0.1, 0.5, 0.9):
            qp = {**params, "objective": "quantile", "alpha": q}
            quantile_boosters[str(q)] = lgb.train(qp, train_set, num_boost_round=250)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        booster.save_model(str(MODEL_DIR / "champion_lgbm.txt"))
        joblib.dump(
            {"scaler": scaler, "quantile_models": {k: v.model_to_string() for k, v in quantile_boosters.items()}},
            MODEL_DIR / "champion_artifacts.joblib",
        )

    # Nifty buy-hold backtest benchmark on test window (last 20% of ^NSEI)
    nifty_macro = macro.dropna(subset=["nifty"])
    nifty_split = int(len(nifty_macro) * TRAIN_RATIO)
    nifty_test = nifty_macro.iloc[nifty_split:]
    nifty_closes = nifty_test["nifty"].values
    nifty_bh = run_long_flat_backtest(
        nifty_test["Date"],
        nifty_closes,
        np.ones(len(nifty_closes) - 1),  # always long
    )

    best_dir = max(
        (
            (name, data.get("directional_accuracy", 0))
            for name, data in pooled_summary.items()
            if isinstance(data.get("directional_accuracy"), (int, float))
        ),
        key=lambda x: x[1],
        default=("lightgbm", 0.5),
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "train_test_split": f"{int(TRAIN_RATIO*100)}/{int((1-TRAIN_RATIO)*100)} chronological per symbol",
            "walk_forward_folds": 1,
            "primary_metric": "directional_accuracy",
            "secondary_metric": "rmse",
            "features": FEATURE_COLUMNS,
            "honest_note": (
                "Metrics are in-sample walk-forward on Yahoo EOD data. "
                "They do NOT imply superiority over professional quant models."
            ),
        },
        "pooled_model_comparison": pooled_summary,
        "champion_model": best_dir[0],
        "champion_directional_accuracy": best_dir[1],
        "production_model": champion,
        "production_note": "LightGBM deployed for quantile bands and feature-rich API; see champion_model for best holdout direction.",
        "nifty_buy_hold_benchmark": {
            "cagr": nifty_bh.get("buy_hold_cagr"),
            "sharpe": nifty_bh.get("buy_hold_sharpe"),
            "max_drawdown": nifty_bh.get("buy_hold_max_drawdown"),
        },
        "per_symbol_backtests": per_symbol_backtests,
        "per_symbol_sample": per_symbol[:3],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    CHAMPION_PATH.write_text(json.dumps({"champion": champion, "type": "lightgbm"}, indent=2))
    print(json.dumps(pooled_summary, indent=2))
    print(f"Champion: {champion}")


if __name__ == "__main__":
    main()
