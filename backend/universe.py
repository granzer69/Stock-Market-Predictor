"""Nifty 50 universe and the macro series that sit around it.

Constituents follow the NSE Nifty 50 list in effect for October 2026
(BSE included, Wipro removed, Tata Motors listed as TMPV).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    symbol: str
    ticker: str
    name: str
    sector: str
    unit: str
    kind: str

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "unit": self.unit,
            "kind": self.kind,
        }


def _equity(ticker: str, name: str, sector: str) -> Series:
    return Series(
        symbol=f"{ticker}.NS",
        ticker=ticker,
        name=name,
        sector=sector,
        unit="INR",
        kind="equity",
    )


NIFTY_50: tuple[Series, ...] = (
    _equity("ADANIENT", "Adani Enterprises", "Metals & Mining"),
    _equity("ADANIPORTS", "Adani Ports", "Services"),
    _equity("APOLLOHOSP", "Apollo Hospitals", "Healthcare"),
    _equity("ASIANPAINT", "Asian Paints", "Consumer Durables"),
    _equity("AXISBANK", "Axis Bank", "Financial Services"),
    _equity("BSE", "BSE", "Financial Services"),
    _equity("BAJAJ-AUTO", "Bajaj Auto", "Automobile"),
    _equity("BAJFINANCE", "Bajaj Finance", "Financial Services"),
    _equity("BAJAJFINSV", "Bajaj Finserv", "Financial Services"),
    _equity("BEL", "Bharat Electronics", "Capital Goods"),
    _equity("BHARTIARTL", "Bharti Airtel", "Telecom"),
    _equity("CIPLA", "Cipla", "Healthcare"),
    _equity("COALINDIA", "Coal India", "Energy"),
    _equity("DRREDDY", "Dr. Reddy's Laboratories", "Healthcare"),
    _equity("EICHERMOT", "Eicher Motors", "Automobile"),
    _equity("ETERNAL", "Eternal", "Consumer Services"),
    _equity("GRASIM", "Grasim Industries", "Construction Materials"),
    _equity("HCLTECH", "HCL Technologies", "Information Technology"),
    _equity("HDFCBANK", "HDFC Bank", "Financial Services"),
    _equity("HDFCLIFE", "HDFC Life Insurance", "Financial Services"),
    _equity("HINDALCO", "Hindalco Industries", "Metals & Mining"),
    _equity("HINDUNILVR", "Hindustan Unilever", "FMCG"),
    _equity("ICICIBANK", "ICICI Bank", "Financial Services"),
    _equity("ITC", "ITC", "FMCG"),
    _equity("INFY", "Infosys", "Information Technology"),
    _equity("INDIGO", "InterGlobe Aviation", "Services"),
    _equity("JSWSTEEL", "JSW Steel", "Metals & Mining"),
    _equity("JIOFIN", "Jio Financial Services", "Financial Services"),
    _equity("KOTAKBANK", "Kotak Mahindra Bank", "Financial Services"),
    _equity("LT", "Larsen & Toubro", "Construction"),
    _equity("M&M", "Mahindra & Mahindra", "Automobile"),
    _equity("MARUTI", "Maruti Suzuki", "Automobile"),
    _equity("MAXHEALTH", "Max Healthcare", "Healthcare"),
    _equity("NTPC", "NTPC", "Power"),
    _equity("NESTLEIND", "Nestle India", "FMCG"),
    _equity("ONGC", "ONGC", "Energy"),
    _equity("POWERGRID", "Power Grid", "Power"),
    _equity("RELIANCE", "Reliance Industries", "Energy"),
    _equity("SBILIFE", "SBI Life Insurance", "Financial Services"),
    _equity("SHRIRAMFIN", "Shriram Finance", "Financial Services"),
    _equity("SBIN", "State Bank of India", "Financial Services"),
    _equity("SUNPHARMA", "Sun Pharmaceutical", "Healthcare"),
    _equity("TCS", "Tata Consultancy Services", "Information Technology"),
    _equity("TATACONSUM", "Tata Consumer Products", "FMCG"),
    _equity("TMPV", "Tata Motors Passenger Vehicles", "Automobile"),
    _equity("TATASTEEL", "Tata Steel", "Metals & Mining"),
    _equity("TECHM", "Tech Mahindra", "Information Technology"),
    _equity("TITAN", "Titan Company", "Consumer Durables"),
    _equity("TRENT", "Trent", "Consumer Services"),
    _equity("ULTRACEMCO", "UltraTech Cement", "Construction Materials"),
)

GLOBALS: tuple[Series, ...] = (
    Series("^NSEI", "NIFTY", "Nifty 50", "Index", "pts", "index"),
    Series("^BSESN", "SENSEX", "Sensex", "Index", "pts", "index"),
    Series("^NSEBANK", "BANKNIFTY", "Bank Nifty", "Index", "pts", "index"),
    Series("^INDIAVIX", "INDIAVIX", "India VIX", "Index", "pts", "index"),
    Series("USDINR=X", "USDINR", "USD / INR", "Macro", "INR", "fx"),
    Series("BZ=F", "BRENT", "Brent crude", "Macro", "USD", "commodity"),
    Series("GC=F", "GOLD", "Gold", "Macro", "USD", "commodity"),
    Series("^GSPC", "SPX", "S&P 500", "Macro", "pts", "index"),
    Series("^IXIC", "NASDAQ", "Nasdaq", "Macro", "pts", "index"),
)

ALL_SERIES: tuple[Series, ...] = NIFTY_50 + GLOBALS

BY_SYMBOL: dict[str, Series] = {item.symbol.upper(): item for item in ALL_SERIES}
BY_TICKER: dict[str, Series] = {item.ticker.upper(): item for item in ALL_SERIES}


def resolve(raw: str) -> Series | None:
    if not raw or not raw.strip():
        return None
    key = raw.strip().upper()
    return BY_SYMBOL.get(key) or BY_TICKER.get(key)
