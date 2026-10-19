"""FastAPI smoke tests with mocked market data and predictor."""

from __future__ import annotations

from tests.conftest import api_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["model"] is True


def test_market_overview(client):
    response = client.get("/api/market/overview")
    assert response.status_code == 200
    body = response.json()
    assert len(body["stocks"]) > 0
    assert body["stocks"][0]["prediction"]["signal"] == "HOLD"
    assert body["model"]["window"] == 60


def test_market_globals(client):
    response = client.get("/api/market/globals")
    assert response.status_code == 200
    series = response.json()["series"]
    assert len(series) > 0
    assert "ticker" in series[0] and "price" in series[0]


def test_history_success(client):
    response = client.get("/api/market/history/RELIANCE?period=1y")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "RELIANCE"
    assert len(body["bars"]) == 80
    assert body["quote"]["price"] == 1000.0


def test_history_unknown_symbol(client):
    response = client.get("/api/market/history/NOTREAL?period=1y")
    assert response.status_code == 404


def test_history_invalid_period(client):
    response = client.get("/api/market/history/RELIANCE?period=3y")
    assert response.status_code == 400


def test_predict_equity(client):
    response = client.get("/api/predict/TCS")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "TCS"
    assert body["signal"] == "HOLD"
    assert body["model"]["directional_accuracy"] == 0.482


def test_predict_unknown_symbol(client):
    response = client.get("/api/predict/NIFTY")
    assert response.status_code == 404


def test_portfolio_starting_cash(client):
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert body["cash"] == 1_000_000.0
    assert body["positions"] == []


def test_order_buy_and_portfolio(client):
    buy = client.post("/api/orders", json={"symbol": "RELIANCE", "side": "BUY", "qty": 2})
    assert buy.status_code == 200
    order = buy.json()
    assert order["side"] == "BUY"
    assert order["qty"] == 2
    assert order["ticker"] == "RELIANCE"

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["cash"] == 1_000_000.0 - 2000.0
    assert len(portfolio["positions"]) == 1

    orders = client.get("/api/orders").json()["orders"]
    assert len(orders) == 1


def test_order_rejected_insufficient_cash(tmp_path):
    with api_client(tmp_path, close=1_000_000.0) as client:
        response = client.post(
            "/api/orders",
            json={"symbol": "RELIANCE", "side": "BUY", "qty": 2000},
        )
        assert response.status_code == 400
        assert "Not enough cash" in response.json()["detail"]


def test_order_rejected_insufficient_shares(client):
    client.post("/api/orders", json={"symbol": "INFY", "side": "BUY", "qty": 1})
    response = client.post("/api/orders", json={"symbol": "INFY", "side": "SELL", "qty": 5})
    assert response.status_code == 400
    assert "Not enough shares" in response.json()["detail"]


def test_order_rejected_non_equity(client):
    response = client.post("/api/orders", json={"symbol": "NIFTY", "side": "BUY", "qty": 1})
    assert response.status_code == 400
