"""
Stock data provider using Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from typing import Optional


class StockProvider:
    """Fetch stock data from Yahoo Finance"""

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a stock"""
        try:
            ticker = yf.Ticker(symbol)
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
            symbol: Stock ticker (e.g., "AAPL")
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        try:
            ticker = yf.Ticker(symbol)
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

    def get_info(self, symbol: str) -> Optional[dict]:
        """Get company information"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except Exception:
            return None

    def search(self, query: str) -> list[dict]:
        """Search for stocks matching query"""
        # Yahoo Finance doesn't have a good search API
        # Return common matches for now
        common_stocks = {
            "apple": {"symbol": "AAPL", "name": "Apple Inc."},
            "microsoft": {"symbol": "MSFT", "name": "Microsoft Corporation"},
            "google": {"symbol": "GOOGL", "name": "Alphabet Inc."},
            "amazon": {"symbol": "AMZN", "name": "Amazon.com Inc."},
            "tesla": {"symbol": "TSLA", "name": "Tesla Inc."},
            "nvidia": {"symbol": "NVDA", "name": "NVIDIA Corporation"},
            "meta": {"symbol": "META", "name": "Meta Platforms Inc."},
            "netflix": {"symbol": "NFLX", "name": "Netflix Inc."},
        }

        query_lower = query.lower()
        results = []

        for key, value in common_stocks.items():
            if query_lower in key or query_lower in value["symbol"].lower():
                results.append(value)

        return results
