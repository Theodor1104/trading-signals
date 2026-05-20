"""
Paper Trading - Simulated trading with virtual money
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json
from pathlib import Path

from config import DEFAULT_PAPER_BALANCE, BASE_DIR
from data.fetcher import DataFetcher
from .orders import Order, OrderSide, OrderStatus, OrderType


@dataclass
class Position:
    """Represents a position in a symbol"""
    symbol: str
    quantity: float
    avg_price: float
    market: str
    opened_at: datetime = field(default_factory=datetime.now)

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price


@dataclass
class PaperAccount:
    """Paper trading account"""
    balance: float = DEFAULT_PAPER_BALANCE
    starting_balance: float = DEFAULT_PAPER_BALANCE
    positions: dict = field(default_factory=dict)  # symbol -> Position
    orders: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_invested(self) -> float:
        return sum(p.cost_basis for p in self.positions.values())

    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "starting_balance": self.starting_balance,
            "positions": {
                s: {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "market": p.market,
                    "opened_at": p.opened_at.isoformat()
                }
                for s, p in self.positions.items()
            },
            "orders": [o.to_dict() for o in self.orders],
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperAccount":
        account = cls(
            balance=data["balance"],
            starting_balance=data["starting_balance"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
        for symbol, pos_data in data.get("positions", {}).items():
            account.positions[symbol] = Position(
                symbol=pos_data["symbol"],
                quantity=pos_data["quantity"],
                avg_price=pos_data["avg_price"],
                market=pos_data["market"],
                opened_at=datetime.fromisoformat(pos_data["opened_at"])
            )
        account.orders = [Order.from_dict(o) for o in data.get("orders", [])]
        return account


class PaperTrader:
    """Paper trading engine"""

    SAVE_FILE = BASE_DIR / "paper_account.json"

    def __init__(self):
        self.fetcher = DataFetcher()
        self.account = self._load_account()

    def _load_account(self) -> PaperAccount:
        """Load account from file or create new"""
        if self.SAVE_FILE.exists():
            try:
                with open(self.SAVE_FILE) as f:
                    return PaperAccount.from_dict(json.load(f))
            except Exception:
                pass
        return PaperAccount()

    def _save_account(self):
        """Save account to file"""
        with open(self.SAVE_FILE, "w") as f:
            json.dump(self.account.to_dict(), f, indent=2)

    def buy(
        self,
        symbol: str,
        quantity: float,
        market: str = "stocks",
        order_type: OrderType = OrderType.MARKET,
        limit_price: float = None,
        notes: str = ""
    ) -> Order:
        """Place a buy order"""
        # Get current price
        price = self.fetcher.get_price(symbol, market)
        if price is None:
            order = Order(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                market=market,
                notes=notes
            )
            order.status = OrderStatus.REJECTED
            return order

        # Check if we have enough balance
        total_cost = price * quantity
        if total_cost > self.account.balance:
            order = Order(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=order_type,
                market=market,
                notes=notes
            )
            order.status = OrderStatus.REJECTED
            return order

        # Create and fill order
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            market=market,
            notes=notes
        )
        order.fill(price, quantity)

        # Update account
        self.account.balance -= total_cost
        self.account.orders.append(order)

        # Update or create position
        if symbol in self.account.positions:
            pos = self.account.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_price = (pos.cost_basis + total_cost) / total_qty
            pos.quantity = total_qty
        else:
            self.account.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                market=market
            )

        self._save_account()
        return order

    def sell(
        self,
        symbol: str,
        quantity: float,
        market: str = "stocks",
        order_type: OrderType = OrderType.MARKET,
        limit_price: float = None,
        notes: str = ""
    ) -> Order:
        """Place a sell order"""
        # Check if we have the position
        if symbol not in self.account.positions:
            order = Order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=order_type,
                market=market,
                notes=notes
            )
            order.status = OrderStatus.REJECTED
            return order

        pos = self.account.positions[symbol]
        if pos.quantity < quantity:
            order = Order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=order_type,
                market=market,
                notes=notes
            )
            order.status = OrderStatus.REJECTED
            return order

        # Get current price
        price = self.fetcher.get_price(symbol, market)
        if price is None:
            order = Order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=order_type,
                market=market,
                notes=notes
            )
            order.status = OrderStatus.REJECTED
            return order

        # Create and fill order
        order = Order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            market=market,
            notes=notes
        )
        order.fill(price, quantity)

        # Update account
        self.account.balance += price * quantity
        self.account.orders.append(order)

        # Update position
        pos.quantity -= quantity
        if pos.quantity <= 0:
            del self.account.positions[symbol]

        self._save_account()
        return order

    def get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions)"""
        total = self.account.balance

        for symbol, pos in self.account.positions.items():
            price = self.fetcher.get_price(symbol, pos.market)
            if price:
                total += price * pos.quantity

        return total

    def get_pnl(self) -> dict:
        """Get profit/loss summary"""
        portfolio_value = self.get_portfolio_value()
        starting = self.account.starting_balance

        total_pnl = portfolio_value - starting
        pnl_percent = (total_pnl / starting) * 100

        # Calculate position PnL
        position_pnl = {}
        for symbol, pos in self.account.positions.items():
            price = self.fetcher.get_price(symbol, pos.market)
            if price:
                pnl = (price - pos.avg_price) * pos.quantity
                pnl_pct = ((price / pos.avg_price) - 1) * 100
                position_pnl[symbol] = {
                    "pnl": pnl,
                    "pnl_percent": pnl_pct,
                    "current_price": price,
                    "avg_price": pos.avg_price,
                    "quantity": pos.quantity
                }

        return {
            "total_pnl": total_pnl,
            "total_pnl_percent": pnl_percent,
            "portfolio_value": portfolio_value,
            "cash": self.account.balance,
            "positions": position_pnl
        }

    def reset_account(self, starting_balance: float = None):
        """Reset paper trading account"""
        balance = starting_balance or DEFAULT_PAPER_BALANCE
        self.account = PaperAccount(
            balance=balance,
            starting_balance=balance
        )
        self._save_account()
