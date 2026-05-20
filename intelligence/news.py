"""
News Analyzer - Fetch and analyze financial news from multiple sources
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re


class NewsAnalyzer:
    """Fetch financial news from multiple RSS feeds and sources"""

    # Financial news RSS feeds
    RSS_FEEDS = {
        "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
        "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "reuters_business": "https://www.rss.reuters.com/rssFeed/businessNews",
        "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "investing_com": "https://www.investing.com/rss/news.rss",
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "cointelegraph": "https://cointelegraph.com/rss",
    }

    # Keywords for filtering relevant news
    CRYPTO_KEYWORDS = ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "defi", "nft", "binance", "coinbase"]
    STOCK_KEYWORDS = ["stock", "shares", "nasdaq", "nyse", "dow", "s&p", "earnings", "ipo", "fed", "interest rate"]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_all_news(self, max_per_source: int = 10) -> List[Dict]:
        """Fetch news from all RSS sources"""
        all_news = []

        for source_name, feed_url in self.RSS_FEEDS.items():
            try:
                news = self._fetch_rss(feed_url, source_name, max_per_source)
                all_news.extend(news)
            except Exception:
                continue

        # Sort by date (newest first)
        all_news.sort(key=lambda x: x.get('published', ''), reverse=True)

        return all_news

    def fetch_news_for_symbol(self, symbol: str, market: str = "stocks") -> List[Dict]:
        """Fetch news relevant to a specific symbol"""
        all_news = self.fetch_all_news(max_per_source=20)

        # Filter by symbol and market
        symbol_clean = symbol.replace("/USDT", "").replace("=X", "").lower()

        relevant = []
        for article in all_news:
            title_lower = article.get('title', '').lower()
            summary_lower = article.get('summary', '').lower()
            content = title_lower + " " + summary_lower

            # Check if symbol mentioned
            if symbol_clean in content:
                article['relevance'] = 'direct'
                relevant.append(article)
            # Check market keywords
            elif market == "crypto" and any(kw in content for kw in self.CRYPTO_KEYWORDS):
                article['relevance'] = 'market'
                relevant.append(article)
            elif market == "stocks" and any(kw in content for kw in self.STOCK_KEYWORDS):
                article['relevance'] = 'market'
                relevant.append(article)

        return relevant[:15]

    def get_market_headlines(self, market: str = "stocks", limit: int = 10) -> List[Dict]:
        """Get top headlines for a market"""
        all_news = self.fetch_all_news(max_per_source=15)

        keywords = self.CRYPTO_KEYWORDS if market == "crypto" else self.STOCK_KEYWORDS

        relevant = []
        for article in all_news:
            content = (article.get('title', '') + " " + article.get('summary', '')).lower()
            if any(kw in content for kw in keywords):
                relevant.append(article)

        return relevant[:limit]

    def _fetch_rss(self, url: str, source: str, max_items: int) -> List[Dict]:
        """Fetch and parse RSS feed"""
        try:
            feed = feedparser.parse(url)

            news = []
            for entry in feed.entries[:max_items]:
                published = entry.get('published', entry.get('updated', ''))

                news.append({
                    'title': entry.get('title', ''),
                    'summary': self._clean_html(entry.get('summary', '')),
                    'link': entry.get('link', ''),
                    'source': source,
                    'published': published,
                })

            return news
        except Exception:
            return []

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text()[:500]

    def get_fear_greed_index(self) -> Dict:
        """Get Crypto Fear & Greed Index"""
        try:
            response = self.session.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=10
            )
            data = response.json()

            if data and 'data' in data and len(data['data']) > 0:
                fng = data['data'][0]
                return {
                    'value': int(fng['value']),
                    'classification': fng['value_classification'],
                    'timestamp': fng['timestamp']
                }
        except Exception:
            pass

        return {'value': 50, 'classification': 'Neutral', 'timestamp': ''}

    def get_trending_tickers(self) -> List[str]:
        """Get trending tickers from Yahoo Finance"""
        try:
            response = self.session.get(
                "https://finance.yahoo.com/trending-tickers",
                timeout=10
            )
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract ticker symbols
            tickers = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/quote/' in href:
                    ticker = href.split('/quote/')[1].split('?')[0].split('/')[0]
                    if ticker and ticker not in tickers:
                        tickers.append(ticker)

            return tickers[:10]
        except Exception:
            return []
