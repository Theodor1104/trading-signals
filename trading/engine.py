"""
Trading Engine - Unified interface for paper and live trading
"""
from typing import Optional
from config import TradingMode, DEFAULT_MODE
from .paper import PaperTrader
from .orders import Order, OrderType


class TradingEngine:
    """Unified trading interface for paper and live modes"""

    def __init__(self, mode: str = None):
        self.mode = mode or DEFAULT_MODE
        self._paper_trader = None
        self._live_trader = None

    @property
    def paper_trader(self) -> PaperTrader:
        if self._paper_trader is None:
            self._paper_trader = PaperTrader()
        return self._paper_trader

    @property
    def is_paper(self) -> bool:
        return self.mode == TradingMode.PAPER

    @property
    def is_live(self) -> bool:
        return self.mode == TradingMode.LIVE

    def set_mode(self, mode: str):
        """Switch trading mode"""
        if mode not in [TradingMode.PAPER, TradingMode.LIVE]:
            raise ValueError(f"Invalid mode: {mode}")
        self.mode = mode

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
        if self.is_paper:
            return self.paper_trader.buy(
                symbol, quantity, market, order_type, limit_price, notes
            )
        else:
            # Live trading - not implemented yet
            raise NotImplementedError(
                "Live trading ikke implementeret endnu. "
                "Brug paper mode til at øve dig."
            )

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
        if self.is_paper:
            return self.paper_trader.sell(
                symbol, quantity, market, order_type, limit_price, notes
            )
        else:
            raise NotImplementedError(
                "Live trading ikke implementeret endnu. "
                "Brug paper mode til at øve dig."
            )

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        if self.is_paper:
            return self.paper_trader.get_portfolio_value()
        else:
            raise NotImplementedError("Live trading ikke implementeret endnu.")

    def get_pnl(self) -> dict:
        """Get P&L summary"""
        if self.is_paper:
            return self.paper_trader.get_pnl()
        else:
            raise NotImplementedError("Live trading ikke implementeret endnu.")

    def get_positions(self) -> dict:
        """Get current positions"""
        if self.is_paper:
            return self.paper_trader.account.positions
        else:
            raise NotImplementedError("Live trading ikke implementeret endnu.")

    def get_orders(self) -> list:
        """Get order history"""
        if self.is_paper:
            return self.paper_trader.account.orders
        else:
            raise NotImplementedError("Live trading ikke implementeret endnu.")

    def get_balance(self) -> float:
        """Get cash balance"""
        if self.is_paper:
            return self.paper_trader.account.balance
        else:
            raise NotImplementedError("Live trading ikke implementeret endnu.")

    def reset(self, starting_balance: float = None):
        """Reset account (paper mode only)"""
        if self.is_paper:
            self.paper_trader.reset_account(starting_balance)
        else:
            raise ValueError("Kan ikke resette live konto!")
