"""
Backtesting Engine
"""
import pandas as pd
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from data.fetcher import DataFetcher
from .strategies import Strategy
from .metrics import calculate_metrics, BacktestMetrics


@dataclass
class BacktestResult:
    """Result from running a backtest"""
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    metrics: BacktestMetrics
    trades: list[dict]
    equity_curve: pd.Series


class Backtester:
    """Run backtests on historical data"""

    def __init__(self):
        self.fetcher = DataFetcher()

    def run(
        self,
        symbol: str,
        market: str,
        strategy: Strategy,
        initial_capital: float = 10000,
        period: str = "1y",
        position_size: float = 0.95,  # Use 95% of capital per trade
        commission: float = 0.001,  # 0.1% commission
    ) -> Optional[BacktestResult]:
        """
        Run a backtest

        Args:
            symbol: Symbol to backtest
            market: Market type (stocks, crypto, forex)
            strategy: Strategy instance to use
            initial_capital: Starting capital
            period: Historical period (1mo, 3mo, 6mo, 1y, 2y)
            position_size: Fraction of capital to use per trade
            commission: Commission rate per trade

        Returns:
            BacktestResult with metrics and trade history
        """
        # Get historical data
        data = self.fetcher.get_historical(symbol, market, period=period)

        if data is None or data.empty:
            return None

        # Prepare data with indicators
        data = strategy.prepare_data(data)

        # Generate signals
        signals = strategy.generate_signals(data)

        # Run simulation
        trades, equity_curve = self._simulate(
            data, signals, initial_capital, position_size, commission
        )

        # Calculate metrics
        metrics = calculate_metrics(trades, equity_curve, initial_capital)

        return BacktestResult(
            symbol=symbol,
            strategy_name=strategy.name,
            start_date=data.index[0],
            end_date=data.index[-1],
            initial_capital=initial_capital,
            final_value=equity_curve.iloc[-1],
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )

    def _simulate(
        self,
        data: pd.DataFrame,
        signals: pd.Series,
        initial_capital: float,
        position_size: float,
        commission: float
    ) -> tuple[list[dict], pd.Series]:
        """
        Simulate trading based on signals

        Returns:
            Tuple of (trades list, equity curve)
        """
        cash = initial_capital
        position = 0  # Number of shares/units held
        entry_price = 0
        entry_date = None

        trades = []
        equity = []

        for date, row in data.iterrows():
            signal = signals.get(date, 0)
            price = row["close"]

            # Calculate current portfolio value
            portfolio_value = cash + (position * price)

            # Process signals
            if signal == 1 and position == 0:  # BUY signal, no position
                # Calculate position size
                trade_value = portfolio_value * position_size
                position = trade_value / price
                cost = position * price * (1 + commission)
                cash -= cost
                entry_price = price
                entry_date = date

            elif signal == -1 and position > 0:  # SELL signal, have position
                # Close position
                proceeds = position * price * (1 - commission)
                pnl = proceeds - (position * entry_price)

                trades.append({
                    "entry_date": entry_date,
                    "exit_date": date,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "quantity": position,
                    "pnl": pnl,
                    "pnl_pct": (price / entry_price - 1) * 100
                })

                cash += proceeds
                position = 0
                entry_price = 0
                entry_date = None

            # Record equity
            current_value = cash + (position * price)
            equity.append({"date": date, "value": current_value})

        # Close any remaining position at the end
        if position > 0:
            final_price = data["close"].iloc[-1]
            proceeds = position * final_price * (1 - commission)
            pnl = proceeds - (position * entry_price)

            trades.append({
                "entry_date": entry_date,
                "exit_date": data.index[-1],
                "entry_price": entry_price,
                "exit_price": final_price,
                "quantity": position,
                "pnl": pnl,
                "pnl_pct": (final_price / entry_price - 1) * 100
            })

        # Create equity curve
        equity_df = pd.DataFrame(equity)
        equity_curve = pd.Series(
            equity_df["value"].values,
            index=pd.to_datetime(equity_df["date"])
        )

        return trades, equity_curve

    def compare_strategies(
        self,
        symbol: str,
        market: str,
        strategies: list[Strategy],
        initial_capital: float = 10000,
        period: str = "1y"
    ) -> list[BacktestResult]:
        """Compare multiple strategies on the same data"""
        results = []

        for strategy in strategies:
            result = self.run(
                symbol, market, strategy,
                initial_capital=initial_capital,
                period=period
            )
            if result:
                results.append(result)

        # Sort by total return
        results.sort(key=lambda r: r.metrics.total_return_pct, reverse=True)

        return results
