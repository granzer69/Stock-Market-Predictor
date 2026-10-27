"""Paper lab: one job, an independent gate, and a paper session.

No Yahoo, no Keras, no broker. The published LSTM and LightGBM claims fail the gate.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import pytest

import lab as lab_jobs
from lab import (
    JobControl,
    assert_side_directory,
    default_trainer,
    passing_tail_metrics,
    protected_snapshot,
    stored_claim_metrics,
    verify_metrics,
    write_metrics_file,
)

REPO = Path(__file__).resolve().parents[2]


def _wait_job(client, job_id: str, terminal: set[str] | None = None) -> dict:
    terminal = terminal or {"verified", "rejected", "canceled", "approved"}
    last = None
    for _ in range(80):
        body = client.get("/api/lab/jobs").json()
        last = next(job for job in body["jobs"] if job["id"] == job_id)
        if last["status"] in terminal:
            return last
        time.sleep(0.05)
    raise AssertionError(last)


def _drive(client, monkeypatch, metrics: dict) -> dict:
    done = threading.Event()

    def train(candidate_id, side_dir, config, log, control):
        write_metrics_file(side_dir, metrics)
        done.set()

    monkeypatch.setattr(lab_jobs, "TRAINER", train)
    started = client.post(
        "/api/lab/jobs",
        json={"action": "start", "candidate_id": metrics["candidate_id"]},
    )
    assert started.status_code == 200, started.text
    assert done.wait(2)
    return _wait_job(client, started.json()["id"])


def _approve_passing(client, monkeypatch) -> dict:
    job = _drive(client, monkeypatch, passing_tail_metrics())
    assert job["status"] == "verified", job
    approved = client.post(f"/api/lab/jobs/{job['id']}/approve")
    assert approved.status_code == 200, approved.text
    opened = client.post(
        "/api/lab/session",
        json={"max_names": 3, "max_notional": 100000, "max_daily_loss": 50000, "apply_india_costs": False},
    )
    assert opened.status_code == 200, opened.text
    return job


def test_second_start_while_running_is_409(client, monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def block(candidate_id, side_dir, config, log, control):
        entered.set()
        while not release.is_set():
            if not control.wait_if_paused():
                return
            release.wait(0.05)

    monkeypatch.setattr(lab_jobs, "TRAINER", block)
    try:
        first = client.post("/api/lab/jobs", json={"action": "start", "candidate_id": "lstm_returns"})
        assert first.status_code == 200, first.text
        assert entered.wait(2)
        second = client.post("/api/lab/jobs", json={"action": "start", "candidate_id": "lightgbm"})
        assert second.status_code == 409
        assert second.json()["detail"] == "a lab job is already running"
        paused = client.post("/api/lab/jobs", json={"action": "pause", "job_id": first.json()["id"]})
        assert paused.status_code == 200
        assert paused.json()["status"] == "paused"
        while_paused = client.post("/api/lab/jobs", json={"action": "start", "candidate_id": "lightgbm"})
        assert while_paused.status_code == 409
        resumed = client.post("/api/lab/jobs", json={"action": "resume", "job_id": first.json()["id"]})
        assert resumed.status_code == 200
        assert resumed.json()["status"] == "running"
    finally:
        release.set()


def test_naive_mae_failure_is_rejected_and_cannot_be_approved(client, monkeypatch):
    job = _drive(client, monkeypatch, stored_claim_metrics("lstm_returns"))
    assert job["status"] == "rejected"
    assert job["rejection_reason"] == "mae_log_return 0.012052 does not beat naive MAE 0.011988"
    approved = client.post(f"/api/lab/jobs/{job['id']}/approve")
    assert approved.status_code == 409
    assert "cannot be approved" in approved.json()["detail"]


def test_published_lightgbm_and_same_return_momentum_are_rejected():
    status, reason, _recomputed = verify_metrics(stored_claim_metrics("lightgbm"))
    assert status == "rejected"
    assert reason == "directional_accuracy 0.4707 does not beat the naive baseline 0.5"

    momentum = passing_tail_metrics()
    momentum["momentum_directional_accuracy"] = 1.0
    status, reason, recomputed = verify_metrics(momentum)
    assert status == "rejected"
    assert reason == "momentum directional accuracy is 1.0 on the same return"
    assert recomputed["momentum_basis"] == "lagged"
    assert recomputed["momentum_directional_accuracy"] != 1.0

    status, reason, _recomputed = verify_metrics(None)
    assert status == "rejected"
    assert reason == "metrics file missing"

    shuffled = passing_tail_metrics()
    shuffled["training_shuffle"] = True
    status, reason, _recomputed = verify_metrics(shuffled)
    assert status == "rejected"
    assert "holdout is not a tail split" in reason


def test_stale_quote_writes_no_order(client, monkeypatch):
    _approve_passing(client, monkeypatch)
    before = client.get("/api/orders").json()["orders"]
    tick = client.post(
        "/api/lab/session/tick",
        json={
            "symbol": "RELIANCE.NS",
            "side": "BUY",
            "qty": 1,
            "quote": {"price": 1000, "as_of": "2026-10-27", "stale": True},
            "forecast_as_of": "2026-10-16",
        },
    )
    assert tick.status_code == 409
    assert tick.json()["detail"] == "stale quote"
    after = client.get("/api/orders").json()["orders"]
    assert after == before
    session = client.get("/api/lab/jobs").json()["session"]
    assert session["status"] == "halted"
    assert session["halt_reason"] == "stale quote"
    assert client.get("/api/lab/portfolio").json()["fills"] == []


def test_two_ticks_on_the_same_quote_date_produce_one_fill(client, monkeypatch):
    job = _approve_passing(client, monkeypatch)
    payload = {
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "qty": 1,
        "quote": {"price": 1000, "as_of": "2026-10-27", "stale": False},
        "forecast_as_of": "2026-10-16",
    }
    first = client.post("/api/lab/session/tick", json=payload)
    assert first.status_code == 200, first.text
    second = client.post("/api/lab/session/tick", json=payload)
    assert second.status_code == 409
    assert "duplicate" in second.json()["detail"]
    orders = client.get("/api/orders").json()["orders"]
    assert len(orders) == 1
    fills = client.get("/api/lab/portfolio").json()["fills"]
    assert len(fills) == 1
    fill = fills[0]
    assert fill["model"] == "lstm_returns"
    assert fill["model_version"] == job["id"]
    assert fill["forecast_as_of"] == "2026-10-16"
    assert fill["fill_date"] == "2026-10-27"
    snapshot = client.get("/api/lab/portfolio").json()["snapshot"]
    assert snapshot["cash"] < snapshot["starting_cash"]


def test_rollback_restores_the_previous_approved_job(client, monkeypatch):
    before = protected_snapshot()
    first = _drive(client, monkeypatch, passing_tail_metrics())
    assert client.post(f"/api/lab/jobs/{first['id']}/approve").status_code == 200
    second = _drive(client, monkeypatch, passing_tail_metrics())
    assert client.post(f"/api/lab/jobs/{second['id']}/approve").status_code == 200
    rolled = client.post(f"/api/lab/jobs/{second['id']}/rollback")
    assert rolled.status_code == 200, rolled.text
    body = rolled.json()
    assert body["approved_job_id"] == first["id"]
    assert protected_snapshot() == before


def _empty_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (tmp_path / "cache", tmp_path / "nse", tmp_path / "panel.csv")


def _write_bars(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "Date,Open,High,Low,Close,Volume\n2024-01-02,10,11,9,10,100\n2024-01-03,10,11,9,11,100\n",
        encoding="utf-8",
    )


def _forbid_yahoo(monkeypatch) -> dict:
    called = {"yahoo": 0, "train": 0}

    def yahoo(*_args, **_kwargs):
        called["yahoo"] += 1
        raise AssertionError("yahoo contacted")

    monkeypatch.setattr("market_data.yfinance_fetcher", yahoo)
    return called


def test_start_refuses_when_local_bars_are_missing(client, monkeypatch, tmp_path):
    monkeypatch.setattr(lab_jobs, "disk_bar_sources", lambda: _empty_sources(tmp_path))
    called = _forbid_yahoo(monkeypatch)

    def train_and_save(*_args, **_kwargs):
        called["train"] += 1
        raise AssertionError("train_and_save")

    monkeypatch.setattr("train_lstm.train_and_save", train_and_save)
    before = protected_snapshot()
    started = client.post("/api/lab/jobs", json={"action": "start", "candidate_id": "lstm_returns"})
    assert started.status_code == 200, started.text
    job = _wait_job(client, started.json()["id"])
    assert job["status"] == "rejected"
    assert job["rejection_reason"] == "no local bars; train not started"
    assert job["metrics"] is None
    assert "0.012052" not in (job["log_tail"] or "")
    assert called == {"yahoo": 0, "train": 0}
    assert protected_snapshot() == before


def test_start_trains_side_directory_when_local_bars_exist(client, monkeypatch, tmp_path):
    nse = tmp_path / "nse"
    _write_bars(nse / "ADANIENT.NS.csv")
    _write_bars(nse / "ADANIPORTS.NS.csv")
    _write_bars(nse / "APOLLOHOSP.NS.csv")
    monkeypatch.setattr(lab_jobs, "disk_bar_sources", lambda: (tmp_path / "cache", nse, tmp_path / "panel.csv"))
    monkeypatch.setenv("LAB_SYMBOL_CAP", "2")
    monkeypatch.setenv("LSTM_EPOCHS", "3")
    called = _forbid_yahoo(monkeypatch)
    seen: dict = {}

    def train_and_save(frames, artifact_dir=None):
        called["train"] += 1
        seen["symbols"] = list(frames)
        seen["artifact_dir"] = str(artifact_dir)
        seen["epochs"] = os.environ.get("LSTM_EPOCHS")
        write_metrics_file(
            Path(artifact_dir),
            {
                "holdout_fraction": 0.2,
                "training_shuffle": False,
                "mae_log_return": 0.02,
                "naive_mae_log_return": 0.01,
            },
        )
        return {}

    monkeypatch.setattr("train_lstm.train_and_save", train_and_save)
    before = protected_snapshot()
    started = client.post("/api/lab/jobs", json={"action": "start", "candidate_id": "lstm_returns"})
    assert started.status_code == 200, started.text
    job = _wait_job(client, started.json()["id"])
    assert called["yahoo"] == 0
    assert called["train"] == 1
    assert seen["symbols"] == ["ADANIENT.NS", "ADANIPORTS.NS"]
    assert seen["epochs"] == "3"
    artifact_dir = Path(seen["artifact_dir"]).resolve()
    assert artifact_dir.name == job["id"]
    assert artifact_dir != (REPO / "backend" / "artifacts").resolve()
    assert (REPO / "backend" / "artifacts").resolve() not in artifact_dir.parents
    assert not (artifact_dir / "champion_lgbm.txt").exists()
    assert job["status"] == "rejected"
    assert job["rejection_reason"] == "mae_log_return 0.020000 does not beat naive MAE 0.010000"
    assert "symbol_cap=2" in job["log_tail"]
    assert "LSTM_EPOCHS=3" in job["log_tail"]
    assert protected_snapshot() == before


def test_side_directory_does_not_touch_live_artifacts(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="backend/artifacts"):
        assert_side_directory(REPO / "backend" / "artifacts")
    with pytest.raises(RuntimeError, match="champion_lgbm.txt"):
        assert_side_directory(REPO / "backend" / "models")
    monkeypatch.setattr(lab_jobs, "disk_bar_sources", lambda: _empty_sources(tmp_path))
    before = protected_snapshot()
    side = tmp_path / "run"
    with pytest.raises(lab_jobs.TrainNotStarted, match="no local bars; train not started"):
        default_trainer("lstm_returns", side, {}, lambda _message: None, JobControl(30))
    assert not (side / "metrics.json").exists()
    assert list(side.glob("champion_lgbm.txt")) == []
    assert protected_snapshot() == before


def test_lab_modules_do_not_import_a_broker_or_a_queue():
    paths = [
        REPO / "backend" / "lab.py",
        REPO / "frontend" / "app" / "lab" / "page.tsx",
    ]
    forbidden = (
        "kiteconnect",
        "smartapi",
        "upstox",
        "aliceblue",
        "angelbroking",
        "broker_api",
        "broker_secret",
        "kite_api",
        "celery",
        "redis",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token}"
