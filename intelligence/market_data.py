"""
Market Intelligence - Combines all data sources for comprehensive analysis
"""
import requests
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetcher import DataFetcher
from analysis.indicators import TechnicalAnalysis
from .news import NewsAnalyzer
from .sentiment import SentimentAnalyzer


class MarketIntelligence:
    """
    Comprehensive market intelligence combining:
    - Real-time price data
    - Technical analysis
    - News sentiment
    - Fear & Greed index
    - Multiple data sources
    """

    def __init__(self):
        self.fetcher = DataFetcher()
        self.news_analyzer = NewsAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()

    def get_full_analysis(self, symbol: str, market: str) -> Optional[Dict]:
        """Get complete analysis from all sources"""

        result = {
            'symbol': symbol,
            'market': market,
            'timestamp': datetime.now().isoformat(),
            'price_data': None,
            'technical': None,
            'news_sentiment': None,
            'fear_greed': None,
            'final_signal': None,
            'confidence': 0,
            'reasons': []
        }

        # 1. Get price data and technical analysis
        try:
            data = self.fetcher.get_historical(symbol, market, period="3mo", interval="1d")
            if data is not None and len(data) >= 20:
                ta = TechnicalAnalysis(data)
                ta.add_all_indicators()

                latest = ta.data.iloc[-1]
                prev = ta.data.iloc[-2] if len(ta.data) > 1 else latest

                result['price_data'] = {
                    'current_price': float(latest['close']),
                    'open': float(latest['open']),
                    'high': float(latest['high']),
                    'low': float(latest['low']),
                    'volume': float(latest['volume']),
                    'change_1d': ((latest['close'] / prev['close']) - 1) * 100 if prev['close'] else 0
                }

                result['technical'] = self._analyze_technical(ta.data, latest, prev)
                result['chart_data'] = ta.data
        except Exception as e:
            result['reasons'].append(f"Pris data fejl: {str(e)}")

        # 2. Get news sentiment
        try:
            news = self.news_analyzer.fetch_news_for_symbol(symbol, market)
            if news:
                sentiment = self.sentiment_analyzer.analyze_news_batch(news)
                sentiment_signal = self.sentiment_analyzer.get_sentiment_signal(sentiment)

                result['news_sentiment'] = {
                    'score': sentiment['overall_score'],
                    'label': sentiment['overall_label'],
                    'articles': len(news),
                    'signal': sentiment_signal,
                    'recent_headlines': [n['title'] for n in news[:5]]
                }
        except Exception as e:
            result['reasons'].append(f"Nyheds fejl: {str(e)}")

        # 3. Get Fear & Greed (for crypto)
        if market == "crypto":
            try:
                fg = self.news_analyzer.get_fear_greed_index()
                result['fear_greed'] = fg
            except Exception:
                pass

        # 4. Calculate final signal
        result['final_signal'], result['confidence'], signal_reasons = self._calculate_final_signal(result)
        result['reasons'].extend(signal_reasons)

        return result

    def _analyze_technical(self, data, latest, prev) -> Dict:
        """Analyze technical indicators"""
        signals = []
        buy_score = 0
        sell_score = 0

        # RSI
        rsi = latest.get('rsi')
        if rsi:
            if rsi < 30:
                buy_score += 25
                signals.append(('RSI', 'BUY', f'Oversold ({rsi:.1f})'))
            elif rsi < 40:
                buy_score += 10
                signals.append(('RSI', 'SLIGHTLY_BULLISH', f'Lav ({rsi:.1f})'))
            elif rsi > 70:
                sell_score += 25
                signals.append(('RSI', 'SELL', f'Overbought ({rsi:.1f})'))
            elif rsi > 60:
                sell_score += 10
                signals.append(('RSI', 'SLIGHTLY_BEARISH', f'Høj ({rsi:.1f})'))
            else:
                signals.append(('RSI', 'NEUTRAL', f'Neutral ({rsi:.1f})'))

        # MACD
        macd_hist = latest.get('MACDh_12_26_9')
        prev_macd_hist = prev.get('MACDh_12_26_9')

        if macd_hist is not None and prev_macd_hist is not None:
            if macd_hist > 0 and prev_macd_hist <= 0:
                buy_score += 20
                signals.append(('MACD', 'BUY', 'Bullish crossover'))
            elif macd_hist < 0 and prev_macd_hist >= 0:
                sell_score += 20
                signals.append(('MACD', 'SELL', 'Bearish crossover'))
            elif macd_hist > 0:
                buy_score += 5
                signals.append(('MACD', 'SLIGHTLY_BULLISH', 'Positiv'))
            else:
                sell_score += 5
                signals.append(('MACD', 'SLIGHTLY_BEARISH', 'Negativ'))

        # Moving Averages
        price = latest['close']
        sma_20 = latest.get('sma_20')
        sma_50 = latest.get('sma_50')
        sma_200 = latest.get('sma_200')

        if sma_20 and sma_50:
            if price > sma_20 > sma_50:
                buy_score += 15
                signals.append(('Trend', 'BUY', 'Stærk optrend'))
            elif price < sma_20 < sma_50:
                sell_score += 15
                signals.append(('Trend', 'SELL', 'Stærk nedtrend'))

        if sma_50 and sma_200:
            if sma_50 > sma_200:
                buy_score += 10
                signals.append(('Golden Cross', 'BUY', 'SMA50 > SMA200'))
            else:
                sell_score += 10
                signals.append(('Death Cross', 'SELL', 'SMA50 < SMA200'))

        # Bollinger Bands
        bb_upper = latest.get('BBU_20_2')
        bb_lower = latest.get('BBL_20_2')

        if bb_upper and bb_lower and bb_upper != bb_lower:
            bb_position = (price - bb_lower) / (bb_upper - bb_lower)

            if bb_position < 0.1:
                buy_score += 15
                signals.append(('Bollinger', 'BUY', 'Ved nedre band'))
            elif bb_position > 0.9:
                sell_score += 15
                signals.append(('Bollinger', 'SELL', 'Ved øvre band'))

        # Volume analysis
        volume = latest.get('volume', 0)
        vol_sma = latest.get('volume_sma', 0)

        if vol_sma and volume > vol_sma * 1.5:
            signals.append(('Volume', 'HIGH', 'Højt volumen'))

        # Support/Resistance
        recent_high = data['high'].tail(20).max()
        recent_low = data['low'].tail(20).min()

        return {
            'signals': signals,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'rsi': rsi,
            'macd': macd_hist,
            'support': recent_low,
            'resistance': recent_high,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200
        }

    def _calculate_final_signal(self, result: Dict) -> tuple:
        """Calculate final trading signal from all sources"""
        total_buy = 0
        total_sell = 0
        reasons = []

        # Technical Analysis (weight: 50%)
        if result['technical']:
            tech = result['technical']
            total_buy += tech['buy_score'] * 0.5
            total_sell += tech['sell_score'] * 0.5

            for sig in tech['signals']:
                if sig[1] == 'BUY':
                    reasons.append(f"✅ {sig[0]}: {sig[2]}")
                elif sig[1] == 'SELL':
                    reasons.append(f"🔴 {sig[0]}: {sig[2]}")

        # News Sentiment (weight: 30%)
        if result['news_sentiment']:
            sent = result['news_sentiment']
            score = sent['score']

            if score > 20:
                total_buy += 30
                reasons.append(f"✅ Nyheder: Positiv sentiment ({score})")
            elif score < -20:
                total_sell += 30
                reasons.append(f"🔴 Nyheder: Negativ sentiment ({score})")

        # Fear & Greed (weight: 20%, crypto only)
        if result['fear_greed']:
            fg = result['fear_greed']
            value = fg['value']

            if value < 25:  # Extreme fear = buy opportunity
                total_buy += 20
                reasons.append(f"✅ Fear & Greed: Ekstrem frygt ({value}) - Købsmulighed")
            elif value > 75:  # Extreme greed = sell signal
                total_sell += 20
                reasons.append(f"🔴 Fear & Greed: Ekstrem grådighed ({value}) - Salgssignal")

        # Calculate final signal
        total = total_buy + total_sell

        if total == 0:
            return "VENT", 50, reasons

        if total_buy > total_sell * 1.3:  # Clear buy signal
            confidence = min(95, (total_buy / total) * 100)
            return "KØB", confidence, reasons
        elif total_sell > total_buy * 1.3:  # Clear sell signal
            confidence = min(95, (total_sell / total) * 100)
            return "SÆLG", confidence, reasons
        else:
            return "VENT", 50, reasons

    def get_market_overview(self, market: str) -> Dict:
        """Get overview of entire market"""
        from config import POPULAR_STOCKS, POPULAR_CRYPTO, POPULAR_FOREX

        symbols = {
            "stocks": POPULAR_STOCKS[:8],
            "crypto": POPULAR_CRYPTO[:8],
            "forex": POPULAR_FOREX[:6]
        }[market]

        results = []
        for symbol in symbols:
            try:
                analysis = self.get_full_analysis(symbol, market)
                if analysis and analysis['price_data']:
                    results.append({
                        'symbol': symbol,
                        'price': analysis['price_data']['current_price'],
                        'change': analysis['price_data']['change_1d'],
                        'signal': analysis['final_signal'],
                        'confidence': analysis['confidence'],
                        'rsi': analysis['technical']['rsi'] if analysis['technical'] else None
                    })
            except Exception:
                continue

        # Sort by signal strength
        buy_signals = [r for r in results if r['signal'] == 'KØB']
        sell_signals = [r for r in results if r['signal'] == 'SÆLG']
        wait_signals = [r for r in results if r['signal'] == 'VENT']

        buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
        sell_signals.sort(key=lambda x: x['confidence'], reverse=True)

        # Get market sentiment
        headlines = self.news_analyzer.get_market_headlines(market, limit=5)
        market_sentiment = self.sentiment_analyzer.analyze_news_batch(headlines)

        # Fear & Greed for crypto
        fear_greed = None
        if market == "crypto":
            fear_greed = self.news_analyzer.get_fear_greed_index()

        return {
            'timestamp': datetime.now().isoformat(),
            'market': market,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'neutral': wait_signals,
            'market_sentiment': market_sentiment,
            'fear_greed': fear_greed,
            'headlines': [h['title'] for h in headlines[:5]]
        }
