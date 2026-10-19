from india_costs import IndiaEquityCostParams, delivery_turnover_cost_inr


def test_sell_stt_exceeds_buy_stamp():
    notional = 100_000.0
    buy = delivery_turnover_cost_inr("BUY", notional)
    sell = delivery_turnover_cost_inr("SELL", notional)
    assert buy > 0 and sell > 0
    assert sell > buy


def test_zero_notional_is_free():
    assert delivery_turnover_cost_inr("BUY", 0.0) == 0.0
