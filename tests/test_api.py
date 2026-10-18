"""FastAPI endpoint tests without loading real TensorFlow weights."""

from __future__ import annotations

from tests.conftest import RELIANCE_CONFIDENCE, WINDOW


def test_canonicalize_reliance_variants(client):
    for symbol in ("RELIANCE", "reliance.ns", "RELIANCE.NS"):
        r = client.get("/chart", params={"symbol": symbol})
        assert r.status_code == 200
        body = r.json()
        assert body["symbol"] == "RELIANCE"
        assert body["yahoo_symbol"] == "RELIANCE.NS"


def test_unknown_symbol_404(client):
    r = client.get("/predict", params={"symbol": "NOTAREALTICKER"})
    assert r.status_code == 404
    assert "Unknown symbol" in r.json()["detail"]


def test_short_data_422(client):
    r = client.get("/predict", params={"symbol": "WIPRO"})
    assert r.status_code == 422
    assert "Not enough data" in r.json()["detail"]


def test_chart_returns_sixty_points(client):
    r = client.get("/chart", params={"symbol": "RELIANCE"})
    assert r.status_code == 200
    chart = r.json()["chart_data"]
    assert len(chart) == WINDOW
    assert "date" in chart[0] and "price" in chart[0]


def test_realtime_stable(client):
    first = client.get("/realtime", params={"symbol": "RELIANCE"})
    second = client.get("/realtime", params={"symbol": "RELIANCE"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["currency"] == "INR"
    assert "change" in body and "change_percent" in body


def test_predict_confidence_from_metrics(client):
    r = client.get("/predict", params={"symbol": "RELIANCE"})
    assert r.status_code == 200
    body = r.json()
    assert body["confidence"] == RELIANCE_CONFIDENCE
    assert body["currency"] == "INR"
    assert body["symbol"] == "RELIANCE"
    assert isinstance(body["predicted_price"], float)


def test_symbols_list_length(client):
    r = client.get("/symbols")
    assert r.status_code == 200
    symbols = r.json()["symbols"]
    assert len(symbols) == 50
