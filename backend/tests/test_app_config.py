import os

from app_config import cors_origins, market_data_provider, public_config


def test_market_data_provider_defaults_yahoo():
    os.environ.pop("MARKET_DATA_PROVIDER", None)
    assert market_data_provider() == "yahoo"


def test_public_config_shape():
    cfg = public_config()
    assert cfg["market_data_provider"] in {"yahoo", "nse_csv"}
    assert "market_data_label" in cfg
    assert "model_card_url" in cfg


def test_cors_origins_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://desk.example.com,http://localhost:3000")
    assert cors_origins() == ["https://desk.example.com", "http://localhost:3000"]
