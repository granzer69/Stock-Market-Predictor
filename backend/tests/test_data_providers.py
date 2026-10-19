from data_providers import LicensedIndiaDailyProvider, get_history_provider


def test_get_history_provider_defaults_yahoo():
    provider = get_history_provider()
    assert provider.__class__.__name__ == "YahooHistoryProvider"


def test_bundled_sample_csv_loads():
    provider = LicensedIndiaDailyProvider()
    frames = provider.fetch(["RELIANCE.NS"], "1y")
    assert "RELIANCE.NS" in frames
    assert len(frames["RELIANCE.NS"]) > 60
