"""
Backtesting Performance Metrics
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class BacktestMetrics:
    """Performance metrics from a backtest"""
    total_return: float
    total_return_pct: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    avg_trade_duration: float  # in days


def calculate_metrics(
    trades: list[dict],
    equity_curve: pd.Series,
    initial_capital: float,
    risk_free_rate: float = 0.02
) -> BacktestMetrics:
    """
    Calculate comprehensive backtest metrics

    Args:
        trades: List of trade dictionaries with 'pnl', 'entry_date', 'exit_date'
        equity_curve: Series of portfolio values over time
        initial_capital: Starting capital
        risk_free_rate: Annual risk-free rate for Sharpe calculation
    """
    final_value = equity_curve.iloc[-1] if len(equity_curve) > 0 else initial_capital

    # Total return
    total_return = final_value - initial_capital
    total_return_pct = (total_return / initial_capital) * 100

    # Annualized return
    if len(equity_curve) > 1:
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365 if days > 0 else 1
        annualized_return = ((final_value / initial_capital) ** (1 / years) - 1) * 100
    else:
        annualized_return = 0

    # Sharpe Ratio
    if len(equity_curve) > 1:
        returns = equity_curve.pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            excess_returns = returns.mean() - (risk_free_rate / 252)
            sharpe_ratio = (excess_returns / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0

    # Max Drawdown
    if len(equity_curve) > 0:
        peak = equity_curve.expanding(min_periods=1).max()
        drawdown = equity_curve - peak
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / peak.max()) * 100 if peak.max() > 0 else 0
    else:
        max_drawdown = 0
        max_drawdown_pct = 0

    # Trade statistics
    if trades:
        pnls = [t.get("pnl", 0) for t in trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        total_trades = len(trades)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)

        win_rate = (num_winning / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0

        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        best_trade = max(pnls) if pnls else 0
        worst_trade = min(pnls) if pnls else 0

        # Average trade duration
        durations = []
        for t in trades:
            if "entry_date" in t and "exit_date" in t:
                duration = (t["exit_date"] - t["entry_date"]).days
                durations.append(duration)
        avg_duration = np.mean(durations) if durations else 0
    else:
        total_trades = 0
        num_winning = 0
        num_losing = 0
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
        best_trade = 0
        worst_trade = 0
        avg_duration = 0

    return BacktestMetrics(
        total_return=total_return,
        total_return_pct=total_return_pct,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=total_trades,
        winning_trades=num_winning,
        losing_trades=num_losing,
        avg_win=avg_win,
        avg_loss=avg_loss,
        best_trade=best_trade,
        worst_trade=worst_trade,
        avg_trade_duration=avg_duration
    )
