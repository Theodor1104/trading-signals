"""
Technical Analysis Indicators
"""
import pandas as pd
import ta
from typing import Optional
from dataclasses import dataclass

from config import (
    DEFAULT_RSI_PERIOD,
    DEFAULT_SMA_PERIODS,
    DEFAULT_EMA_PERIODS,
    DEFAULT_MACD_PARAMS,
    DEFAULT_BB_PARAMS,
)


@dataclass
class Signal:
    """Trading signal"""
    type: str  # "BUY", "SELL", "NEUTRAL"
    strength: float  # 0-100
    reason: str


class TechnicalAnalysis:
    """Calculate technical indicators and generate signals"""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV data

        Args:
            data: DataFrame with columns: open, high, low, close, volume
        """
        self.data = data.copy()

    def add_all_indicators(self) -> pd.DataFrame:
        """Add all standard indicators to the data"""
        self.add_sma()
        self.add_ema()
        self.add_rsi()
        self.add_macd()
        self.add_bollinger_bands()
        self.add_atr()
        self.add_volume_sma()
        return self.data

    def add_sma(self, periods: list[int] = None) -> pd.DataFrame:
        """Add Simple Moving Averages"""
        periods = periods or DEFAULT_SMA_PERIODS
        for period in periods:
            self.data[f"sma_{period}"] = ta.trend.sma_indicator(
                self.data["close"], window=period
            )
        return self.data

    def add_ema(self, periods: list[int] = None) -> pd.DataFrame:
        """Add Exponential Moving Averages"""
        periods = periods or DEFAULT_EMA_PERIODS
        for period in periods:
            self.data[f"ema_{period}"] = ta.trend.ema_indicator(
                self.data["close"], window=period
            )
        return self.data

    def add_rsi(self, period: int = None) -> pd.DataFrame:
        """Add Relative Strength Index"""
        period = period or DEFAULT_RSI_PERIOD
        self.data["rsi"] = ta.momentum.rsi(self.data["close"], window=period)
        return self.data

    def add_macd(self, params: tuple = None) -> pd.DataFrame:
        """Add MACD (Moving Average Convergence Divergence)"""
        fast, slow, signal = params or DEFAULT_MACD_PARAMS
        macd = ta.trend.MACD(
            self.data["close"],
            window_slow=slow,
            window_fast=fast,
            window_sign=signal
        )
        self.data[f"MACD_{fast}_{slow}_{signal}"] = macd.macd()
        self.data[f"MACDs_{fast}_{slow}_{signal}"] = macd.macd_signal()
        self.data[f"MACDh_{fast}_{slow}_{signal}"] = macd.macd_diff()
        return self.data

    def add_bollinger_bands(self, params: tuple = None) -> pd.DataFrame:
        """Add Bollinger Bands"""
        period, std = params or DEFAULT_BB_PARAMS
        bb = ta.volatility.BollingerBands(
            self.data["close"], window=period, window_dev=std
        )
        self.data[f"BBU_{period}_{std}"] = bb.bollinger_hband()
        self.data[f"BBM_{period}_{std}"] = bb.bollinger_mavg()
        self.data[f"BBL_{period}_{std}"] = bb.bollinger_lband()
        return self.data

    def add_atr(self, period: int = 14) -> pd.DataFrame:
        """Add Average True Range"""
        self.data["atr"] = ta.volatility.average_true_range(
            self.data["high"],
            self.data["low"],
            self.data["close"],
            window=period
        )
        return self.data

    def add_volume_sma(self, period: int = 20) -> pd.DataFrame:
        """Add Volume SMA for volume analysis"""
        self.data["volume_sma"] = ta.trend.sma_indicator(
            self.data["volume"], window=period
        )
        return self.data

    def get_current_values(self) -> dict:
        """Get the most recent indicator values"""
        if self.data.empty:
            return {}

        latest = self.data.iloc[-1]
        return {
            "price": latest.get("close"),
            "rsi": latest.get("rsi"),
            "macd": latest.get("MACD_12_26_9"),
            "macd_signal": latest.get("MACDs_12_26_9"),
            "macd_hist": latest.get("MACDh_12_26_9"),
            "sma_20": latest.get("sma_20"),
            "sma_50": latest.get("sma_50"),
            "sma_200": latest.get("sma_200"),
            "bb_upper": latest.get("BBU_20_2"),
            "bb_middle": latest.get("BBM_20_2"),
            "bb_lower": latest.get("BBL_20_2"),
            "atr": latest.get("atr"),
        }

    def generate_signal(self) -> Signal:
        """Generate a trading signal based on multiple indicators"""
        values = self.get_current_values()

        if not values.get("price"):
            return Signal("NEUTRAL", 0, "Insufficient data")

        buy_signals = 0
        sell_signals = 0
        reasons = []

        # RSI signals
        rsi = values.get("rsi")
        if rsi:
            if rsi < 30:
                buy_signals += 2
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                sell_signals += 2
                reasons.append(f"RSI overbought ({rsi:.1f})")

        # MACD signals
        macd_hist = values.get("macd_hist")
        if macd_hist:
            if macd_hist > 0:
                buy_signals += 1
                reasons.append("MACD bullish")
            else:
                sell_signals += 1
                reasons.append("MACD bearish")

        # Price vs SMA signals
        price = values.get("price")
        sma_50 = values.get("sma_50")
        sma_200 = values.get("sma_200")

        if price and sma_50:
            if price > sma_50:
                buy_signals += 1
                reasons.append("Price above SMA50")
            else:
                sell_signals += 1
                reasons.append("Price below SMA50")

        if sma_50 and sma_200:
            if sma_50 > sma_200:
                buy_signals += 1
                reasons.append("Golden cross (SMA50 > SMA200)")
            else:
                sell_signals += 1
                reasons.append("Death cross (SMA50 < SMA200)")

        # Bollinger Band signals
        bb_lower = values.get("bb_lower")
        bb_upper = values.get("bb_upper")

        if price and bb_lower and bb_upper:
            if price <= bb_lower:
                buy_signals += 1
                reasons.append("Price at lower BB")
            elif price >= bb_upper:
                sell_signals += 1
                reasons.append("Price at upper BB")

        # Calculate final signal
        total = buy_signals + sell_signals
        if total == 0:
            return Signal("NEUTRAL", 50, "No clear signals")

        if buy_signals > sell_signals:
            strength = (buy_signals / total) * 100
            return Signal("BUY", strength, " | ".join(reasons))
        elif sell_signals > buy_signals:
            strength = (sell_signals / total) * 100
            return Signal("SELL", strength, " | ".join(reasons))
        else:
            return Signal("NEUTRAL", 50, " | ".join(reasons))

    def find_support_resistance(self, window: int = 20) -> dict:
        """Find support and resistance levels"""
        if len(self.data) < window:
            return {"support": [], "resistance": []}

        highs = self.data["high"].rolling(window=window, center=True).max()
        lows = self.data["low"].rolling(window=window, center=True).min()

        resistance_levels = self.data[self.data["high"] == highs]["high"].unique()
        support_levels = self.data[self.data["low"] == lows]["low"].unique()

        # Get top 3 most recent levels
        return {
            "support": sorted(support_levels)[:3],
            "resistance": sorted(resistance_levels, reverse=True)[:3]
        }
