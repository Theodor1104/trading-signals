"""
Cryptocurrency data provider using ccxt
"""
import ccxt
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

from config import BINANCE_API_KEY, BINANCE_SECRET


class CryptoProvider:
    """Fetch crypto data from exchanges via ccxt"""

    def __init__(self):
        # Initialize Binance (most liquid exchange)
        self.exchange = ccxt.binance({
            "apiKey": BINANCE_API_KEY if BINANCE_API_KEY else None,
            "secret": BINANCE_SECRET if BINANCE_SECRET else None,
            "enableRateLimit": True,
        })

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a crypto pair

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
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
            symbol: Trading pair (e.g., "BTC/USDT")
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y)
            interval: 1m, 5m, 15m, 1h, 4h, 1d, 1w
        """
        try:
            # Convert period to since timestamp
            since = self._period_to_timestamp(period)

            # Map interval to ccxt timeframe
            timeframe = self._map_interval(interval)

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since,
                limit=1000
            )

            if not ohlcv:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

            # Convert timestamp to datetime index
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            return df
        except Exception:
            return None

    def get_order_book(self, symbol: str, limit: int = 10) -> Optional[dict]:
        """Get order book for a symbol"""
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception:
            return None

    def search(self, query: str) -> list[dict]:
        """Search for crypto pairs matching query"""
        try:
            markets = self.exchange.load_markets()
            query_upper = query.upper()

            results = []
            for symbol, market in markets.items():
                if query_upper in symbol and market["quote"] == "USDT":
                    results.append({
                        "symbol": symbol,
                        "name": f"{market['base']}/{market['quote']}"
                    })
                    if len(results) >= 10:
                        break

            return results
        except Exception:
            return []

    def _period_to_timestamp(self, period: str) -> int:
        """Convert period string to millisecond timestamp"""
        now = datetime.now()

        period_map = {
            "1d": timedelta(days=1),
            "5d": timedelta(days=5),
            "1mo": timedelta(days=30),
            "3mo": timedelta(days=90),
            "6mo": timedelta(days=180),
            "1y": timedelta(days=365),
            "2y": timedelta(days=730),
        }

        delta = period_map.get(period, timedelta(days=365))
        since = now - delta

        return int(since.timestamp() * 1000)

    def _map_interval(self, interval: str) -> str:
        """Map standard interval to ccxt timeframe"""
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1wk": "1w",
            "1mo": "1M",
        }
        return interval_map.get(interval, "1d")
