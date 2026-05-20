"""
Unified Data Fetcher - Handles data from multiple markets
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Literal
from pathlib import Path
import json
import pickle

from .providers.stocks import StockProvider
from .providers.crypto import CryptoProvider
from .providers.forex import ForexProvider
from config import DATA_DIR


MarketType = Literal["stocks", "crypto", "forex"]


class DataFetcher:
    """Unified interface for fetching market data"""

    def __init__(self):
        self.stock_provider = StockProvider()
        self.crypto_provider = CryptoProvider()
        self.forex_provider = ForexProvider()
        self._cache_dir = DATA_DIR

    def get_price(self, symbol: str, market: MarketType) -> Optional[float]:
        """Get current price for a symbol"""
        provider = self._get_provider(market)
        return provider.get_price(symbol)

    def get_historical(
        self,
        symbol: str,
        market: MarketType,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data

        Args:
            symbol: Ticker symbol
            market: Market type (stocks, crypto, forex)
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        # Check cache first
        cache_key = f"{market}_{symbol}_{period}_{interval}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        provider = self._get_provider(market)
        data = provider.get_historical(symbol, period, interval)

        if data is not None and not data.empty:
            self._save_cache(cache_key, data)

        return data

    def get_multiple_prices(
        self,
        symbols: list[str],
        market: MarketType
    ) -> dict[str, Optional[float]]:
        """Get current prices for multiple symbols"""
        provider = self._get_provider(market)
        return {symbol: provider.get_price(symbol) for symbol in symbols}

    def search_symbol(self, query: str, market: MarketType) -> list[dict]:
        """Search for symbols matching query"""
        provider = self._get_provider(market)
        return provider.search(query)

    def _get_provider(self, market: MarketType):
        """Get the appropriate provider for a market"""
        providers = {
            "stocks": self.stock_provider,
            "crypto": self.crypto_provider,
            "forex": self.forex_provider
        }
        return providers.get(market, self.stock_provider)

    def _get_cached(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if fresh (< 1 hour for daily data)"""
        cache_file = self._cache_dir / f"{cache_key}.pkl"
        meta_file = self._cache_dir / f"{cache_key}.meta"

        if not cache_file.exists() or not meta_file.exists():
            return None

        # Check if cache is fresh
        with open(meta_file) as f:
            meta = json.load(f)

        cached_time = datetime.fromisoformat(meta["timestamp"])
        cache_duration = timedelta(hours=1)

        if datetime.now() - cached_time > cache_duration:
            return None

        with open(cache_file, "rb") as f:
            return pickle.load(f)

    def _save_cache(self, cache_key: str, data: pd.DataFrame):
        """Save data to cache"""
        cache_file = self._cache_dir / f"{cache_key}.pkl"
        meta_file = self._cache_dir / f"{cache_key}.meta"

        with open(cache_file, "wb") as f:
            pickle.dump(data, f)

        with open(meta_file, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat()}, f)

    def clear_cache(self):
        """Clear all cached data"""
        for file in self._cache_dir.glob("*"):
            file.unlink()
