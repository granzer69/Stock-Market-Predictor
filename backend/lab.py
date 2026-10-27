"""Paper-lab jobs, the independent gate, and paper sessions.

Training writes a side directory. It does not write ``backend/artifacts`` or
``champion_lgbm.txt``. A job becomes approved only after the gate passes and a
person calls approve. Nothing here talks to a broker.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from app_config import paper_apply_india_costs
from portfolio import STARTING_CASH

_BACKEND = Path(__file__).resolve().parent
_ROOT = _BACKEND.parent
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from ml.metrics import directional_accuracy, momentum_directional_accuracy, naive_mae  # noqa: E402

ARTIFACTS_DIR = _BACKEND / "artifacts"
MODELS_DIR = _BACKEND / "models"
CHAMPION_FILE = MODELS_DIR / "champion_lgbm.txt"
PROTECTED_FILES = (
    ARTIFACTS_DIR / "metrics.json",
    ARTIFACTS_DIR / "model.keras",
    ARTIFACTS_DIR / "scaler.joblib",
    CHAMPION_FILE,
)

CANDIDATES = ("lstm_returns", "lightgbm")
ACTIVE_STATUSES = ("running", "paused")

# Published claims the gate is expected to reject. Not a new measurement.
PUBLISHED_LSTM_MAE = 0.012051809898621074
PUBLISHED_LSTM_NAIVE = 0.011987893123182505
PUBLISHED_LIGHTGBM_DIRECTIONAL = 0.4707

_SERVICES: dict[str, "LabService"] = {}


class LabConflict(Exception):
    """The request fights a job or session that is already in progress."""


class LabBadRequest(Exception):
    """The command does not apply to this job."""


class TrainNotStarted(Exception):
    """Start found no daily bars on disk, so the trainer was not called."""


NO_LOCAL_BARS = "no local bars; train not started"


class JobControl:
    def __init__(self, limit_seconds: float):
        self._pause = threading.Event()
        self._cancel = threading.Event()
        self._started = time.monotonic()
        self._limit = limit_seconds

    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.clear()

    def canceled(self) -> bool:
        if self._cancel.is_set():
            return True
        return (time.monotonic() - self._started) >= self._limit

    def timed_out(self) -> bool:
        return (time.monotonic() - self._started) >= self._limit and not self._cancel.is_set()

    def wait_if_paused(self) -> bool:
        while self._pause.is_set():
            if self.canceled():
                return False
            time.sleep(0.02)
        return not self.canceled()


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_side_directory(side_dir: Path) -> None:
    """Refuse the live artifact directory and the champion booster file."""
    side = Path(side_dir).resolve()
    artifacts = ARTIFACTS_DIR.resolve()
    models = MODELS_DIR.resolve()
    champion = CHAMPION_FILE.resolve()
    if side == artifacts or _is_inside(side, artifacts) or _is_inside(artifacts, side):
        raise RuntimeError("refusing to write backend/artifacts")
    if side == models or _is_inside(side, models) or side == champion or side.name == "champion_lgbm.txt":
        raise RuntimeError("refusing to write champion_lgbm.txt")


def protected_snapshot() -> dict[str, tuple[int, int] | None]:
    snapshot: dict[str, tuple[int, int] | None] = {}
    for path in PROTECTED_FILES:
        if path.exists():
            stat = path.stat()
            snapshot[str(path)] = (stat.st_mtime_ns, stat.st_size)
        else:
            snapshot[str(path)] = None
    return snapshot


def _config_hash(candidate_id: str, config: dict) -> str:
    payload = json.dumps({"candidate_id": candidate_id, "config": config}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _max_runtime() -> float:
    try:
        return max(1.0, float(os.environ.get("LAB_MAX_RUNTIME_SECONDS", "180")))
    except ValueError:
        return 180.0


def stored_claim_metrics(candidate_id: str) -> dict:
    """Side-directory metrics for a stored claim. The gate rejects both."""
    closes = [100.0, 110.0, 100.0, 110.0, 100.0, 110.0]
    common = {
        "candidate_id": candidate_id,
        "holdout": "tail",
        "holdout_fraction": 0.2,
        "training_shuffle": False,
        "closes": closes,
        "split": 4,
    }
    if candidate_id == "lightgbm":
        return {
            **common,
            "claimed_metric": "directional_accuracy",
            "claimed_value": PUBLISHED_LIGHTGBM_DIRECTIONAL,
            "actual_log_returns": [0.01, -0.01, 0.01, -0.01, 0.01],
            "predicted_log_returns": [-0.01, 0.01, -0.01, 0.01, 0.01],
        }
    actual = PUBLISHED_LSTM_NAIVE
    predicted = PUBLISHED_LSTM_NAIVE - PUBLISHED_LSTM_MAE
    return {
        **common,
        "candidate_id": "lstm_returns",
        "claimed_metric": "mae_log_return",
        "claimed_value": PUBLISHED_LSTM_MAE,
        "naive_mae_log_return": PUBLISHED_LSTM_NAIVE,
        "actual_log_returns": [actual],
        "predicted_log_returns": [predicted],
    }


def passing_tail_metrics(candidate_id: str = "lstm_returns") -> dict:
    """A synthetic tail split that beats predict-zero. Used to exercise approve."""
    return {
        "candidate_id": candidate_id,
        "claimed_metric": "mae_log_return",
        "holdout": "tail",
        "holdout_fraction": 0.2,
        "training_shuffle": False,
        "actual_log_returns": [0.02, -0.02],
        "predicted_log_returns": [0.019, -0.019],
        "closes": [100.0, 110.0, 100.0, 110.0, 100.0, 110.0],
        "split": 4,
    }


def write_metrics_file(side_dir: Path, metrics: dict) -> None:
    assert_side_directory(side_dir)
    side_dir.mkdir(parents=True, exist_ok=True)
    target = side_dir / "metrics.json"
    if target.name == "champion_lgbm.txt":
        raise RuntimeError("refusing to write champion_lgbm.txt")
    target.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def _as_float_array(values) -> np.ndarray | None:
    if not isinstance(values, list) or not values:
        return None
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if not np.all(np.isfinite(array)):
        return None
    return array


def _summary_mae(metrics: dict) -> tuple[float, float] | None:
    """MAE pair written by ``train_and_save`` when the side file has no return series."""
    if "mae_log_return" not in metrics or "naive_mae_log_return" not in metrics:
        return None
    try:
        model_mae = float(metrics["mae_log_return"])
        baseline = float(metrics["naive_mae_log_return"])
    except (TypeError, ValueError):
        return None
    if not np.isfinite(model_mae) or not np.isfinite(baseline):
        return None
    return model_mae, baseline


def verify_metrics(metrics: dict | None) -> tuple[str, str | None, dict]:
    """Recompute naive MAE and lagged momentum. Does not refit."""
    if not metrics:
        return "rejected", "metrics file missing", {}

    reasons: list[str] = []
    recomputed: dict = {}

    shuffle = metrics.get("training_shuffle")
    holdout = metrics.get("holdout")
    if shuffle is not False or "holdout_fraction" not in metrics or (holdout is not None and holdout != "tail"):
        reasons.append("holdout is not a tail split")

    reported_momentum = metrics.get("momentum_directional_accuracy")
    if reported_momentum is not None:
        try:
            reported_value = float(reported_momentum)
        except (TypeError, ValueError):
            reported_value = None
        if reported_value == 1.0:
            reasons.append("momentum directional accuracy is 1.0 on the same return")

    closes = _as_float_array(metrics.get("closes"))
    split = metrics.get("split")
    if closes is not None and isinstance(split, int) and not isinstance(split, bool) and split >= 2 and len(closes) > split:
        lagged = momentum_directional_accuracy(closes, split)
        recomputed["momentum_directional_accuracy"] = lagged["directional_accuracy"]
        recomputed["momentum_basis"] = "lagged"

    claimed = metrics.get("claimed_metric")
    if not claimed:
        claimed = "directional_accuracy" if metrics.get("candidate_id") == "lightgbm" else "mae_log_return"

    actual = _as_float_array(metrics.get("actual_log_returns"))
    predicted = _as_float_array(metrics.get("predicted_log_returns"))
    summary_mae = _summary_mae(metrics)
    if actual is not None and predicted is not None and len(actual) == len(predicted) and claimed == "directional_accuracy":
        score = float(directional_accuracy(actual, predicted))
        recomputed["directional_accuracy"] = score
        claimed_value = metrics.get("claimed_value")
        try:
            claimed_score = float(claimed_value) if claimed_value is not None else None
        except (TypeError, ValueError):
            claimed_score = None
        if claimed_score is not None and not claimed_score > 0.5:
            reasons.append(
                f"directional_accuracy {claimed_score:.4f} does not beat the naive baseline 0.5"
            )
        elif not score > 0.5:
            reasons.append(f"directional_accuracy {score:.4f} does not beat the naive baseline 0.5")
    elif actual is not None and predicted is not None and len(actual) == len(predicted):
        model_mae = float(np.mean(np.abs(actual - predicted)))
        baseline = float(naive_mae(actual))
        recomputed["mae_log_return"] = model_mae
        recomputed["naive_mae"] = baseline
        if not model_mae < baseline:
            reasons.append(f"mae_log_return {model_mae:.6f} does not beat naive MAE {baseline:.6f}")
    elif summary_mae is not None:
        model_mae, baseline = summary_mae
        recomputed["mae_log_return"] = model_mae
        recomputed["naive_mae"] = baseline
        if not model_mae < baseline:
            reasons.append(f"mae_log_return {model_mae:.6f} does not beat naive MAE {baseline:.6f}")
    else:
        reasons.append("cannot recompute naive MAE")

    if reasons:
        return "rejected", "; ".join(reasons), recomputed
    return "verified", None, recomputed


_PERIOD_RANK = {"5y": 0, "2y": 1, "1y": 2, "6mo": 3}


def disk_bar_sources() -> tuple[Path, Path, Path]:
    """Cache history, NSE CSV directory, and the local OHLCV panel. No network."""
    from app_config import nse_csv_dir

    configured = nse_csv_dir().strip()
    nse_dir = Path(configured) if configured else _BACKEND / "data" / "nse_daily"
    return (
        _BACKEND / "cache" / "history",
        nse_dir,
        _BACKEND / "data" / "ohlcv_panel.csv",
    )


def _usable_frame(frame: pd.DataFrame | None) -> bool:
    if frame is None or frame.empty or "Close" not in frame.columns:
        return False
    closes = pd.to_numeric(frame["Close"], errors="coerce")
    return bool(closes.notna().any())


def _cache_history_frames(history_dir: Path) -> dict[str, pd.DataFrame]:
    if not history_dir.is_dir():
        return {}
    best: dict[str, tuple[int, Path]] = {}
    for path in history_dir.glob("*.csv"):
        if "__" not in path.stem:
            continue
        symbol, period = path.stem.rsplit("__", 1)
        rank = _PERIOD_RANK.get(period, 9)
        current = best.get(symbol)
        if current is None or rank < current[0]:
            best[symbol] = (rank, path)
    frames: dict[str, pd.DataFrame] = {}
    for symbol, (_rank, path) in best.items():
        frame = pd.read_csv(path)
        if _usable_frame(frame):
            frames[symbol] = frame
    return frames


def _nse_csv_frames(root: Path) -> dict[str, pd.DataFrame]:
    if not root.is_dir():
        return {}
    from data_providers import LicensedIndiaDailyProvider
    from universe import NIFTY_50

    symbols = [item.symbol for item in NIFTY_50 if item.kind == "equity"]
    try:
        found = LicensedIndiaDailyProvider(root).fetch(symbols, "5y") or {}
    except FileNotFoundError:
        return {}
    return {symbol: frame for symbol, frame in found.items() if _usable_frame(frame)}


def _panel_frames(path: Path) -> dict[str, pd.DataFrame]:
    if not path.is_file():
        return {}
    frame = pd.read_csv(path)
    if "Symbol" not in frame.columns or "Close" not in frame.columns:
        return {}
    frames: dict[str, pd.DataFrame] = {}
    for symbol, group in frame.groupby("Symbol", sort=False):
        bars = group.reset_index(drop=True)
        if _usable_frame(bars):
            frames[str(symbol)] = bars
    return frames


def local_bar_frames(symbol_cap: int) -> dict[str, pd.DataFrame]:
    """Daily bars already stored on disk, capped. Does not call Yahoo."""
    if symbol_cap < 1:
        return {}
    history_dir, nse_dir, panel_path = disk_bar_sources()
    found: dict[str, pd.DataFrame] = {}
    for batch in (
        _cache_history_frames(history_dir),
        _nse_csv_frames(nse_dir),
        _panel_frames(panel_path),
    ):
        for symbol, frame in batch.items():
            if symbol not in found:
                found[symbol] = frame
    if not found:
        return {}
    from universe import NIFTY_50

    ordered = [item.symbol for item in NIFTY_50 if item.kind == "equity" and item.symbol in found]
    for symbol in found:
        if symbol not in ordered:
            ordered.append(symbol)
    return {symbol: found[symbol] for symbol in ordered[:symbol_cap]}


def default_trainer(candidate_id: str, side_dir: Path, config: dict, log, control: JobControl) -> None:
    """Train with ``train_and_save`` when disk bars exist. Otherwise refuse.

    ``artifact_dir`` is the job side directory. The committed artifact folder
    and ``champion_lgbm.txt`` are not written. Yahoo is not contacted.
    """
    del candidate_id
    assert_side_directory(side_dir)
    if not control.wait_if_paused():
        log("stopped before training")
        return
    epochs = int(os.environ.get("LSTM_EPOCHS", "8"))
    try:
        symbol_cap = max(1, int(os.environ.get("LAB_SYMBOL_CAP", str((config or {}).get("symbol_cap", 2)))))
    except (TypeError, ValueError):
        symbol_cap = 2
    frames = local_bar_frames(symbol_cap)
    if not frames:
        raise TrainNotStarted(NO_LOCAL_BARS)
    log(
        f"entry point train_lstm.train_and_save; fixed budget LSTM_EPOCHS={epochs} "
        f"symbol_cap={symbol_cap}; writing {side_dir.name} only"
    )
    from train_lstm import train_and_save

    before = protected_snapshot()
    train_and_save(frames, artifact_dir=side_dir)
    if protected_snapshot() != before:
        raise RuntimeError("protected artifacts changed")
    log("train_and_save finished in the side directory")


def service_for(db_path: str | Path, runs_dir: str | Path) -> "LabService":
    key = str(db_path)
    service = _SERVICES.get(key)
    if service is None:
        service = LabService(db_path, runs_dir)
        _SERVICES[key] = service
    return service


class LabService:
    def __init__(self, db_path: str | Path, runs_dir: str | Path):
        self.db_path = str(db_path)
        self.runs_dir = Path(runs_dir)
        self._lock = threading.RLock()
        self._controls: dict[str, JobControl] = {}
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS lab_jobs (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        candidate_id TEXT NOT NULL,
                        config_hash TEXT NOT NULL,
                        config_json TEXT NOT NULL,
                        metrics_json TEXT,
                        rejection_reason TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        log_text TEXT NOT NULL DEFAULT '',
                        side_dir TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lab_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        approved_job_id TEXT,
                        previous_approved_job_id TEXT
                    );
                    CREATE TABLE IF NOT EXISTS lab_sessions (
                        id TEXT PRIMARY KEY,
                        approved_job_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        halt_reason TEXT,
                        max_names INTEGER NOT NULL,
                        max_notional REAL NOT NULL,
                        max_daily_loss REAL NOT NULL,
                        apply_india_costs INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS lab_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        quote_date TEXT NOT NULL,
                        order_id INTEGER,
                        model TEXT,
                        model_version TEXT,
                        forecast_as_of TEXT,
                        fill_date TEXT,
                        UNIQUE(session_id, symbol, quote_date)
                    );
                    """
                )
                conn.execute(
                    "INSERT OR IGNORE INTO lab_state (id, approved_job_id, previous_approved_job_id) VALUES (1, NULL, NULL)"
                )
                conn.commit()
            finally:
                conn.close()

    def _job_from_row(self, row: sqlite3.Row) -> dict:
        metrics = None
        if row["metrics_json"]:
            metrics = json.loads(row["metrics_json"])
        lines = [line for line in (row["log_text"] or "").splitlines() if line]
        return {
            "id": row["id"],
            "status": row["status"],
            "candidate_id": row["candidate_id"],
            "config_hash": row["config_hash"],
            "metrics": metrics,
            "rejection_reason": row["rejection_reason"],
            "created_at": row["created_at"],
            "log_tail": "\n".join(lines[-30:]),
        }

    def _load(self, conn: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM lab_jobs WHERE id = ?", (job_id,)).fetchone()

    def list_jobs(self) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM lab_jobs ORDER BY created_at DESC").fetchall()
                state = conn.execute("SELECT approved_job_id, previous_approved_job_id FROM lab_state WHERE id = 1").fetchone()
                session = conn.execute(
                    "SELECT * FROM lab_sessions ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                return {
                    "jobs": [self._job_from_row(row) for row in rows],
                    "approved_job_id": state["approved_job_id"] if state else None,
                    "previous_approved_job_id": state["previous_approved_job_id"] if state else None,
                    "session": _session_dict(session),
                }
            finally:
                conn.close()

    def append_log(self, job_id: str, message: str) -> None:
        line = message.rstrip("\n")
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
                if row is None:
                    return
                text = row["log_text"] + line + "\n"
                conn.execute(
                    "UPDATE lab_jobs SET log_text = ?, updated_at = ? WHERE id = ?",
                    (text, _now(), job_id),
                )
                conn.commit()
            finally:
                conn.close()

    def _set_status(self, job_id: str, status: str, reason: str | None = None, metrics: dict | None = None) -> None:
        with self._lock:
            conn = self._connect()
            try:
                if metrics is None and reason is None:
                    conn.execute(
                        "UPDATE lab_jobs SET status = ?, updated_at = ? WHERE id = ?",
                        (status, _now(), job_id),
                    )
                else:
                    current = self._load(conn, job_id)
                    metrics_json = current["metrics_json"] if current else None
                    if metrics is not None:
                        metrics_json = json.dumps(metrics)
                    conn.execute(
                        """
                        UPDATE lab_jobs
                        SET status = ?, rejection_reason = ?, metrics_json = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (status, reason, metrics_json, _now(), job_id),
                    )
                conn.commit()
            finally:
                conn.close()

    def _status(self, job_id: str) -> str | None:
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
                return row["status"] if row else None
            finally:
                conn.close()

    def start(self, candidate_id: str, config: dict | None = None) -> dict:
        if candidate_id not in CANDIDATES:
            raise LabBadRequest("candidate_id must be lstm_returns or lightgbm")
        clean = dict(config or {})
        frames = clean.pop("frames", None)
        if frames is not None:
            clean["frames"] = frames
        # HTTP callers pass JSON only. A non-mapping frames value is dropped.
        if "frames" in clean and not hasattr(clean["frames"], "items"):
            clean.pop("frames")
        stored_config = {key: value for key, value in clean.items() if key != "frames"}
        with self._lock:
            conn = self._connect()
            try:
                active = conn.execute(
                    "SELECT id FROM lab_jobs WHERE status IN ('running', 'paused') LIMIT 1"
                ).fetchone()
                if active is not None:
                    raise LabConflict("a lab job is already running")
                job_id = uuid.uuid4().hex[:12]
                side = self.runs_dir / job_id
                assert_side_directory(side)
                side.mkdir(parents=True, exist_ok=True)
                created = _now()
                conn.execute(
                    """
                    INSERT INTO lab_jobs (
                        id, status, candidate_id, config_hash, config_json, metrics_json,
                        rejection_reason, created_at, updated_at, log_text, side_dir
                    ) VALUES (?, 'running', ?, ?, ?, NULL, NULL, ?, ?, '', ?)
                    """,
                    (
                        job_id,
                        candidate_id,
                        _config_hash(candidate_id, stored_config),
                        json.dumps(stored_config, sort_keys=True),
                        created,
                        created,
                        str(side),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            control = JobControl(_max_runtime())
            self._controls[job_id] = control
            trainer = TRAINER
            thread = threading.Thread(
                target=self._execute,
                args=(job_id, trainer, control, clean),
                name=f"lab-{job_id}",
                daemon=True,
            )
            thread.start()
        return self._public_job(job_id)

    def _public_job(self, job_id: str) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
            finally:
                conn.close()
        if row is None:
            raise LabBadRequest("unknown job")
        return self._job_from_row(row)

    def _execute(self, job_id: str, trainer, control: JobControl, config: dict) -> None:
        try:
            if not control.wait_if_paused():
                self._stop(job_id, control)
                return
            with self._lock:
                conn = self._connect()
                try:
                    row = self._load(conn, job_id)
                finally:
                    conn.close()
            if row is None or row["status"] == "canceled":
                return
            try:
                trainer(
                    row["candidate_id"],
                    Path(row["side_dir"]),
                    config,
                    lambda message: self.append_log(job_id, message),
                    control,
                )
            except TrainNotStarted as exc:
                reason = str(exc) or NO_LOCAL_BARS
                self.append_log(job_id, reason)
                self._set_status(job_id, "rejected", reason=reason)
                return
            if self._status(job_id) == "canceled" or control.canceled():
                self._stop(job_id, control)
                return
            while self._status(job_id) == "paused":
                if control.canceled():
                    self._stop(job_id, control)
                    return
                time.sleep(0.02)
            self.verify(job_id)
        except Exception as exc:  # noqa: BLE001 — a failed job must leave the running slot
            if self._status(job_id) != "canceled":
                self.append_log(job_id, f"training failed: {exc}")
                self._set_status(job_id, "rejected", reason=f"training failed: {exc}")

    def _stop(self, job_id: str, control: JobControl) -> None:
        if self._status(job_id) in {"verified", "rejected", "approved"}:
            return
        reason = "max runtime exceeded" if control.timed_out() else None
        self._set_status(job_id, "canceled", reason=reason)
        self.append_log(job_id, reason or "canceled")

    def verify(self, job_id: str) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
            finally:
                conn.close()
        if row is None:
            raise LabBadRequest("unknown job")
        if row["status"] == "canceled":
            return self._public_job(job_id)
        path = Path(row["side_dir"]) / "metrics.json"
        metrics = None
        if path.exists():
            try:
                metrics = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metrics = None
        status, reason, recomputed = verify_metrics(metrics)
        stored = dict(metrics or {})
        if recomputed:
            stored["recomputed"] = recomputed
        if status == "verified":
            self.append_log(job_id, "gate passed; waiting for manual approval")
        else:
            self.append_log(job_id, f"gate rejected: {reason}")
        self._set_status(job_id, status, reason=reason, metrics=stored)
        return self._public_job(job_id)

    def pause(self, job_id: str) -> dict:
        return self._control(job_id, "pause")

    def resume(self, job_id: str) -> dict:
        return self._control(job_id, "resume")

    def cancel(self, job_id: str) -> dict:
        return self._control(job_id, "cancel")

    def _control(self, job_id: str, action: str) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
            finally:
                conn.close()
            if row is None:
                raise LabBadRequest("unknown job")
            control = self._controls.get(job_id)
            if action == "pause":
                if row["status"] != "running":
                    raise LabBadRequest("job is not running")
                if control:
                    control.pause()
                self._set_status(job_id, "paused")
                self.append_log(job_id, "paused")
            elif action == "resume":
                if row["status"] != "paused":
                    raise LabBadRequest("job is not paused")
                if control:
                    control.resume()
                self._set_status(job_id, "running")
                self.append_log(job_id, "resumed")
            elif action == "cancel":
                if row["status"] not in ACTIVE_STATUSES:
                    raise LabBadRequest("job is not running")
                if control:
                    control.cancel()
                self._set_status(job_id, "canceled", reason=row["rejection_reason"])
                self.append_log(job_id, "canceled")
            else:
                raise LabBadRequest("unknown action")
        return self._public_job(job_id)

    def approve(self, job_id: str) -> dict:
        before = protected_snapshot()
        with self._lock:
            conn = self._connect()
            try:
                row = self._load(conn, job_id)
                if row is None:
                    raise LabBadRequest("unknown job")
                if row["status"] == "rejected":
                    raise LabConflict(f"rejected job cannot be approved: {row['rejection_reason']}")
                if row["status"] != "verified":
                    raise LabConflict("only a verified job can be approved")
                state = conn.execute(
                    "SELECT approved_job_id, previous_approved_job_id FROM lab_state WHERE id = 1"
                ).fetchone()
                previous = state["approved_job_id"]
                if previous and previous != job_id:
                    conn.execute(
                        "UPDATE lab_jobs SET status = 'verified', updated_at = ? WHERE id = ? AND status = 'approved'",
                        (_now(), previous),
                    )
                conn.execute(
                    "UPDATE lab_jobs SET status = 'approved', updated_at = ? WHERE id = ?",
                    (_now(), job_id),
                )
                conn.execute(
                    "UPDATE lab_state SET approved_job_id = ?, previous_approved_job_id = ? WHERE id = 1",
                    (job_id, previous if previous != job_id else state["previous_approved_job_id"]),
                )
                conn.commit()
            finally:
                conn.close()
        if protected_snapshot() != before:
            raise RuntimeError("approve changed protected artifacts")
        self.append_log(job_id, "approved by hand; live artifacts were not replaced")
        return self._public_job(job_id)

    def rollback(self, job_id: str) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                state = conn.execute(
                    "SELECT approved_job_id, previous_approved_job_id FROM lab_state WHERE id = 1"
                ).fetchone()
                if state is None or state["approved_job_id"] != job_id:
                    raise LabBadRequest("job is not the approved model")
                previous = state["previous_approved_job_id"]
                if not previous:
                    raise LabConflict("no previous approved job")
                now = _now()
                conn.execute(
                    "UPDATE lab_jobs SET status = 'verified', updated_at = ? WHERE id = ?",
                    (now, job_id),
                )
                conn.execute(
                    "UPDATE lab_jobs SET status = 'approved', updated_at = ? WHERE id = ?",
                    (now, previous),
                )
                conn.execute(
                    "UPDATE lab_state SET approved_job_id = ?, previous_approved_job_id = NULL WHERE id = 1",
                    (previous,),
                )
                conn.commit()
            finally:
                conn.close()
        self.append_log(job_id, f"rolled back; approved job is {previous}")
        return self.list_jobs()

    def open_session(self, max_names: int, max_notional: float, max_daily_loss: float, apply_india_costs: bool) -> dict:
        schedule_on = paper_apply_india_costs()
        with self._lock:
            conn = self._connect()
            try:
                state = conn.execute("SELECT approved_job_id FROM lab_state WHERE id = 1").fetchone()
                approved = state["approved_job_id"] if state else None
                if not approved:
                    raise LabConflict("unapproved model")
                job = self._load(conn, approved)
                if job is None or job["status"] != "approved":
                    raise LabConflict("unapproved model")
                running = conn.execute(
                    "SELECT id FROM lab_sessions WHERE status = 'running' LIMIT 1"
                ).fetchone()
                if running is not None:
                    raise LabConflict("a paper session is already open")
                session_id = uuid.uuid4().hex[:12]
                conn.execute(
                    """
                    INSERT INTO lab_sessions (
                        id, approved_job_id, status, halt_reason, max_names, max_notional,
                        max_daily_loss, apply_india_costs, created_at
                    ) VALUES (?, ?, 'running', NULL, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        approved,
                        int(max_names),
                        float(max_notional),
                        float(max_daily_loss),
                        1 if (apply_india_costs and schedule_on) else 0,
                        _now(),
                    ),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM lab_sessions WHERE id = ?", (session_id,)).fetchone()
                return _session_dict(row)
            finally:
                conn.close()

    def tick(self, body: dict, book) -> dict:
        symbol = str(body.get("symbol") or "").strip()
        side = str(body.get("side") or "").strip().upper()
        qty = body.get("qty")
        quote = body.get("quote")
        forecast_as_of = body.get("forecast_as_of")
        if not symbol:
            raise LabBadRequest("symbol is required")
        if side not in {"BUY", "SELL"}:
            raise LabBadRequest("side must be BUY or SELL")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise LabBadRequest("qty must be a positive whole number of shares")

        with self._lock:
            conn = self._connect()
            try:
                session = conn.execute(
                    "SELECT * FROM lab_sessions ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if session is None:
                    raise LabConflict("no paper session")
                if session["status"] == "halted":
                    raise LabConflict(f"session is halted: {session['halt_reason']}")
                session_id = session["id"]
                job = self._load(conn, session["approved_job_id"])
                state = conn.execute("SELECT approved_job_id FROM lab_state WHERE id = 1").fetchone()
                approved_id = state["approved_job_id"] if state else None
                requested_model = body.get("model")
                if (
                    job is None
                    or job["status"] != "approved"
                    or approved_id != session["approved_job_id"]
                    or (requested_model and requested_model != job["candidate_id"])
                ):
                    self._halt(conn, session_id, "unapproved model")
                    raise LabConflict("unapproved model")

                quote_reason = _quote_problem(quote)
                if quote_reason:
                    self._halt(conn, session_id, quote_reason)
                    raise LabConflict(quote_reason)
                if not forecast_as_of:
                    self._halt(conn, session_id, "forecast_as_of missing")
                    raise LabConflict("forecast_as_of missing")

                price = float(quote["price"])
                quote_date = str(quote["as_of"])[:10]
                notional = qty * price
                positions = book.positions()
                held = {row["symbol"] for row in positions if int(row["qty"]) > 0}
                if side == "BUY" and symbol not in held and len(held) >= int(session["max_names"]):
                    self._halt(conn, session_id, "max names breached")
                    raise LabConflict("max names breached")
                spent = conn.execute(
                    """
                    SELECT COALESCE(SUM(o.notional), 0) AS spent
                    FROM lab_decisions d
                    JOIN orders o ON o.id = d.order_id
                    WHERE d.session_id = ?
                    """,
                    (session_id,),
                ).fetchone()
                if notional > float(session["max_notional"]) or float(spent["spent"]) + notional > float(session["max_notional"]):
                    self._halt(conn, session_id, "max notional breached")
                    raise LabConflict("max notional breached")
                prices = {row["symbol"]: float(row["avg_cost"]) for row in positions}
                prices[symbol] = price
                snapshot = book.snapshot(prices)
                loss = STARTING_CASH - float(snapshot["equity"])
                if loss >= float(session["max_daily_loss"]):
                    self._halt(conn, session_id, "max daily loss breached")
                    raise LabConflict("max daily loss breached")

                try:
                    conn.execute(
                        """
                        INSERT INTO lab_decisions (
                            session_id, symbol, quote_date, order_id, model, model_version, forecast_as_of, fill_date
                        ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            symbol,
                            quote_date,
                            job["candidate_id"],
                            job["id"],
                            str(forecast_as_of),
                            quote_date,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise LabConflict("duplicate decision for this session, symbol, and quote date") from exc
                conn.commit()
            finally:
                conn.close()

        try:
            order = book.place_order(symbol, side, qty, price)
        except ValueError as exc:
            self._drop_decision(session_id, symbol, quote_date)
            self._halt_id(session_id, str(exc))
            raise LabConflict(str(exc)) from exc

        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE lab_decisions
                    SET order_id = ?
                    WHERE session_id = ? AND symbol = ? AND quote_date = ?
                    """,
                    (order["id"], session_id, symbol, quote_date),
                )
                conn.commit()
                fill = conn.execute(
                    """
                    SELECT session_id, symbol, quote_date, order_id, model, model_version, forecast_as_of, fill_date
                    FROM lab_decisions
                    WHERE session_id = ? AND symbol = ? AND quote_date = ?
                    """,
                    (session_id, symbol, quote_date),
                ).fetchone()
            finally:
                conn.close()
        return {"order": order, "fill": _fill_dict(fill)}

    def _drop_decision(self, session_id: str, symbol: str, quote_date: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "DELETE FROM lab_decisions WHERE session_id = ? AND symbol = ? AND quote_date = ? AND order_id IS NULL",
                    (session_id, symbol, quote_date),
                )
                conn.commit()
            finally:
                conn.close()

    def _halt(self, conn: sqlite3.Connection, session_id: str, reason: str) -> None:
        conn.execute(
            "UPDATE lab_sessions SET status = 'halted', halt_reason = ? WHERE id = ?",
            (reason, session_id),
        )
        conn.commit()

    def _halt_id(self, session_id: str, reason: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                self._halt(conn, session_id, reason)
            finally:
                conn.close()

    def fills(self) -> list[dict]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT session_id, symbol, quote_date, order_id, model, model_version, forecast_as_of, fill_date
                    FROM lab_decisions
                    WHERE order_id IS NOT NULL
                    ORDER BY id
                    """
                ).fetchall()
                return [_fill_dict(row) for row in rows]
            finally:
                conn.close()


def _quote_problem(quote) -> str | None:
    if not isinstance(quote, dict):
        return "quote missing"
    if quote.get("stale") is True:
        return "stale quote"
    price = quote.get("price")
    try:
        if price is None or float(price) <= 0:
            return "quote price missing"
    except (TypeError, ValueError):
        return "quote price missing"
    if not quote.get("as_of"):
        return "quote as_of missing"
    return None


def _session_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "approved_job_id": row["approved_job_id"],
        "status": row["status"],
        "halt_reason": row["halt_reason"],
        "max_names": int(row["max_names"]),
        "max_notional": float(row["max_notional"]),
        "max_daily_loss": float(row["max_daily_loss"]),
        "apply_india_costs": bool(row["apply_india_costs"]),
        "created_at": row["created_at"],
    }


def _fill_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "session_id": row["session_id"],
        "symbol": row["symbol"],
        "quote_date": row["quote_date"],
        "order_id": int(row["order_id"]) if row["order_id"] is not None else None,
        "model": row["model"],
        "model_version": row["model_version"],
        "forecast_as_of": row["forecast_as_of"],
        "fill_date": row["fill_date"],
    }


TRAINER = default_trainer
