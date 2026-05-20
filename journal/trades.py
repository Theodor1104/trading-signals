"""
Trade Journal - Log and analyze trades
"""
from datetime import datetime
from typing import Optional

from trading.orders import Order, OrderStatus
from .database import JournalDB


class TradeJournal:
    """Journal for logging and analyzing trades"""

    def __init__(self):
        self.db = JournalDB()

    def log_trade(
        self,
        order: Order,
        notes: str = "",
        tags: list[str] = None,
        strategy: str = ""
    ) -> int:
        """Log a completed trade"""
        if order.status != OrderStatus.FILLED:
            return -1

        tags_str = ",".join(tags) if tags else ""

        return self.db.add_trade(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.filled_quantity,
            price=order.filled_price,
            market=order.market,
            timestamp=order.filled_at,
            notes=notes or order.notes,
            tags=tags_str,
            strategy=strategy,
        )

    def update_trade_pnl(
        self,
        trade_id: int,
        exit_price: float,
        entry_price: float,
        quantity: float,
        side: str
    ):
        """Update trade P&L after closing position"""
        if side == "buy":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        pnl_percent = ((exit_price / entry_price) - 1) * 100
        if side == "sell":
            pnl_percent = -pnl_percent

        self.db.update_trade(trade_id, pnl=pnl, pnl_percent=pnl_percent)

    def add_note(self, content: str, trade_id: int = None):
        """Add a journal note"""
        self.db.add_note(content, trade_id)

    def get_recent_trades(self, limit: int = 20) -> list[dict]:
        """Get recent trades"""
        return self.db.get_trades(limit=limit)

    def get_trades_by_symbol(self, symbol: str) -> list[dict]:
        """Get all trades for a symbol"""
        return self.db.get_trades(symbol=symbol)

    def get_trades_by_date(
        self,
        start_date: datetime,
        end_date: datetime = None
    ) -> list[dict]:
        """Get trades within date range"""
        end_date = end_date or datetime.now()
        return self.db.get_trades(start_date=start_date, end_date=end_date)

    def get_performance_summary(self) -> dict:
        """Get trading performance summary"""
        stats = self.db.get_stats_summary()
        trades = self.db.get_trades(limit=1000)

        # Calculate win rate
        winning = len([t for t in trades if (t.get("pnl") or 0) > 0])
        losing = len([t for t in trades if (t.get("pnl") or 0) < 0])

        win_rate = (winning / len(trades) * 100) if trades else 0

        # Calculate average P&L
        pnls = [t["pnl"] for t in trades if t.get("pnl") is not None]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0

        # Best and worst trades
        if pnls:
            best_pnl = max(pnls)
            worst_pnl = min(pnls)
        else:
            best_pnl = worst_pnl = 0

        return {
            **stats,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "best_trade_pnl": best_pnl,
            "worst_trade_pnl": worst_pnl,
        }

    def get_strategy_performance(self) -> dict[str, dict]:
        """Get performance by strategy"""
        trades = self.db.get_trades(limit=1000)

        strategies = {}
        for trade in trades:
            strategy = trade.get("strategy") or "Unknown"
            if strategy not in strategies:
                strategies[strategy] = {
                    "trades": 0,
                    "winning": 0,
                    "total_pnl": 0,
                    "pnls": []
                }

            strategies[strategy]["trades"] += 1
            pnl = trade.get("pnl") or 0
            strategies[strategy]["total_pnl"] += pnl
            strategies[strategy]["pnls"].append(pnl)
            if pnl > 0:
                strategies[strategy]["winning"] += 1

        # Calculate metrics
        for strategy in strategies:
            data = strategies[strategy]
            data["win_rate"] = (
                data["winning"] / data["trades"] * 100
                if data["trades"] > 0 else 0
            )
            data["avg_pnl"] = (
                data["total_pnl"] / data["trades"]
                if data["trades"] > 0 else 0
            )
            del data["pnls"]  # Clean up

        return strategies
