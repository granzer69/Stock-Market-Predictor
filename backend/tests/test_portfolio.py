import pytest

from portfolio import STARTING_CASH, PaperBook


def test_buy_rejected_when_cash_is_short(tmp_path):
    book = PaperBook(tmp_path / "book.db")
    with pytest.raises(ValueError, match="Not enough cash"):
        book.place_order("RELIANCE.NS", "BUY", 2, STARTING_CASH)
    snapshot = book.snapshot()
    assert snapshot["cash"] == STARTING_CASH
    assert snapshot["positions"] == []


def test_sell_rejected_when_shares_are_short(tmp_path):
    book = PaperBook(tmp_path / "book.db")
    book.place_order("TCS.NS", "BUY", 1, 100)
    with pytest.raises(ValueError, match="Not enough shares"):
        book.place_order("TCS.NS", "SELL", 2, 100)
    assert book.positions()[0]["qty"] == 1


def test_average_cost_after_two_buys(tmp_path):
    book = PaperBook(tmp_path / "book.db")
    book.place_order("INFY.NS", "BUY", 10, 100)
    book.place_order("INFY.NS", "BUY", 10, 200)
    position = book.positions()[0]
    assert position["qty"] == 20
    assert position["avg_cost"] == 150

    snapshot = book.snapshot({"INFY.NS": 180})
    assert snapshot["cash"] == STARTING_CASH - 3000
    assert snapshot["unrealized_pnl"] == 600
    assert snapshot["equity"] == STARTING_CASH - 3000 + 3600
