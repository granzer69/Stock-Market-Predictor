from data_providers import LicensedIndiaDailyProvider


def test_licensed_provider_not_implemented():
    provider = LicensedIndiaDailyProvider()
    try:
        provider.fetch(["RELIANCE.NS"], "1y")
        assert False, "expected NotImplementedError"
    except NotImplementedError as err:
        assert "Licensed" in str(err)
