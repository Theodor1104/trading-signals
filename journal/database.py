"""
SQLite database for trading journal
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DB_PATH


class JournalDB:
    """SQLite database manager for trading journal"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    market TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    notes TEXT,
                    tags TEXT,
                    strategy TEXT,
                    pnl REAL,
                    pnl_percent REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    starting_balance REAL,
                    ending_balance REAL,
                    trades_count INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    total_pnl REAL,
                    notes TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (trade_id) REFERENCES trades(id)
                )
            """)

            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        market: str,
        timestamp: datetime = None,
        notes: str = "",
        tags: str = "",
        strategy: str = "",
        pnl: float = None,
        pnl_percent: float = None
    ) -> int:
        """Add a trade to the journal"""
        timestamp = timestamp or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (
                    order_id, symbol, side, quantity, price, market,
                    timestamp, notes, tags, strategy, pnl, pnl_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, symbol, side, quantity, price, market,
                timestamp.isoformat(), notes, tags, strategy, pnl, pnl_percent
            ))
            conn.commit()
            return cursor.lastrowid

    def get_trade(self, trade_id: int) -> Optional[dict]:
        """Get a single trade by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM trades WHERE id = ?", (trade_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_trades(
        self,
        symbol: str = None,
        market: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> list[dict]:
        """Get trades with optional filters"""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if market:
            query += " AND market = ?"
            params.append(market)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def update_trade(self, trade_id: int, **kwargs):
        """Update trade fields"""
        valid_fields = {
            "notes", "tags", "strategy", "pnl", "pnl_percent"
        }

        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [trade_id]

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE trades SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()

    def add_daily_stats(
        self,
        date: str,
        starting_balance: float,
        ending_balance: float,
        trades_count: int,
        winning_trades: int,
        losing_trades: int,
        total_pnl: float,
        notes: str = ""
    ):
        """Add or update daily statistics"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_stats (
                    date, starting_balance, ending_balance, trades_count,
                    winning_trades, losing_trades, total_pnl, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date, starting_balance, ending_balance, trades_count,
                winning_trades, losing_trades, total_pnl, notes
            ))
            conn.commit()

    def get_daily_stats(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> list[dict]:
        """Get daily statistics"""
        query = "SELECT * FROM daily_stats WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def add_note(self, content: str, trade_id: int = None) -> int:
        """Add a journal note"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO notes (trade_id, timestamp, content)
                VALUES (?, ?, ?)
            """, (trade_id, datetime.now().isoformat(), content))
            conn.commit()
            return cursor.lastrowid

    def get_stats_summary(self) -> dict:
        """Get overall trading statistics"""
        with self._get_connection() as conn:
            # Total trades
            total = conn.execute(
                "SELECT COUNT(*) as count FROM trades"
            ).fetchone()["count"]

            # Winning/losing trades
            buy_trades = conn.execute("""
                SELECT COUNT(*) as count FROM trades WHERE side = 'buy'
            """).fetchone()["count"]

            sell_trades = conn.execute("""
                SELECT COUNT(*) as count FROM trades WHERE side = 'sell'
            """).fetchone()["count"]

            # Total P&L
            pnl_result = conn.execute("""
                SELECT SUM(pnl) as total_pnl FROM trades WHERE pnl IS NOT NULL
            """).fetchone()
            total_pnl = pnl_result["total_pnl"] or 0

            return {
                "total_trades": total,
                "buy_trades": buy_trades,
                "sell_trades": sell_trades,
                "total_pnl": total_pnl,
            }
