"""SQLite paper book. Fills are whole shares at a caller-supplied price."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app_config import paper_apply_india_costs
from india_costs import delivery_turnover_cost_inr

STARTING_CASH = 1_000_000.0


def _money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperBook:
    def __init__(self, path: Path | str):
        self.path = str(path)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS account (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        cash REAL NOT NULL,
                        realized_pnl REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS positions (
                        symbol TEXT PRIMARY KEY,
                        qty INTEGER NOT NULL,
                        avg_cost REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        qty INTEGER NOT NULL,
                        price REAL NOT NULL,
                        notional REAL NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        equity REAL NOT NULL,
                        cash REAL NOT NULL
                    );
                    """
                )
                row = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO account (id, cash, realized_pnl) VALUES (1, ?, 0)",
                        (STARTING_CASH,),
                    )
                    conn.execute(
                        "INSERT INTO snapshots (created_at, equity, cash) VALUES (?, ?, ?)",
                        (_now(), STARTING_CASH, STARTING_CASH),
                    )
                conn.commit()
            finally:
                conn.close()

    def place_order(self, symbol: str, side: str, qty: int, price: float) -> dict:
        side = side.strip().upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("qty must be a positive whole number of shares")
        if price <= 0:
            raise ValueError("price must be positive")
        notional = _money(qty * float(price))
        fill_price = _money(price)

        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN")
                account = conn.execute("SELECT cash, realized_pnl FROM account WHERE id = 1").fetchone()
                position = conn.execute(
                    "SELECT qty, avg_cost FROM positions WHERE symbol = ?",
                    (symbol,),
                ).fetchone()
                cash = float(account["cash"])
                realized = float(account["realized_pnl"])
                old_qty = int(position["qty"]) if position else 0
                old_avg = float(position["avg_cost"]) if position else 0.0

                if side == "BUY":
                    friction = (
                        delivery_turnover_cost_inr("BUY", notional) if paper_apply_india_costs() else 0.0
                    )
                    if notional + friction > cash + 1e-6:
                        raise ValueError("Not enough cash for this order")
                    new_qty = old_qty + qty
                    new_avg = _money(((old_qty * old_avg) + notional) / new_qty)
                    cash = _money(cash - notional - friction)
                    conn.execute(
                        """
                        INSERT INTO positions (symbol, qty, avg_cost) VALUES (?, ?, ?)
                        ON CONFLICT(symbol) DO UPDATE SET qty = excluded.qty, avg_cost = excluded.avg_cost
                        """,
                        (symbol, new_qty, new_avg),
                    )
                else:
                    if qty > old_qty:
                        raise ValueError("Not enough shares to sell")
                    friction = (
                        delivery_turnover_cost_inr("SELL", notional) if paper_apply_india_costs() else 0.0
                    )
                    realized = _money(realized + (fill_price - old_avg) * qty - friction)
                    cash = _money(cash + notional - friction)
                    new_qty = old_qty - qty
                    if new_qty == 0:
                        conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
                    else:
                        conn.execute(
                            "UPDATE positions SET qty = ? WHERE symbol = ?",
                            (new_qty, symbol),
                        )

                conn.execute(
                    "UPDATE account SET cash = ?, realized_pnl = ? WHERE id = 1",
                    (cash, realized),
                )
                created_at = _now()
                cursor = conn.execute(
                    """
                    INSERT INTO orders (symbol, side, qty, price, notional, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, side, qty, fill_price, notional, created_at),
                )
                equity = self._equity_locked(conn, {})
                conn.execute(
                    "INSERT INTO snapshots (created_at, equity, cash) VALUES (?, ?, ?)",
                    (created_at, equity, cash),
                )
                conn.commit()
                return {
                    "id": int(cursor.lastrowid),
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": fill_price,
                    "notional": notional,
                    "created_at": created_at,
                }
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _equity_locked(self, conn: sqlite3.Connection, prices: dict[str, float]) -> float:
        account = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()
        equity = float(account["cash"])
        for row in conn.execute("SELECT symbol, qty, avg_cost FROM positions"):
            mark = float(prices.get(row["symbol"], row["avg_cost"]))
            equity += int(row["qty"]) * mark
        return _money(equity)

    def positions(self) -> list[dict]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT symbol, qty, avg_cost FROM positions ORDER BY symbol"
                ).fetchall()
                return [
                    {"symbol": row["symbol"], "qty": int(row["qty"]), "avg_cost": float(row["avg_cost"])}
                    for row in rows
                ]
            finally:
                conn.close()

    def orders(self, limit: int = 100) -> list[dict]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT id, symbol, side, qty, price, notional, created_at
                    FROM orders ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
                return [
                    {
                        "id": int(row["id"]),
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "qty": int(row["qty"]),
                        "price": float(row["price"]),
                        "notional": float(row["notional"]),
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
            finally:
                conn.close()

    def snapshot(self, prices: dict[str, float] | None = None) -> dict:
        marks = prices or {}
        with self._lock:
            conn = self._connect()
            try:
                account = conn.execute("SELECT cash, realized_pnl FROM account WHERE id = 1").fetchone()
                cash = float(account["cash"])
                realized = float(account["realized_pnl"])
                positions = []
                market_value = 0.0
                unrealized = 0.0
                for row in conn.execute("SELECT symbol, qty, avg_cost FROM positions ORDER BY symbol"):
                    qty = int(row["qty"])
                    avg = float(row["avg_cost"])
                    marked = row["symbol"] in marks
                    last = float(marks[row["symbol"]]) if marked else avg
                    value = _money(qty * last)
                    pnl = _money((last - avg) * qty)
                    market_value += value
                    unrealized += pnl
                    positions.append(
                        {
                            "symbol": row["symbol"],
                            "qty": qty,
                            "avg_cost": avg,
                            "last": last,
                            "market_value": value,
                            "unrealized_pnl": pnl,
                            "stale": not marked,
                        }
                    )
                equity = _money(cash + market_value)
                curve = [
                    {"time": row["created_at"], "equity": float(row["equity"]), "cash": float(row["cash"])}
                    for row in conn.execute(
                        "SELECT created_at, equity, cash FROM snapshots ORDER BY id"
                    )
                ]
                curve.append({"time": _now(), "equity": equity, "cash": cash})
                return {
                    "cash": _money(cash),
                    "starting_cash": STARTING_CASH,
                    "realized_pnl": _money(realized),
                    "unrealized_pnl": _money(unrealized),
                    "market_value": _money(market_value),
                    "equity": equity,
                    "positions": positions,
                    "equity_curve": curve,
                }
            finally:
                conn.close()
