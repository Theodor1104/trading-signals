"""
Market Scanner - Scan multiple symbols for trading signals
"""
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from data.fetcher import DataFetcher
from analysis.indicators import TechnicalAnalysis, Signal


@dataclass
class ScanResult:
    """Result from scanning a symbol"""
    symbol: str
    market: str
    price: Optional[float]
    signal: Signal
    rsi: Optional[float]
    trend: str  # "UP", "DOWN", "SIDEWAYS"


class MarketScanner:
    """Scan markets for trading opportunities"""

    def __init__(self):
        self.fetcher = DataFetcher()

    def scan_symbol(self, symbol: str, market: str) -> Optional[ScanResult]:
        """Scan a single symbol and return analysis"""
        try:
            # Get historical data
            data = self.fetcher.get_historical(
                symbol, market, period="3mo", interval="1d"
            )

            if data is None or data.empty:
                return None

            # Calculate indicators
            ta = TechnicalAnalysis(data)
            ta.add_all_indicators()

            # Get current values
            values = ta.get_current_values()
            signal = ta.generate_signal()

            # Determine trend
            trend = self._determine_trend(data, values)

            return ScanResult(
                symbol=symbol,
                market=market,
                price=values.get("price"),
                signal=signal,
                rsi=values.get("rsi"),
                trend=trend
            )
        except Exception:
            return None

    def scan_multiple(
        self,
        symbols: list[str],
        market: str,
        max_workers: int = 5
    ) -> list[ScanResult]:
        """Scan multiple symbols in parallel"""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.scan_symbol, symbol, market): symbol
                for symbol in symbols
            }

            for future in futures:
                result = future.result()
                if result:
                    results.append(result)

        return results

    def scan_for_signals(
        self,
        symbols: list[str],
        market: str,
        signal_type: str = None
    ) -> list[ScanResult]:
        """Scan for specific signal types (BUY, SELL)"""
        results = self.scan_multiple(symbols, market)

        if signal_type:
            results = [r for r in results if r.signal.type == signal_type]

        # Sort by signal strength
        results.sort(key=lambda x: x.signal.strength, reverse=True)

        return results

    def scan_oversold(
        self,
        symbols: list[str],
        market: str,
        threshold: float = 30
    ) -> list[ScanResult]:
        """Find oversold stocks (RSI < threshold)"""
        results = self.scan_multiple(symbols, market)
        oversold = [r for r in results if r.rsi and r.rsi < threshold]
        oversold.sort(key=lambda x: x.rsi or 100)
        return oversold

    def scan_overbought(
        self,
        symbols: list[str],
        market: str,
        threshold: float = 70
    ) -> list[ScanResult]:
        """Find overbought stocks (RSI > threshold)"""
        results = self.scan_multiple(symbols, market)
        overbought = [r for r in results if r.rsi and r.rsi > threshold]
        overbought.sort(key=lambda x: -(x.rsi or 0))
        return overbought

    def _determine_trend(self, data, values) -> str:
        """Determine the current trend"""
        price = values.get("price")
        sma_20 = values.get("sma_20")
        sma_50 = values.get("sma_50")

        if not all([price, sma_20, sma_50]):
            return "SIDEWAYS"

        if price > sma_20 > sma_50:
            return "UP"
        elif price < sma_20 < sma_50:
            return "DOWN"
        else:
            return "SIDEWAYS"
