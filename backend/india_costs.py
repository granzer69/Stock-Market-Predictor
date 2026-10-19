"""Simplified Indian equity delivery cost model for backtests (not used by paper book)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndiaEquityCostParams:
    """Retail-oriented defaults; override per broker/exchange circular."""

    brokerage_rate: float = 0.0  # fraction of turnover; paper desk uses 0
    brokerage_cap_inr: float = 20.0
    stt_sell_rate: float = 0.001  # 0.1% on sell turnover (delivery, illustrative)
    exchange_charge_rate: float = 0.0000345
    sebi_rate: float = 0.000001
    stamp_duty_buy_rate: float = 0.00015
    gst_on_brokerage: float = 0.18


def delivery_turnover_cost_inr(side: str, notional_inr: float, params: IndiaEquityCostParams | None = None) -> float:
    """Total friction in INR for one delivery leg at ``notional_inr`` (qty * price)."""
    if notional_inr <= 0:
        return 0.0
    p = params or IndiaEquityCostParams()
    side_u = side.upper()
    if side_u not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    brokerage = min(notional_inr * p.brokerage_rate, p.brokerage_cap_inr)
    brokerage_gst = brokerage * p.gst_on_brokerage
    exchange = notional_inr * (p.exchange_charge_rate + p.sebi_rate)
    stamp = notional_inr * p.stamp_duty_buy_rate if side_u == "BUY" else 0.0
    stt = notional_inr * p.stt_sell_rate if side_u == "SELL" else 0.0
    return brokerage + brokerage_gst + exchange + stamp + stt
