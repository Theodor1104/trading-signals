"""
Forex data provider using Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from typing import Optional


class ForexProvider:
    """Fetch forex data from Yahoo Finance"""

    # Common forex pairs with Yahoo Finance symbols
    FOREX_PAIRS = {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "USD/CHF": "USDCHF=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "USDCAD=X",
        "NZD/USD": "NZDUSD=X",
        "EUR/GBP": "EURGBP=X",
        "EUR/JPY": "EURJPY=X",
        "GBP/JPY": "GBPJPY=X",
    }

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a forex pair

        Args:
            symbol: Forex pair (e.g., "EUR/USD" or "EURUSD=X")
        """
        try:
            yahoo_symbol = self._to_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
            return None
        except Exception:
            return None

    def get_historical(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data

        Args:
            symbol: Forex pair (e.g., "EUR/USD" or "EURUSD=X")
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
        """
        try:
            yahoo_symbol = self._to_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            data = ticker.history(period=period, interval=interval)

            if data.empty:
                return None

            # Standardize column names
            data = data.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })

            # Keep only OHLCV columns
            data = data[["open", "high", "low", "close", "volume"]]

            return data
        except Exception:
            return None

    def search(self, query: str) -> list[dict]:
        """Search for forex pairs matching query"""
        query_upper = query.upper().replace("/", "").replace("=X", "")

        results = []
        for pair, yahoo_symbol in self.FOREX_PAIRS.items():
            pair_clean = pair.replace("/", "")
            if query_upper in pair_clean:
                results.append({
                    "symbol": yahoo_symbol,
                    "name": pair
                })

        return results

    def _to_yahoo_symbol(self, symbol: str) -> str:
        """Convert various forex formats to Yahoo Finance symbol"""
        # If already Yahoo format
        if "=X" in symbol:
            return symbol

        # If in FOREX_PAIRS
        if symbol in self.FOREX_PAIRS:
            return self.FOREX_PAIRS[symbol]

        # Try to construct Yahoo symbol
        clean = symbol.upper().replace("/", "").replace("-", "")
        return f"{clean}=X"
