"""
Trading Signals Pro - Advanced Multi-Source Analysis Platform
Ultra-secure signals with multi-timeframe confluence analysis
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
import ta
import requests
import feedparser
from textblob import TextBlob
import time

# TradingView Technical Analysis
try:
    from tradingview_ta import TA_Handler, Interval, Exchange
    TRADINGVIEW_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AVAILABLE = False

# Import config
from config import (
    INDUSTRIES, ALL_STOCKS, CRYPTO_SYMBOLS, FOREX_PAIRS,
    NEWS_RSS_FEEDS, API_ENDPOINTS, REFRESH_INTERVAL
)

st.set_page_config(
    page_title="Trading Signals Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== PASSWORD PROTECTION =====
def check_password():
    """Returns True if the user has entered the correct password."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🔐 Trading Signals Pro")
    st.markdown("---")

    password = st.text_input("Indtast adgangskode:", type="password", key="password_input")

    if st.button("Log ind", type="primary"):
        if password == "Money":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Forkert adgangskode. Prøv igen.")

    return False

if not check_password():
    st.stop()

# ===== CACHING FUNCTIONS =====
@st.cache_data(ttl=60)
def fetch_stock_data(symbol, period="6mo", interval="1d"):
    """Fetch stock data with caching"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
        data.columns = [c.lower() for c in data.columns]
        return data
    except:
        return None

@st.cache_data(ttl=60)
def fetch_multi_timeframe_data(symbol):
    """Fetch data for multiple timeframes"""
    timeframes = {}
    try:
        ticker = yf.Ticker(symbol)

        # Daily data (6 months)
        daily = ticker.history(period="6mo", interval="1d")
        if not daily.empty:
            daily.columns = [c.lower() for c in daily.columns]
            timeframes['1D'] = daily

        # Weekly data (2 years)
        weekly = ticker.history(period="2y", interval="1wk")
        if not weekly.empty:
            weekly.columns = [c.lower() for c in weekly.columns]
            timeframes['1W'] = weekly

        # Monthly data (5 years)
        monthly = ticker.history(period="5y", interval="1mo")
        if not monthly.empty:
            monthly.columns = [c.lower() for c in monthly.columns]
            timeframes['1M'] = monthly

    except:
        pass

    return timeframes

@st.cache_data(ttl=300)
def fetch_news_sentiment(keywords, max_articles=20):
    """Fetch and analyze news from multiple sources"""
    articles = []

    for source, url in list(NEWS_RSS_FEEDS.items())[:8]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))[:200]
                if any(kw.lower() in (title + summary).lower() for kw in keywords):
                    articles.append({
                        'source': source,
                        'title': title,
                        'summary': summary,
                        'link': entry.get('link', '')
                    })
        except:
            continue

    # Analyze sentiment
    sentiments = []
    for article in articles[:max_articles]:
        text = article['title'] + ' ' + article['summary']
        blob = TextBlob(text)
        score = blob.sentiment.polarity

        # Financial keyword boost
        text_lower = text.lower()
        bullish = ['surge', 'rally', 'gain', 'rise', 'bullish', 'breakout', 'buy', 'upgrade', 'beat', 'record', 'soar', 'jump']
        bearish = ['crash', 'plunge', 'drop', 'fall', 'bearish', 'dump', 'sell', 'downgrade', 'miss', 'fear', 'tank', 'sink']

        for word in bullish:
            if word in text_lower:
                score += 0.15
        for word in bearish:
            if word in text_lower:
                score -= 0.15

        article['sentiment'] = max(-1, min(1, score))
        sentiments.append(score)

    avg_sentiment = np.mean(sentiments) if sentiments else 0
    return articles, avg_sentiment

@st.cache_data(ttl=60)
def get_fear_greed_index():
    """Get Fear & Greed Index for crypto"""
    try:
        response = requests.get(API_ENDPOINTS['fear_greed_crypto'], timeout=5)
        data = response.json()
        return {
            'value': int(data['data'][0]['value']),
            'label': data['data'][0]['value_classification']
        }
    except:
        return None

@st.cache_data(ttl=120)
def get_tradingview_analysis(symbol, exchange="NASDAQ", screener="america"):
    """Get TradingView technical analysis for multiple timeframes"""
    if not TRADINGVIEW_AVAILABLE:
        return None

    results = {}
    intervals = [
        (Interval.INTERVAL_1_DAY, '1D'),
        (Interval.INTERVAL_1_WEEK, '1W'),
        (Interval.INTERVAL_1_MONTH, '1M'),
    ]

    try:
        # Clean symbol for TradingView
        clean_symbol = symbol.replace('-USD', '').replace('=X', '').replace('-', '')

        # Determine exchange and screener
        if 'USD' in symbol or symbol in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE']:
            exchange = "BINANCE"
            screener = "crypto"
            clean_symbol = symbol.replace('-USD', '') + "USDT"
        elif '=X' in symbol:
            exchange = "FX_IDC"
            screener = "forex"
        else:
            # Try common exchanges for stocks
            for ex in ["NASDAQ", "NYSE", "AMEX"]:
                try:
                    handler = TA_Handler(
                        symbol=clean_symbol,
                        exchange=ex,
                        screener=screener,
                        interval=Interval.INTERVAL_1_DAY,
                        timeout=10
                    )
                    analysis = handler.get_analysis()
                    if analysis:
                        exchange = ex
                        break
                except:
                    continue

        for interval, name in intervals:
            try:
                handler = TA_Handler(
                    symbol=clean_symbol,
                    exchange=exchange,
                    screener=screener,
                    interval=interval,
                    timeout=10
                )
                analysis = handler.get_analysis()
                results[name] = {
                    'summary': analysis.summary,
                    'oscillators': analysis.oscillators,
                    'moving_averages': analysis.moving_averages,
                    'indicators': analysis.indicators
                }
            except:
                continue

        return results if results else None
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def get_finnhub_sentiment(symbol):
    """Get news sentiment from Finnhub (free tier)"""
    try:
        url = f"https://finnhub.io/api/v1/stock/social-sentiment?symbol={symbol}&token=demo"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('reddit') or data.get('twitter'):
                reddit = data.get('reddit', [{}])
                twitter = data.get('twitter', [{}])
                reddit_score = reddit[-1].get('score', 0) if reddit else 0
                twitter_score = twitter[-1].get('score', 0) if twitter else 0
                return {
                    'reddit_sentiment': reddit_score,
                    'twitter_sentiment': twitter_score,
                    'combined': (reddit_score + twitter_score) / 2
                }
    except:
        pass
    return None

@st.cache_data(ttl=600)
def get_analyst_ratings(symbol):
    """Get analyst recommendations from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        recommendations = ticker.recommendations
        if recommendations is not None and len(recommendations) > 0:
            latest = recommendations.tail(5)
            buy_count = latest['strongBuy'].sum() + latest['buy'].sum()
            sell_count = latest['strongSell'].sum() + latest['sell'].sum()
            hold_count = latest['hold'].sum()

            total = buy_count + sell_count + hold_count
            if total > 0:
                return {
                    'buy': buy_count,
                    'sell': sell_count,
                    'hold': hold_count,
                    'rating': 'BUY' if buy_count > sell_count else 'SELL' if sell_count > buy_count else 'HOLD',
                    'buy_pct': (buy_count / total) * 100
                }
    except:
        pass
    return None

@st.cache_data(ttl=300)
def get_stock_info(symbol):
    """Get additional stock info from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 0),
            '52w_high': info.get('fiftyTwoWeekHigh', 0),
            '52w_low': info.get('fiftyTwoWeekLow', 0),
            'avg_volume': info.get('averageVolume', 0),
            'short_name': info.get('shortName', symbol),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown')
        }
    except:
        return None

# ===== ADVANCED TECHNICAL ANALYSIS =====
def calculate_indicators(data):
    """Calculate comprehensive technical indicators"""
    if data is None or len(data) < 50:
        return None

    df = data.copy()

    # Momentum Indicators
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['rsi_6'] = ta.momentum.rsi(df['close'], window=6)  # Fast RSI
    df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'], window=14)
    df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'], window=14)
    df['cci'] = ta.trend.cci(df['high'], df['low'], df['close'], window=20)
    df['williams_r'] = ta.momentum.williams_r(df['high'], df['low'], df['close'], lbp=14)
    df['roc'] = ta.momentum.roc(df['close'], window=12)
    df['ultimate_osc'] = ta.momentum.ultimate_oscillator(df['high'], df['low'], df['close'])

    # Trend Indicators
    df['sma_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
    df['sma_100'] = ta.trend.sma_indicator(df['close'], window=100)
    df['sma_200'] = ta.trend.sma_indicator(df['close'], window=200)
    df['ema_9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
    df['ema_21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)

    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()

    df['adx'] = ta.trend.adx(df['high'], df['low'], df['close'], window=14)
    df['adx_pos'] = ta.trend.adx_pos(df['high'], df['low'], df['close'], window=14)
    df['adx_neg'] = ta.trend.adx_neg(df['high'], df['low'], df['close'], window=14)

    # Ichimoku Cloud
    df['ichimoku_a'] = ta.trend.ichimoku_a(df['high'], df['low'])
    df['ichimoku_b'] = ta.trend.ichimoku_b(df['high'], df['low'])
    df['ichimoku_base'] = ta.trend.ichimoku_base_line(df['high'], df['low'])
    df['ichimoku_conv'] = ta.trend.ichimoku_conversion_line(df['high'], df['low'])

    # Volatility Indicators
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_middle'] = bb.bollinger_mavg()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = bb.bollinger_wband()
    df['bb_pct'] = bb.bollinger_pband()

    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'], window=20)
    df['kc_upper'] = kc.keltner_channel_hband()
    df['kc_lower'] = kc.keltner_channel_lband()
    df['kc_middle'] = kc.keltner_channel_mband()

    # Volume Indicators
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['mfi'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=14)
    df['volume_sma'] = df['volume'].rolling(window=20).mean()
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    df['cmf'] = ta.volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume'], window=20)
    df['force_index'] = ta.volume.force_index(df['close'], df['volume'], window=13)

    # Calculate Support and Resistance
    df['pivot'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['r1'] = 2 * df['pivot'] - df['low'].shift(1)
    df['s1'] = 2 * df['pivot'] - df['high'].shift(1)
    df['r2'] = df['pivot'] + (df['high'].shift(1) - df['low'].shift(1))
    df['s2'] = df['pivot'] - (df['high'].shift(1) - df['low'].shift(1))
    df['r3'] = df['high'].shift(1) + 2 * (df['pivot'] - df['low'].shift(1))
    df['s3'] = df['low'].shift(1) - 2 * (df['high'].shift(1) - df['pivot'])

    # Volatility metrics
    df['daily_return'] = df['close'].pct_change()
    df['volatility_20'] = df['daily_return'].rolling(window=20).std() * np.sqrt(252) * 100

    # Calculate drawdown
    df['cummax'] = df['close'].cummax()
    df['drawdown'] = (df['close'] - df['cummax']) / df['cummax'] * 100

    return df

def calculate_support_resistance(data, window=20):
    """Calculate key support and resistance levels"""
    if data is None or len(data) < window:
        return []

    levels = []
    highs = data['high'].values
    lows = data['low'].values
    closes = data['close'].values

    # Find local maxima and minima
    for i in range(window, len(data) - window):
        # Resistance (local high)
        if highs[i] == max(highs[i-window:i+window+1]):
            levels.append({'price': highs[i], 'type': 'resistance', 'strength': 1})
        # Support (local low)
        if lows[i] == min(lows[i-window:i+window+1]):
            levels.append({'price': lows[i], 'type': 'support', 'strength': 1})

    # Consolidate nearby levels
    consolidated = []
    threshold = closes[-1] * 0.02  # 2% threshold

    for level in sorted(levels, key=lambda x: x['price']):
        merged = False
        for c in consolidated:
            if abs(c['price'] - level['price']) < threshold:
                c['strength'] += 1
                c['price'] = (c['price'] + level['price']) / 2
                merged = True
                break
        if not merged:
            consolidated.append(level)

    # Sort by strength and return top levels
    return sorted(consolidated, key=lambda x: -x['strength'])[:8]

def calculate_confluence_score(data, tf_signals, tv_analysis, news_sentiment, fear_greed, analyst_ratings):
    """Calculate confluence score from multiple sources and timeframes"""

    confluence = {
        'sources': {},
        'total_bullish': 0,
        'total_bearish': 0,
        'total_sources': 0,
        'score': 0,
        'confidence': 'LAV'
    }

    # 1. Technical Indicators (Local calculation)
    if data is not None and len(data) >= 2:
        latest = data.iloc[-1]
        bullish = 0
        bearish = 0

        # RSI
        rsi = latest.get('rsi')
        if rsi:
            if rsi < 30: bullish += 2
            elif rsi < 40: bullish += 1
            elif rsi > 70: bearish += 2
            elif rsi > 60: bearish += 1

        # MACD
        macd_hist = latest.get('macd_hist')
        if macd_hist is not None:
            if macd_hist > 0: bullish += 1
            else: bearish += 1

        # Moving Averages
        price = latest['close']
        sma_20 = latest.get('sma_20')
        sma_50 = latest.get('sma_50')
        sma_200 = latest.get('sma_200')

        if sma_20 and price > sma_20: bullish += 1
        elif sma_20: bearish += 1

        if sma_50 and price > sma_50: bullish += 1
        elif sma_50: bearish += 1

        if sma_200 and price > sma_200: bullish += 2  # Golden/Death cross weight
        elif sma_200: bearish += 2

        # Stochastic
        stoch_k = latest.get('stoch_k')
        if stoch_k:
            if stoch_k < 20: bullish += 1
            elif stoch_k > 80: bearish += 1

        # CCI
        cci = latest.get('cci')
        if cci:
            if cci < -100: bullish += 1
            elif cci > 100: bearish += 1

        # MFI
        mfi = latest.get('mfi')
        if mfi:
            if mfi < 20: bullish += 1
            elif mfi > 80: bearish += 1

        # Bollinger Bands
        bb_pct = latest.get('bb_pct')
        if bb_pct is not None:
            if bb_pct < 0: bullish += 1
            elif bb_pct > 1: bearish += 1

        # Ichimoku
        ichimoku_a = latest.get('ichimoku_a')
        ichimoku_b = latest.get('ichimoku_b')
        if ichimoku_a and ichimoku_b:
            if price > ichimoku_a and price > ichimoku_b: bullish += 2
            elif price < ichimoku_a and price < ichimoku_b: bearish += 2

        total = bullish + bearish
        if total > 0:
            if bullish > bearish:
                confluence['sources']['Teknisk Analyse'] = {'signal': 'KØB', 'strength': bullish / total}
            elif bearish > bullish:
                confluence['sources']['Teknisk Analyse'] = {'signal': 'SÆLG', 'strength': bearish / total}
            else:
                confluence['sources']['Teknisk Analyse'] = {'signal': 'NEUTRAL', 'strength': 0.5}

            confluence['total_bullish'] += bullish
            confluence['total_bearish'] += bearish
            confluence['total_sources'] += 1

    # 2. Multi-Timeframe TradingView Analysis
    if tv_analysis:
        for tf, analysis in tv_analysis.items():
            summary = analysis.get('summary', {})
            rec = summary.get('RECOMMENDATION', 'NEUTRAL')
            buy_count = summary.get('BUY', 0)
            sell_count = summary.get('SELL', 0)

            if rec in ['STRONG_BUY', 'BUY']:
                confluence['sources'][f'TradingView {tf}'] = {'signal': 'KØB', 'strength': buy_count / max(1, buy_count + sell_count)}
                confluence['total_bullish'] += 2 if rec == 'STRONG_BUY' else 1
            elif rec in ['STRONG_SELL', 'SELL']:
                confluence['sources'][f'TradingView {tf}'] = {'signal': 'SÆLG', 'strength': sell_count / max(1, buy_count + sell_count)}
                confluence['total_bearish'] += 2 if rec == 'STRONG_SELL' else 1
            else:
                confluence['sources'][f'TradingView {tf}'] = {'signal': 'NEUTRAL', 'strength': 0.5}

            confluence['total_sources'] += 1

    # 3. News Sentiment
    if news_sentiment:
        if news_sentiment > 0.2:
            confluence['sources']['Nyheder'] = {'signal': 'KØB', 'strength': min(1, news_sentiment)}
            confluence['total_bullish'] += 1
        elif news_sentiment < -0.2:
            confluence['sources']['Nyheder'] = {'signal': 'SÆLG', 'strength': min(1, abs(news_sentiment))}
            confluence['total_bearish'] += 1
        else:
            confluence['sources']['Nyheder'] = {'signal': 'NEUTRAL', 'strength': 0.5}
        confluence['total_sources'] += 1

    # 4. Fear & Greed Index
    if fear_greed:
        fg_value = fear_greed['value']
        if fg_value < 25:
            confluence['sources']['Fear & Greed'] = {'signal': 'KØB', 'strength': (50 - fg_value) / 50}
            confluence['total_bullish'] += 2
        elif fg_value > 75:
            confluence['sources']['Fear & Greed'] = {'signal': 'SÆLG', 'strength': (fg_value - 50) / 50}
            confluence['total_bearish'] += 2
        else:
            confluence['sources']['Fear & Greed'] = {'signal': 'NEUTRAL', 'strength': 0.5}
        confluence['total_sources'] += 1

    # 5. Analyst Ratings
    if analyst_ratings:
        buy_pct = analyst_ratings.get('buy_pct', 50)
        if buy_pct > 65:
            confluence['sources']['Analytikere'] = {'signal': 'KØB', 'strength': buy_pct / 100}
            confluence['total_bullish'] += 1
        elif buy_pct < 35:
            confluence['sources']['Analytikere'] = {'signal': 'SÆLG', 'strength': (100 - buy_pct) / 100}
            confluence['total_bearish'] += 1
        else:
            confluence['sources']['Analytikere'] = {'signal': 'NEUTRAL', 'strength': 0.5}
        confluence['total_sources'] += 1

    # Calculate final confluence score
    total = confluence['total_bullish'] + confluence['total_bearish']
    if total > 0:
        if confluence['total_bullish'] > confluence['total_bearish']:
            confluence['score'] = (confluence['total_bullish'] / total) * 100
            confluence['signal'] = 'KØB'
        else:
            confluence['score'] = (confluence['total_bearish'] / total) * 100
            confluence['signal'] = 'SÆLG'
    else:
        confluence['score'] = 50
        confluence['signal'] = 'NEUTRAL'

    # Determine confidence based on agreement
    agreeing_sources = sum(1 for s in confluence['sources'].values() if s['signal'] == confluence.get('signal', 'NEUTRAL'))
    agreement_pct = agreeing_sources / max(1, confluence['total_sources']) * 100

    if agreement_pct >= 80 and confluence['total_sources'] >= 4:
        confluence['confidence'] = 'MEGET HØJ'
    elif agreement_pct >= 65 and confluence['total_sources'] >= 3:
        confluence['confidence'] = 'HØJ'
    elif agreement_pct >= 50:
        confluence['confidence'] = 'MEDIUM'
    else:
        confluence['confidence'] = 'LAV'

    return confluence

def calculate_risk_metrics(data):
    """Calculate risk metrics"""
    if data is None or len(data) < 20:
        return None

    metrics = {}

    # Volatility
    metrics['volatility_20d'] = data['volatility_20'].iloc[-1] if 'volatility_20' in data else 0

    # Max drawdown (last 6 months)
    metrics['max_drawdown'] = data['drawdown'].min() if 'drawdown' in data else 0

    # Current drawdown
    metrics['current_drawdown'] = data['drawdown'].iloc[-1] if 'drawdown' in data else 0

    # ATR percentage
    metrics['atr_pct'] = data['atr_pct'].iloc[-1] if 'atr_pct' in data else 0

    # Sharpe-like ratio (simplified)
    returns = data['daily_return'].dropna()
    if len(returns) > 0:
        avg_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)
        metrics['sharpe_ratio'] = avg_return / std_return if std_return > 0 else 0
    else:
        metrics['sharpe_ratio'] = 0

    # Risk level
    if metrics['volatility_20d'] > 50 or metrics['max_drawdown'] < -30:
        metrics['risk_level'] = 'HØJ RISIKO'
        metrics['risk_color'] = 'red'
    elif metrics['volatility_20d'] > 25 or metrics['max_drawdown'] < -15:
        metrics['risk_level'] = 'MEDIUM RISIKO'
        metrics['risk_color'] = 'orange'
    else:
        metrics['risk_level'] = 'LAV RISIKO'
        metrics['risk_color'] = 'green'

    return metrics

def generate_final_signal(confluence, risk_metrics):
    """Generate final signal with risk adjustment"""

    signal = confluence.get('signal', 'NEUTRAL')
    score = confluence.get('score', 50)
    confidence = confluence.get('confidence', 'LAV')

    # Risk adjustment
    if risk_metrics:
        if risk_metrics.get('risk_level') == 'HØJ RISIKO':
            score = score * 0.7  # Reduce confidence for high risk
            if confidence == 'MEGET HØJ':
                confidence = 'HØJ'
            elif confidence == 'HØJ':
                confidence = 'MEDIUM'

    # Final recommendation
    if score >= 70 and confidence in ['HØJ', 'MEGET HØJ']:
        if signal == 'KØB':
            recommendation = 'STÆRK KØB'
        else:
            recommendation = 'STÆRK SÆLG'
    elif score >= 55:
        recommendation = signal
    else:
        recommendation = 'VENT'

    return {
        'signal': recommendation,
        'score': score,
        'confidence': confidence,
        'original_signal': signal
    }

def scan_industry(industry_name, stocks, progress_callback=None):
    """Scan all stocks in an industry for signals"""
    results = []
    total = len(stocks)

    for i, symbol in enumerate(stocks):
        if progress_callback:
            progress_callback((i + 1) / total)

        try:
            data = fetch_stock_data(symbol, period="3mo")
            if data is None or len(data) < 50:
                continue

            data = calculate_indicators(data)
            confluence = calculate_confluence_score(data, {}, None, 0, None, None)

            latest = data.iloc[-1]
            prev = data.iloc[-2]
            change = ((latest['close'] / prev['close']) - 1) * 100

            results.append({
                'Symbol': symbol,
                'Pris': latest['close'],
                'Ændring': change,
                'RSI': latest.get('rsi', 0),
                'Signal': confluence.get('signal', 'NEUTRAL'),
                'Score': confluence.get('score', 50)
            })
        except Exception:
            continue

        time.sleep(0.1)

    return results

# ===== STREAMLIT UI =====
st.title("📈 Trading Signals Pro - Advanced Analysis")

# Sidebar
st.sidebar.title("⚙️ Indstillinger")

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("🔄 Auto-opdatering (30 sek)", value=False)
if auto_refresh:
    st.sidebar.info(f"Opdaterer automatisk hvert {REFRESH_INTERVAL} sekund")

# Mode selection
mode = st.sidebar.radio("📊 Tilstand", ["Fuld Analyse", "Industri Scanner", "Marked Oversigt"])

# Market selection
market = st.sidebar.selectbox("🌍 Marked", ["Aktier", "Crypto", "Forex"])

# Time display
st.sidebar.markdown("---")
st.sidebar.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Fear & Greed for crypto
if market == "Crypto":
    fg = get_fear_greed_index()
    if fg:
        st.sidebar.markdown(f"### 😱 Fear & Greed: {fg['value']}")
        st.sidebar.caption(fg['label'])

# ===== MAIN CONTENT =====
if mode == "Fuld Analyse":
    col1, col2 = st.columns([1, 3])

    with col1:
        if market == "Aktier":
            industry = st.selectbox("Industri", list(INDUSTRIES.keys()))
            symbol = st.selectbox("Symbol", INDUSTRIES[industry])
        elif market == "Crypto":
            symbol = st.selectbox("Symbol", CRYPTO_SYMBOLS)
        else:
            symbol = st.selectbox("Symbol", FOREX_PAIRS)

        analyze_btn = st.button("🔍 Fuld Analyse", type="primary", use_container_width=True)

    if analyze_btn or auto_refresh:
        with st.spinner(f"Udfører fuld analyse af {symbol}..."):
            # Fetch multi-timeframe data
            tf_data = fetch_multi_timeframe_data(symbol)
            data = tf_data.get('1D')

            if data is None or len(data) < 50:
                st.error("Kunne ikke hente nok data for dette symbol")
                st.stop()

            # Calculate indicators
            data = calculate_indicators(data)

            # Get all external data
            keywords = [symbol.split('-')[0], symbol.replace('-USD', '')]
            articles, news_sentiment = fetch_news_sentiment(keywords)
            fg = get_fear_greed_index() if market == "Crypto" else None
            tv_analysis = get_tradingview_analysis(symbol)
            analyst_ratings = get_analyst_ratings(symbol)
            stock_info = get_stock_info(symbol)

            # Calculate support/resistance
            sr_levels = calculate_support_resistance(data)

            # Calculate risk metrics
            risk_metrics = calculate_risk_metrics(data)

            # Calculate confluence score
            confluence = calculate_confluence_score(
                data, tf_data, tv_analysis, news_sentiment, fg, analyst_ratings
            )

            # Generate final signal
            final = generate_final_signal(confluence, risk_metrics)

            latest = data.iloc[-1]
            prev = data.iloc[-2]
            price = latest['close']
            change_1d = ((price / prev['close']) - 1) * 100

        # ===== DISPLAY RESULTS =====

        # Top row: Signal and Key Metrics
        st.markdown("---")
        col_sig, col_conf, col_risk, col_price = st.columns(4)

        with col_sig:
            signal_color = "green" if "KØB" in final['signal'] else "red" if "SÆLG" in final['signal'] else "orange"
            st.markdown(f"""
            <div style="background-color: {signal_color}; padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: white; margin: 0;">{'🟢' if 'KØB' in final['signal'] else '🔴' if 'SÆLG' in final['signal'] else '🟡'} {final['signal']}</h2>
            </div>
            """, unsafe_allow_html=True)

        with col_conf:
            st.metric("Confluence Score", f"{final['score']:.0f}%")
            st.caption(f"Sikkerhed: {final['confidence']}")

        with col_risk:
            if risk_metrics:
                st.metric("Risiko", risk_metrics['risk_level'])
                st.caption(f"Volatilitet: {risk_metrics['volatility_20d']:.1f}%")

        with col_price:
            st.metric("Pris", f"${price:,.2f}", f"{change_1d:+.2f}%")

        # Confluence Breakdown
        st.markdown("---")
        st.subheader("🎯 Confluence Analyse - Alle Kilder")

        source_cols = st.columns(min(6, len(confluence['sources'])))
        for i, (source, data_src) in enumerate(confluence['sources'].items()):
            with source_cols[i % len(source_cols)]:
                emoji = "🟢" if data_src['signal'] == 'KØB' else "🔴" if data_src['signal'] == 'SÆLG' else "🟡"
                strength_bar = "█" * int(data_src['strength'] * 5)
                st.markdown(f"""
                **{source}**
                {emoji} {data_src['signal']}
                Styrke: {strength_bar}
                """)

        # Charts and Analysis
        st.markdown("---")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Pris Chart", "📊 Indikatorer", "🎯 Support/Resistance", "⚠️ Risiko", "📰 Nyheder"])

        with tab1:
            # Advanced price chart
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                               vertical_spacing=0.03,
                               row_heights=[0.5, 0.15, 0.15, 0.2],
                               subplot_titles=[f'{symbol} - Pris med Indikatorer', 'RSI', 'MACD', 'Volumen'])

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['open'], high=data['high'],
                low=data['low'], close=data['close'], name='Pris'
            ), row=1, col=1)

            # Bollinger Bands
            fig.add_trace(go.Scatter(x=data.index, y=data['bb_upper'],
                line=dict(color='rgba(128,128,128,0.5)', width=1), name='BB Upper', showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['bb_lower'],
                line=dict(color='rgba(128,128,128,0.5)', width=1), name='BB Lower',
                fill='tonexty', fillcolor='rgba(128,128,128,0.1)', showlegend=False), row=1, col=1)

            # Moving Averages
            fig.add_trace(go.Scatter(x=data.index, y=data['sma_20'],
                line=dict(color='orange', width=1), name='SMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['sma_50'],
                line=dict(color='blue', width=1), name='SMA 50'), row=1, col=1)
            if 'sma_200' in data and not data['sma_200'].isna().all():
                fig.add_trace(go.Scatter(x=data.index, y=data['sma_200'],
                    line=dict(color='red', width=1), name='SMA 200'), row=1, col=1)

            # Support/Resistance lines
            for level in sr_levels[:4]:
                color = 'green' if level['type'] == 'support' else 'red'
                fig.add_hline(y=level['price'], line_dash="dash", line_color=color,
                             opacity=0.5, row=1, col=1)

            # RSI
            fig.add_trace(go.Scatter(x=data.index, y=data['rsi'],
                line=dict(color='purple', width=1), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, row=2, col=1)

            # MACD
            colors = ['green' if v >= 0 else 'red' for v in data['macd_hist']]
            fig.add_trace(go.Bar(x=data.index, y=data['macd_hist'],
                marker_color=colors, name='MACD Hist'), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['macd'],
                line=dict(color='blue', width=1), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['macd_signal'],
                line=dict(color='orange', width=1), name='Signal'), row=3, col=1)

            # Volume
            vol_colors = ['green' if data['close'].iloc[i] >= data['open'].iloc[i] else 'red'
                         for i in range(len(data))]
            fig.add_trace(go.Bar(x=data.index, y=data['volume'],
                marker_color=vol_colors, name='Volume', opacity=0.7), row=4, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['volume_sma'],
                line=dict(color='blue', width=1), name='Vol SMA'), row=4, col=1)

            fig.update_layout(
                height=800,
                template='plotly_dark',
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            col_ind1, col_ind2, col_ind3 = st.columns(3)

            with col_ind1:
                st.markdown("### Momentum")
                rsi = latest.get('rsi', 0)
                stoch = latest.get('stoch_k', 0)
                mfi = latest.get('mfi', 0)
                cci = latest.get('cci', 0)
                williams = latest.get('williams_r', 0)

                st.metric("RSI (14)", f"{rsi:.1f}",
                         "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral")
                st.metric("Stochastic K", f"{stoch:.1f}",
                         "Oversold" if stoch < 20 else "Overbought" if stoch > 80 else "Neutral")
                st.metric("MFI", f"{mfi:.1f}",
                         "Oversold" if mfi < 20 else "Overbought" if mfi > 80 else "Neutral")
                st.metric("CCI", f"{cci:.0f}",
                         "Oversold" if cci < -100 else "Overbought" if cci > 100 else "Neutral")
                st.metric("Williams %R", f"{williams:.1f}",
                         "Oversold" if williams < -80 else "Overbought" if williams > -20 else "Neutral")

            with col_ind2:
                st.markdown("### Trend")
                adx = latest.get('adx', 0)
                macd_h = latest.get('macd_hist', 0)

                # MA positions
                st.metric("ADX (Trend Styrke)", f"{adx:.1f}",
                         "Stærk" if adx > 25 else "Svag")
                st.metric("MACD Histogram", f"{macd_h:.4f}",
                         "Bullish" if macd_h > 0 else "Bearish")

                # Price vs MAs
                st.markdown("**Pris vs Moving Averages:**")
                mas = [('SMA 20', 'sma_20'), ('SMA 50', 'sma_50'), ('SMA 200', 'sma_200')]
                for name, col in mas:
                    if col in latest and not pd.isna(latest[col]):
                        status = "✅ Over" if price > latest[col] else "❌ Under"
                        st.write(f"{name}: {status} ({latest[col]:.2f})")

            with col_ind3:
                st.markdown("### Volatilitet")
                atr = latest.get('atr', 0)
                atr_pct = latest.get('atr_pct', 0)
                bb_width = latest.get('bb_width', 0)
                bb_pct = latest.get('bb_pct', 0)

                st.metric("ATR", f"${atr:.2f}", f"{atr_pct:.1f}% af pris")
                st.metric("Bollinger Band %B", f"{bb_pct:.2f}",
                         "Oversold" if bb_pct < 0 else "Overbought" if bb_pct > 1 else "Normal")
                st.metric("BB Width", f"{bb_width:.4f}")

                if risk_metrics:
                    st.metric("20-dages Volatilitet", f"{risk_metrics['volatility_20d']:.1f}%")

        with tab3:
            st.markdown("### 🎯 Support & Resistance Niveauer")

            col_sr1, col_sr2 = st.columns(2)

            with col_sr1:
                st.markdown("**Pivot Points:**")
                st.write(f"Pivot: ${latest.get('pivot', 0):.2f}")
                st.write(f"R1: ${latest.get('r1', 0):.2f}")
                st.write(f"R2: ${latest.get('r2', 0):.2f}")
                st.write(f"R3: ${latest.get('r3', 0):.2f}")

            with col_sr2:
                st.markdown("**Support Niveauer:**")
                st.write(f"S1: ${latest.get('s1', 0):.2f}")
                st.write(f"S2: ${latest.get('s2', 0):.2f}")
                st.write(f"S3: ${latest.get('s3', 0):.2f}")

            st.markdown("---")
            st.markdown("**Identificerede Nøgle-niveauer:**")

            for level in sr_levels:
                emoji = "🟢" if level['type'] == 'support' else "🔴"
                strength_bar = "█" * level['strength']
                pct_from_price = ((level['price'] - price) / price) * 100
                st.write(f"{emoji} {level['type'].upper()}: ${level['price']:.2f} ({pct_from_price:+.1f}% fra nuværende pris) | Styrke: {strength_bar}")

        with tab4:
            if risk_metrics:
                st.markdown("### ⚠️ Risiko Analyse")

                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    st.metric("Risiko Niveau", risk_metrics['risk_level'])
                    st.metric("20-dages Volatilitet", f"{risk_metrics['volatility_20d']:.1f}%")
                    st.metric("ATR %", f"{risk_metrics['atr_pct']:.2f}%")

                with col_r2:
                    st.metric("Max Drawdown (6M)", f"{risk_metrics['max_drawdown']:.1f}%")
                    st.metric("Current Drawdown", f"{risk_metrics['current_drawdown']:.1f}%")
                    st.metric("Sharpe Ratio (approx)", f"{risk_metrics['sharpe_ratio']:.2f}")

                # Drawdown chart
                st.markdown("### Drawdown Over Tid")
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=data.index, y=data['drawdown'],
                    fill='tozeroy', fillcolor='rgba(255,0,0,0.3)',
                    line=dict(color='red', width=1),
                    name='Drawdown %'
                ))
                fig_dd.update_layout(height=300, template='plotly_dark')
                st.plotly_chart(fig_dd, use_container_width=True)

        with tab5:
            st.markdown("### 📰 Nyheds Sentiment")
            st.metric("Samlet Sentiment", f"{news_sentiment:.2f}",
                     "Positiv" if news_sentiment > 0.1 else "Negativ" if news_sentiment < -0.1 else "Neutral")

            if articles:
                for article in articles[:5]:
                    sentiment_emoji = "🟢" if article['sentiment'] > 0.1 else "🔴" if article['sentiment'] < -0.1 else "⚪"
                    st.markdown(f"""
                    {sentiment_emoji} **{article['source']}**
                    {article['title'][:100]}...
                    *Sentiment: {article['sentiment']:.2f}*
                    """)
                    st.markdown("---")
            else:
                st.info("Ingen relevante nyheder fundet")

        # Stock Info
        if stock_info:
            st.markdown("---")
            st.subheader("📊 Aktie Information")
            info_cols = st.columns(4)
            with info_cols[0]:
                st.metric("Sektor", stock_info.get('sector', 'N/A'))
            with info_cols[1]:
                pe = stock_info.get('pe_ratio', 0)
                st.metric("P/E Ratio", f"{pe:.1f}" if pe else "N/A")
            with info_cols[2]:
                st.metric("52u Høj", f"${stock_info.get('52w_high', 0):,.2f}")
            with info_cols[3]:
                st.metric("52u Lav", f"${stock_info.get('52w_low', 0):,.2f}")

elif mode == "Industri Scanner":
    st.subheader("🔍 Industri Scanner - Find de bedste muligheder")

    if market == "Aktier":
        industry = st.selectbox("Vælg industri at scanne", list(INDUSTRIES.keys()))
        stocks_to_scan = INDUSTRIES[industry]
    elif market == "Crypto":
        industry = "Crypto"
        stocks_to_scan = CRYPTO_SYMBOLS
    else:
        industry = "Forex"
        stocks_to_scan = FOREX_PAIRS

    st.info(f"Scanner {len(stocks_to_scan)} symboler i {industry}...")

    if st.button("🚀 Start Scanner", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(progress):
            progress_bar.progress(progress)
            status_text.text(f"Scanner... {int(progress * 100)}%")

        results = scan_industry(industry, stocks_to_scan, update_progress)

        progress_bar.empty()
        status_text.empty()

        if results:
            df = pd.DataFrame(results)

            # Split by signal
            buy_signals = df[df['Signal'] == 'KØB'].sort_values('Score', ascending=False)
            sell_signals = df[df['Signal'] == 'SÆLG'].sort_values('Score', ascending=False)
            wait_signals = df[df['Signal'] == 'NEUTRAL']

            col1, col2, col3 = st.columns(3)

            with col1:
                st.success(f"### 🟢 KØB Signaler ({len(buy_signals)})")
                if not buy_signals.empty:
                    for _, row in buy_signals.head(10).iterrows():
                        st.write(f"**{row['Symbol']}** - ${row['Pris']:.2f} ({row['Ændring']:+.1f}%)")
                        st.caption(f"RSI: {row['RSI']:.0f} | Score: {row['Score']:.0f}%")

            with col2:
                st.error(f"### 🔴 SÆLG Signaler ({len(sell_signals)})")
                if not sell_signals.empty:
                    for _, row in sell_signals.head(10).iterrows():
                        st.write(f"**{row['Symbol']}** - ${row['Pris']:.2f} ({row['Ændring']:+.1f}%)")
                        st.caption(f"RSI: {row['RSI']:.0f} | Score: {row['Score']:.0f}%")

            with col3:
                st.warning(f"### 🟡 NEUTRAL ({len(wait_signals)})")
                if not wait_signals.empty:
                    for _, row in wait_signals.head(10).iterrows():
                        st.write(f"**{row['Symbol']}** - ${row['Pris']:.2f} ({row['Ændring']:+.1f}%)")

            # Full table
            st.divider()
            st.subheader("📊 Alle resultater")

            def color_signal(val):
                if val == 'KØB':
                    return 'background-color: green; color: white'
                elif val == 'SÆLG':
                    return 'background-color: red; color: white'
                return ''

            styled_df = df.style.map(color_signal, subset=['Signal'])
            styled_df = styled_df.format({
                'Pris': '${:.2f}',
                'Ændring': '{:+.2f}%',
                'RSI': '{:.1f}',
                'Score': '{:.0f}%'
            })
            st.dataframe(styled_df, use_container_width=True)

else:  # Marked Oversigt
    st.subheader("🌍 Marked Oversigt")

    overview_data = []

    progress_bar = st.progress(0)
    industries_list = list(INDUSTRIES.items()) if market == "Aktier" else [("Crypto", CRYPTO_SYMBOLS[:10])]

    for i, (ind_name, stocks) in enumerate(industries_list):
        progress_bar.progress((i + 1) / len(industries_list))

        buy_count = 0
        sell_count = 0

        for symbol in stocks[:5]:
            try:
                data = fetch_stock_data(symbol)
                if data is not None and len(data) >= 50:
                    data = calculate_indicators(data)
                    confluence = calculate_confluence_score(data, {}, None, 0, None, None)
                    if confluence.get('signal') == "KØB":
                        buy_count += 1
                    elif confluence.get('signal') == "SÆLG":
                        sell_count += 1
            except:
                continue

        overview_data.append({
            'Industri': ind_name,
            'KØB': buy_count,
            'SÆLG': sell_count,
            'Sentiment': '🟢' if buy_count > sell_count else '🔴' if sell_count > buy_count else '🟡'
        })

    progress_bar.empty()

    if overview_data:
        df = pd.DataFrame(overview_data)
        st.dataframe(df, use_container_width=True)

        # Visual chart
        fig = go.Figure()
        fig.add_trace(go.Bar(name='KØB', x=df['Industri'], y=df['KØB'], marker_color='green'))
        fig.add_trace(go.Bar(name='SÆLG', x=df['Industri'], y=df['SÆLG'], marker_color='red'))
        fig.update_layout(barmode='group', height=400, template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)

# Auto-refresh
if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Multi-Source Confluence Analysis")
st.sidebar.caption("Data: Yahoo Finance, TradingView, RSS News")
st.sidebar.caption(f"Aktier: {len(ALL_STOCKS)} | Crypto: {len(CRYPTO_SYMBOLS)}")
