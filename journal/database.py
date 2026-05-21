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

            # Watchlist table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    notes TEXT,
                    UNIQUE(symbol, market)
                )
            """)

            # Holdings/Portfolio table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    purchase_date TEXT NOT NULL,
                    notes TEXT
                )
            """)

            # Signal history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    score REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    price_5d_later REAL,
                    result TEXT
                )
            """)

            # Backtest results table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    period TEXT NOT NULL,
                    total_return REAL,
                    win_rate REAL,
                    sharpe REAL,
                    max_drawdown REAL,
                    trades_json TEXT,
                    equity_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # User settings table (for notifications)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    value REAL NOT NULL,
                    active INTEGER DEFAULT 1,
                    triggered INTEGER DEFAULT 0,
                    triggered_at TEXT,
                    created_at TEXT NOT NULL
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

    # ===== WATCHLIST METHODS =====

    def add_to_watchlist(self, symbol: str, market: str, notes: str = "") -> bool:
        """Add symbol to watchlist"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO watchlist (symbol, market, added_at, notes)
                    VALUES (?, ?, ?, ?)
                """, (symbol, market, datetime.now().isoformat(), notes))
                conn.commit()
                return True
        except:
            return False

    def remove_from_watchlist(self, symbol: str, market: str) -> bool:
        """Remove symbol from watchlist"""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM watchlist WHERE symbol = ? AND market = ?",
                (symbol, market)
            )
            conn.commit()
            return True

    def get_watchlist(self, market: str = None) -> list[dict]:
        """Get all watchlist items"""
        query = "SELECT * FROM watchlist"
        params = []
        if market:
            query += " WHERE market = ?"
            params.append(market)
        query += " ORDER BY added_at DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ===== HOLDINGS/PORTFOLIO METHODS =====

    def add_holding(self, symbol: str, market: str, quantity: float,
                    avg_price: float, purchase_date: str = None, notes: str = "") -> int:
        """Add a holding to portfolio"""
        purchase_date = purchase_date or datetime.now().strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO holdings (symbol, market, quantity, avg_price, purchase_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, market, quantity, avg_price, purchase_date, notes))
            conn.commit()
            return cursor.lastrowid

    def update_holding(self, holding_id: int, quantity: float = None,
                       avg_price: float = None, notes: str = None):
        """Update a holding"""
        updates = []
        params = []
        if quantity is not None:
            updates.append("quantity = ?")
            params.append(quantity)
        if avg_price is not None:
            updates.append("avg_price = ?")
            params.append(avg_price)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if updates:
            params.append(holding_id)
            with self._get_connection() as conn:
                conn.execute(
                    f"UPDATE holdings SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()

    def remove_holding(self, holding_id: int):
        """Remove a holding"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
            conn.commit()

    def get_holdings(self, market: str = None) -> list[dict]:
        """Get all holdings"""
        query = "SELECT * FROM holdings"
        params = []
        if market:
            query += " WHERE market = ?"
            params.append(market)
        query += " ORDER BY purchase_date DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ===== SIGNAL HISTORY METHODS =====

    def log_signal(self, symbol: str, market: str, signal: str,
                   score: float, price: float) -> int:
        """Log a signal to history"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO signal_history (symbol, market, signal, score, price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, market, signal, score, price, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def update_signal_result(self, signal_id: int, price_5d_later: float, result: str):
        """Update signal with 5-day result"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE signal_history SET price_5d_later = ?, result = ?
                WHERE id = ?
            """, (price_5d_later, result, signal_id))
            conn.commit()

    def get_signal_history(self, symbol: str = None, limit: int = 100) -> list[dict]:
        """Get signal history"""
        query = "SELECT * FROM signal_history"
        params = []
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_signal_accuracy(self) -> dict:
        """Calculate signal accuracy"""
        with self._get_connection() as conn:
            # BUY accuracy
            buy_total = conn.execute(
                "SELECT COUNT(*) as c FROM signal_history WHERE signal = 'BUY' AND result IS NOT NULL"
            ).fetchone()["c"]
            buy_correct = conn.execute(
                "SELECT COUNT(*) as c FROM signal_history WHERE signal = 'BUY' AND result = 'correct'"
            ).fetchone()["c"]

            # SELL accuracy
            sell_total = conn.execute(
                "SELECT COUNT(*) as c FROM signal_history WHERE signal = 'SELL' AND result IS NOT NULL"
            ).fetchone()["c"]
            sell_correct = conn.execute(
                "SELECT COUNT(*) as c FROM signal_history WHERE signal = 'SELL' AND result = 'correct'"
            ).fetchone()["c"]

            return {
                "buy_accuracy": (buy_correct / buy_total * 100) if buy_total > 0 else 0,
                "buy_total": buy_total,
                "buy_correct": buy_correct,
                "sell_accuracy": (sell_correct / sell_total * 100) if sell_total > 0 else 0,
                "sell_total": sell_total,
                "sell_correct": sell_correct,
            }

    # ===== BACKTEST METHODS =====

    def save_backtest(self, symbol: str, strategy: str, period: str,
                      total_return: float, win_rate: float, sharpe: float,
                      max_drawdown: float, trades_json: str, equity_json: str) -> int:
        """Save backtest results"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO backtest_results
                (symbol, strategy, period, total_return, win_rate, sharpe, max_drawdown, trades_json, equity_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, strategy, period, total_return, win_rate, sharpe,
                  max_drawdown, trades_json, equity_json, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def get_backtests(self, symbol: str = None, limit: int = 20) -> list[dict]:
        """Get backtest history"""
        query = "SELECT * FROM backtest_results"
        params = []
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ===== USER SETTINGS METHODS =====

    def set_setting(self, key: str, value: str):
        """Set a user setting"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)
            """, (key, value))
            conn.commit()

    def get_setting(self, key: str, default: str = None) -> str:
        """Get a user setting"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def get_all_settings(self) -> dict:
        """Get all user settings"""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM user_settings").fetchall()
            return {row["key"]: row["value"] for row in rows}

    # ===== ALERTS METHODS =====

    def add_alert(self, symbol: str, market: str, alert_type: str,
                  condition: str, value: float) -> int:
        """Add an alert"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO alerts (symbol, market, alert_type, condition, value, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, market, alert_type, condition, value, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def remove_alert(self, alert_id: int):
        """Remove an alert"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
            conn.commit()

    def get_alerts(self, active_only: bool = True) -> list[dict]:
        """Get all alerts"""
        query = "SELECT * FROM alerts"
        if active_only:
            query += " WHERE active = 1 AND triggered = 0"
        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def trigger_alert(self, alert_id: int):
        """Mark alert as triggered"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE alerts SET triggered = 1, triggered_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), alert_id))
            conn.commit()

    def get_triggered_alerts(self, limit: int = 50) -> list[dict]:
        """Get triggered alerts history"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM alerts WHERE triggered = 1
                ORDER BY triggered_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
