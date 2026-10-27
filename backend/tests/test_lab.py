"""Paper lab: one job, an independent gate, and a paper session.

No Yahoo, no Keras, no broker. The published LSTM and LightGBM claims fail the gate.
"""

from __future__ import annotations

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


def test_side_directory_does_not_touch_live_artifacts(tmp_path):
    with pytest.raises(RuntimeError, match="backend/artifacts"):
        assert_side_directory(REPO / "backend" / "artifacts")
    with pytest.raises(RuntimeError, match="champion_lgbm.txt"):
        assert_side_directory(REPO / "backend" / "models")
    before = protected_snapshot()
    side = tmp_path / "run"
    default_trainer("lstm_returns", side, {}, lambda _message: None, JobControl(30))
    assert (side / "metrics.json").exists()
    assert list(side.glob("champion_lgbm.txt")) == []
    assert protected_snapshot() == before
    status, reason, _recomputed = verify_metrics(__import__("json").loads((side / "metrics.json").read_text()))
    assert status == "rejected"
    assert reason == "mae_log_return 0.012052 does not beat naive MAE 0.011988"


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
