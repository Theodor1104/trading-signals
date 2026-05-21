"""
Trading Signals Pro - Professional Multi-Source Analysis Platform
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

from config import (
    INDUSTRIES, ALL_STOCKS, CRYPTO_SYMBOLS, FOREX_PAIRS,
    NEWS_RSS_FEEDS, API_ENDPOINTS, REFRESH_INTERVAL
)

# Page config
st.set_page_config(
    page_title="Trading Signals Pro",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background-color: #0e1117;
    }

    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #151922 100%);
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
    }

    /* Signal boxes */
    .signal-buy {
        background: linear-gradient(135deg, #065f46 0%, #047857 100%);
        border-left: 4px solid #10b981;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }

    .signal-sell {
        background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);
        border-left: 4px solid #ef4444;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }

    .signal-neutral {
        background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
        border-left: 4px solid #f59e0b;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
    }

    /* Tables */
    .dataframe {
        font-size: 14px !important;
    }

    /* Sidebar */
    .css-1d391kg {
        background-color: #1a1f2e;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
    }

    /* Remove default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Professional buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #1a1f2e;
        border-radius: 6px;
        padding: 10px 20px;
    }

    /* Indicator colors */
    .bullish { color: #10b981; }
    .bearish { color: #ef4444; }
    .neutral { color: #f59e0b; }

    /* Fix dark/black backgrounds */
    .stExpander {
        background-color: #1a1f2e !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
    }
    .stExpander > div {
        background-color: #1a1f2e !important;
    }
    [data-testid="stExpander"] {
        background-color: #1a1f2e !important;
    }
    .streamlit-expanderHeader {
        background-color: #1a1f2e !important;
        color: #ffffff !important;
    }
    .streamlit-expanderContent {
        background-color: #151922 !important;
    }

    /* Fix metric backgrounds */
    [data-testid="stMetric"] {
        background-color: #1a1f2e !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border: 1px solid #2d3748 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
    }

    /* Fix selectbox and inputs */
    .stSelectbox > div > div {
        background-color: #1a1f2e !important;
    }

    /* Stock card clickable */
    .stock-card {
        background: #1a1f2e;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 15px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    .stock-card:hover {
        border-color: #3b82f6;
        background: #1e2433;
    }
    .stock-card-buy {
        border-left: 4px solid #10b981;
    }
    .stock-card-sell {
        border-left: 4px solid #ef4444;
    }
    .stock-card-neutral {
        border-left: 4px solid #f59e0b;
    }

    /* Watermark - large, transparent, aligned with nav */
    .watermark {
        position: fixed !important;
        top: 40px !important;
        left: 200px !important;
        z-index: 999999 !important;
        background: transparent !important;
        border: none;
        padding: 10px 20px;
        pointer-events: none;
    }
    .watermark-subtitle {
        margin: 0;
        font-size: 28px;
        color: rgba(156, 163, 175, 0.85);
        text-transform: uppercase;
        letter-spacing: 6px;
        font-weight: 700;
    }
    .watermark-name {
        margin: 10px 0;
        font-size: 72px;
        font-weight: 900;
        color: rgba(59, 130, 246, 0.7);
    }
    .watermark-title {
        margin: 0;
        font-size: 58px;
        color: rgba(245, 158, 11, 0.7);
        font-weight: 900;
        letter-spacing: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Watermark - ALWAYS visible on ALL pages including login
st.markdown("""
<div class="watermark">
    <p class="watermark-subtitle">Created by</p>
    <p class="watermark-name">Theodor Hauch's</p>
    <p class="watermark-title">AKTIE MAGI</p>
</div>
""", unsafe_allow_html=True)

# ===== PASSWORD PROTECTION =====
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-top: 100px;'>TRADING SIGNALS PRO</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6b7280;'>Professional Market Analysis Platform</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        password = st.text_input("Access Code", type="password", key="password_input")

        if st.button("ENTER", use_container_width=True):
            if password == "Money":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid access code")

    return False

if not check_password():
    st.stop()

# ===== DATA FUNCTIONS =====
@st.cache_data(ttl=60)
def fetch_stock_data(symbol, period="6mo", interval="1d"):
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
    timeframes = {}
    try:
        ticker = yf.Ticker(symbol)

        daily = ticker.history(period="6mo", interval="1d")
        if not daily.empty:
            daily.columns = [c.lower() for c in daily.columns]
            timeframes['1D'] = daily

        weekly = ticker.history(period="2y", interval="1wk")
        if not weekly.empty:
            weekly.columns = [c.lower() for c in weekly.columns]
            timeframes['1W'] = weekly

        monthly = ticker.history(period="5y", interval="1mo")
        if not monthly.empty:
            monthly.columns = [c.lower() for c in monthly.columns]
            timeframes['1M'] = monthly
    except:
        pass
    return timeframes

@st.cache_data(ttl=300)
def fetch_news_sentiment(keywords, max_articles=20):
    articles = []
    for source, url in list(NEWS_RSS_FEEDS.items())[:10]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))[:200]
                if any(kw.lower() in (title + summary).lower() for kw in keywords):
                    articles.append({
                        'source': source.replace('_', ' ').title(),
                        'title': title,
                        'summary': summary,
                        'link': entry.get('link', ''),
                        'published': entry.get('published', '')
                    })
        except:
            continue

    sentiments = []
    for article in articles[:max_articles]:
        text = article['title'] + ' ' + article['summary']
        blob = TextBlob(text)
        score = blob.sentiment.polarity

        text_lower = text.lower()
        bullish = ['surge', 'rally', 'gain', 'rise', 'bullish', 'breakout', 'buy', 'upgrade', 'beat', 'record', 'soar', 'jump', 'profit']
        bearish = ['crash', 'plunge', 'drop', 'fall', 'bearish', 'dump', 'sell', 'downgrade', 'miss', 'fear', 'tank', 'sink', 'loss']

        for word in bullish:
            if word in text_lower: score += 0.15
        for word in bearish:
            if word in text_lower: score -= 0.15

        article['sentiment'] = max(-1, min(1, score))
        sentiments.append(score)

    return articles, np.mean(sentiments) if sentiments else 0

@st.cache_data(ttl=60)
def get_fear_greed_index():
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
def get_tradingview_analysis(symbol):
    if not TRADINGVIEW_AVAILABLE:
        return None

    results = {}
    intervals = [
        (Interval.INTERVAL_1_DAY, '1D'),
        (Interval.INTERVAL_1_WEEK, '1W'),
        (Interval.INTERVAL_1_MONTH, '1M'),
    ]

    try:
        clean_symbol = symbol.replace('-USD', '').replace('=X', '').replace('-', '')

        if 'USD' in symbol or symbol in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE']:
            exchange = "BINANCE"
            screener = "crypto"
            clean_symbol = symbol.replace('-USD', '') + "USDT"
        elif '=X' in symbol:
            exchange = "FX_IDC"
            screener = "forex"
        else:
            exchange = "NASDAQ"
            screener = "america"
            for ex in ["NASDAQ", "NYSE", "AMEX"]:
                try:
                    handler = TA_Handler(symbol=clean_symbol, exchange=ex, screener=screener, interval=Interval.INTERVAL_1_DAY, timeout=10)
                    if handler.get_analysis():
                        exchange = ex
                        break
                except:
                    continue

        for interval, name in intervals:
            try:
                handler = TA_Handler(symbol=clean_symbol, exchange=exchange, screener=screener, interval=interval, timeout=10)
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
    except:
        return None

@st.cache_data(ttl=600)
def get_analyst_ratings(symbol):
    try:
        ticker = yf.Ticker(symbol)
        rec = ticker.recommendations
        if rec is not None and len(rec) > 0:
            latest = rec.tail(5)
            buy = latest['strongBuy'].sum() + latest['buy'].sum()
            sell = latest['strongSell'].sum() + latest['sell'].sum()
            hold = latest['hold'].sum()
            total = buy + sell + hold
            if total > 0:
                return {'buy': buy, 'sell': sell, 'hold': hold, 'buy_pct': (buy/total)*100}
    except:
        pass
    return None

@st.cache_data(ttl=300)
def get_stock_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            'name': info.get('shortName', symbol),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 0),
            '52w_high': info.get('fiftyTwoWeekHigh', 0),
            '52w_low': info.get('fiftyTwoWeekLow', 0),
            'avg_volume': info.get('averageVolume', 0),
        }
    except:
        return None

# ===== TECHNICAL ANALYSIS =====
def calculate_indicators(data):
    if data is None or len(data) < 50:
        return None

    df = data.copy()

    # Momentum
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['rsi_6'] = ta.momentum.rsi(df['close'], window=6)
    df['stoch_k'] = ta.momentum.stoch(df['high'], df['low'], df['close'], window=14)
    df['stoch_d'] = ta.momentum.stoch_signal(df['high'], df['low'], df['close'], window=14)
    df['cci'] = ta.trend.cci(df['high'], df['low'], df['close'], window=20)
    df['williams_r'] = ta.momentum.williams_r(df['high'], df['low'], df['close'], lbp=14)
    df['roc'] = ta.momentum.roc(df['close'], window=12)
    df['ultimate_osc'] = ta.momentum.ultimate_oscillator(df['high'], df['low'], df['close'])

    # Trend
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

    # Ichimoku
    df['ichimoku_a'] = ta.trend.ichimoku_a(df['high'], df['low'])
    df['ichimoku_b'] = ta.trend.ichimoku_b(df['high'], df['low'])

    # Volatility
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_middle'] = bb.bollinger_mavg()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = bb.bollinger_wband()
    df['bb_pct'] = bb.bollinger_pband()

    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    # Volume
    df['obv'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    df['mfi'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=14)
    df['volume_sma'] = df['volume'].rolling(window=20).mean()
    df['cmf'] = ta.volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume'], window=20)

    # Pivot Points
    df['pivot'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    df['r1'] = 2 * df['pivot'] - df['low'].shift(1)
    df['s1'] = 2 * df['pivot'] - df['high'].shift(1)
    df['r2'] = df['pivot'] + (df['high'].shift(1) - df['low'].shift(1))
    df['s2'] = df['pivot'] - (df['high'].shift(1) - df['low'].shift(1))

    # Risk metrics
    df['daily_return'] = df['close'].pct_change()
    df['volatility_20'] = df['daily_return'].rolling(window=20).std() * np.sqrt(252) * 100
    df['cummax'] = df['close'].cummax()
    df['drawdown'] = (df['close'] - df['cummax']) / df['cummax'] * 100

    return df

def calculate_confluence(data, tv_analysis, news_sentiment, fear_greed, analyst_ratings):
    """
    Advanced confluence scoring with 25+ indicators
    Combines momentum, trend, volume, volatility, and external data
    """
    confluence = {'sources': {}, 'bullish': 0, 'bearish': 0, 'total': 0, 'details': {}}

    if data is not None and len(data) >= 10:
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        prev5 = data.iloc[-5] if len(data) >= 5 else prev
        price = latest['close']

        signals = []

        # ===== MOMENTUM INDICATORS =====

        # RSI (14) - Standard
        rsi = latest.get('rsi')
        if rsi:
            if rsi < 30: signals.append(('RSI 14', 'BUY', 3))
            elif rsi < 40: signals.append(('RSI 14', 'BUY', 1))
            elif rsi > 70: signals.append(('RSI 14', 'SELL', 3))
            elif rsi > 60: signals.append(('RSI 14', 'SELL', 1))
            else: signals.append(('RSI 14', 'NEUTRAL', 0))

        # RSI (6) - Fast
        rsi6 = latest.get('rsi_6')
        if rsi6:
            if rsi6 < 20: signals.append(('RSI 6', 'BUY', 2))
            elif rsi6 > 80: signals.append(('RSI 6', 'SELL', 2))

        # Stochastic %K and %D
        stoch_k = latest.get('stoch_k')
        stoch_d = latest.get('stoch_d')
        if stoch_k and stoch_d:
            if stoch_k < 20 and stoch_d < 20:
                signals.append(('Stochastic', 'BUY', 2))
            elif stoch_k > 80 and stoch_d > 80:
                signals.append(('Stochastic', 'SELL', 2))
            # Stochastic crossover
            prev_stoch_k = prev.get('stoch_k', 0)
            if stoch_k > stoch_d and prev_stoch_k <= prev.get('stoch_d', 0):
                signals.append(('Stoch Cross', 'BUY', 1))
            elif stoch_k < stoch_d and prev_stoch_k >= prev.get('stoch_d', 0):
                signals.append(('Stoch Cross', 'SELL', 1))

        # CCI
        cci = latest.get('cci')
        if cci:
            if cci < -100: signals.append(('CCI', 'BUY', 2))
            elif cci < -50: signals.append(('CCI', 'BUY', 1))
            elif cci > 100: signals.append(('CCI', 'SELL', 2))
            elif cci > 50: signals.append(('CCI', 'SELL', 1))

        # Williams %R
        williams = latest.get('williams_r')
        if williams:
            if williams < -80: signals.append(('Williams %R', 'BUY', 2))
            elif williams > -20: signals.append(('Williams %R', 'SELL', 2))

        # Ultimate Oscillator
        uo = latest.get('ultimate_osc')
        if uo:
            if uo < 30: signals.append(('Ultimate Osc', 'BUY', 1))
            elif uo > 70: signals.append(('Ultimate Osc', 'SELL', 1))

        # ROC (Rate of Change)
        roc = latest.get('roc')
        if roc:
            if roc > 5: signals.append(('ROC', 'BUY', 1))
            elif roc < -5: signals.append(('ROC', 'SELL', 1))

        # ===== TREND INDICATORS =====

        # MACD
        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        macd_hist = latest.get('macd_hist')
        if macd_hist is not None:
            if macd_hist > 0:
                signals.append(('MACD Hist', 'BUY', 2))
            else:
                signals.append(('MACD Hist', 'SELL', 2))

            # MACD Crossover
            prev_hist = prev.get('macd_hist', 0)
            if macd_hist > 0 and prev_hist <= 0:
                signals.append(('MACD Cross', 'BUY', 3))
            elif macd_hist < 0 and prev_hist >= 0:
                signals.append(('MACD Cross', 'SELL', 3))

        # Moving Averages
        sma_10 = latest.get('sma_10')
        sma_20 = latest.get('sma_20')
        sma_50 = latest.get('sma_50')
        sma_100 = latest.get('sma_100')
        sma_200 = latest.get('sma_200')
        ema_9 = latest.get('ema_9')
        ema_21 = latest.get('ema_21')

        # Price vs MAs
        if sma_20 and not pd.isna(sma_20):
            if price > sma_20: signals.append(('Price>SMA20', 'BUY', 1))
            else: signals.append(('Price>SMA20', 'SELL', 1))

        if sma_50 and not pd.isna(sma_50):
            if price > sma_50: signals.append(('Price>SMA50', 'BUY', 2))
            else: signals.append(('Price>SMA50', 'SELL', 2))

        if sma_200 and not pd.isna(sma_200):
            if price > sma_200: signals.append(('Price>SMA200', 'BUY', 3))
            else: signals.append(('Price>SMA200', 'SELL', 3))

        # Golden Cross / Death Cross (SMA 50 vs 200)
        if sma_50 and sma_200 and not pd.isna(sma_50) and not pd.isna(sma_200):
            prev_sma_50 = prev.get('sma_50', 0)
            prev_sma_200 = prev.get('sma_200', 0)
            if sma_50 > sma_200:
                signals.append(('50/200 Trend', 'BUY', 2))
                if prev_sma_50 and prev_sma_200 and prev_sma_50 <= prev_sma_200:
                    signals.append(('Golden Cross', 'BUY', 4))
            else:
                signals.append(('50/200 Trend', 'SELL', 2))
                if prev_sma_50 and prev_sma_200 and prev_sma_50 >= prev_sma_200:
                    signals.append(('Death Cross', 'SELL', 4))

        # EMA Crossover (9 vs 21)
        if ema_9 and ema_21 and not pd.isna(ema_9) and not pd.isna(ema_21):
            if ema_9 > ema_21: signals.append(('EMA 9/21', 'BUY', 1))
            else: signals.append(('EMA 9/21', 'SELL', 1))

        # ADX - Trend Strength
        adx = latest.get('adx')
        adx_pos = latest.get('adx_pos')
        adx_neg = latest.get('adx_neg')
        if adx and adx_pos and adx_neg:
            if adx > 25:  # Strong trend
                if adx_pos > adx_neg:
                    signals.append(('ADX Trend', 'BUY', 2))
                else:
                    signals.append(('ADX Trend', 'SELL', 2))

        # Ichimoku Cloud
        ichimoku_a = latest.get('ichimoku_a')
        ichimoku_b = latest.get('ichimoku_b')
        if ichimoku_a and ichimoku_b and not pd.isna(ichimoku_a) and not pd.isna(ichimoku_b):
            cloud_top = max(ichimoku_a, ichimoku_b)
            cloud_bottom = min(ichimoku_a, ichimoku_b)
            if price > cloud_top:
                signals.append(('Ichimoku', 'BUY', 2))
            elif price < cloud_bottom:
                signals.append(('Ichimoku', 'SELL', 2))
            else:
                signals.append(('Ichimoku', 'NEUTRAL', 0))

        # ===== VOLATILITY INDICATORS =====

        # Bollinger Bands
        bb_upper = latest.get('bb_upper')
        bb_lower = latest.get('bb_lower')
        bb_pct = latest.get('bb_pct')
        if bb_pct is not None:
            if bb_pct < 0:
                signals.append(('BB %B', 'BUY', 2))
            elif bb_pct < 0.2:
                signals.append(('BB %B', 'BUY', 1))
            elif bb_pct > 1:
                signals.append(('BB %B', 'SELL', 2))
            elif bb_pct > 0.8:
                signals.append(('BB %B', 'SELL', 1))

        # ATR-based volatility signal
        atr_pct = latest.get('atr_pct')
        if atr_pct:
            # High volatility = more caution
            if atr_pct > 5:
                confluence['details']['high_volatility'] = True

        # ===== VOLUME INDICATORS =====

        # MFI (Money Flow Index)
        mfi = latest.get('mfi')
        if mfi:
            if mfi < 20: signals.append(('MFI', 'BUY', 2))
            elif mfi < 30: signals.append(('MFI', 'BUY', 1))
            elif mfi > 80: signals.append(('MFI', 'SELL', 2))
            elif mfi > 70: signals.append(('MFI', 'SELL', 1))

        # OBV Trend
        obv = latest.get('obv')
        if obv and len(data) >= 10:
            obv_sma = data['obv'].rolling(10).mean().iloc[-1]
            if obv > obv_sma:
                signals.append(('OBV Trend', 'BUY', 1))
            else:
                signals.append(('OBV Trend', 'SELL', 1))

        # CMF (Chaikin Money Flow)
        cmf = latest.get('cmf')
        if cmf:
            if cmf > 0.1: signals.append(('CMF', 'BUY', 1))
            elif cmf < -0.1: signals.append(('CMF', 'SELL', 1))

        # Volume vs Average
        volume = latest.get('volume')
        volume_sma = latest.get('volume_sma')
        if volume and volume_sma and volume_sma > 0:
            vol_ratio = volume / volume_sma
            if vol_ratio > 1.5:
                # High volume confirms the move
                if price > prev['close']:
                    signals.append(('Vol Confirm', 'BUY', 1))
                else:
                    signals.append(('Vol Confirm', 'SELL', 1))

        # ===== SUPPORT/RESISTANCE =====

        # Pivot Points
        pivot = latest.get('pivot')
        r1 = latest.get('r1')
        s1 = latest.get('s1')
        if pivot and r1 and s1:
            if price > r1:
                signals.append(('Pivot', 'BUY', 1))
            elif price < s1:
                signals.append(('Pivot', 'SELL', 1))

        # ===== PRICE ACTION =====

        # 5-day momentum
        if len(data) >= 5:
            momentum_5d = ((price / prev5['close']) - 1) * 100
            if momentum_5d > 5:
                signals.append(('5D Momentum', 'BUY', 1))
            elif momentum_5d < -5:
                signals.append(('5D Momentum', 'SELL', 1))

        # Higher highs / Lower lows (3 day)
        if len(data) >= 3:
            highs = data['high'].iloc[-3:]
            lows = data['low'].iloc[-3:]
            if highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
                signals.append(('Higher Highs', 'BUY', 1))
            if lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
                signals.append(('Lower Lows', 'SELL', 1))

        # ===== RSI DIVERGENCE =====
        if len(data) >= 14 and rsi:
            price_14d_ago = data['close'].iloc[-14]
            rsi_14d_ago = data['rsi'].iloc[-14] if 'rsi' in data else None
            if rsi_14d_ago:
                # Bullish divergence: price lower, RSI higher
                if price < price_14d_ago and rsi > rsi_14d_ago:
                    signals.append(('RSI Divergence', 'BUY', 2))
                # Bearish divergence: price higher, RSI lower
                elif price > price_14d_ago and rsi < rsi_14d_ago:
                    signals.append(('RSI Divergence', 'SELL', 2))

        # Add all technical signals
        for name, signal, weight in signals:
            confluence['sources'][name] = signal
            if signal == 'BUY': confluence['bullish'] += weight
            elif signal == 'SELL': confluence['bearish'] += weight
            confluence['total'] += 1

    # ===== EXTERNAL DATA SOURCES =====

    # TradingView Analysis (3 timeframes)
    if tv_analysis:
        for tf, analysis in tv_analysis.items():
            rec = analysis.get('summary', {}).get('RECOMMENDATION', 'NEUTRAL')
            buy_count = analysis.get('summary', {}).get('BUY', 0)
            sell_count = analysis.get('summary', {}).get('SELL', 0)

            if rec == 'STRONG_BUY':
                confluence['sources'][f'TV {tf}'] = 'BUY'
                confluence['bullish'] += 3
            elif rec == 'BUY':
                confluence['sources'][f'TV {tf}'] = 'BUY'
                confluence['bullish'] += 2
            elif rec == 'STRONG_SELL':
                confluence['sources'][f'TV {tf}'] = 'SELL'
                confluence['bearish'] += 3
            elif rec == 'SELL':
                confluence['sources'][f'TV {tf}'] = 'SELL'
                confluence['bearish'] += 2
            else:
                confluence['sources'][f'TV {tf}'] = 'NEUTRAL'
            confluence['total'] += 1

    # News Sentiment
    if news_sentiment:
        if news_sentiment > 0.3:
            confluence['sources']['News'] = 'BUY'
            confluence['bullish'] += 2
        elif news_sentiment > 0.1:
            confluence['sources']['News'] = 'BUY'
            confluence['bullish'] += 1
        elif news_sentiment < -0.3:
            confluence['sources']['News'] = 'SELL'
            confluence['bearish'] += 2
        elif news_sentiment < -0.1:
            confluence['sources']['News'] = 'SELL'
            confluence['bearish'] += 1
        else:
            confluence['sources']['News'] = 'NEUTRAL'
        confluence['total'] += 1

    # Fear & Greed Index (Crypto)
    if fear_greed:
        fg = fear_greed['value']
        if fg < 20:
            confluence['sources']['Fear/Greed'] = 'BUY'
            confluence['bullish'] += 3
        elif fg < 35:
            confluence['sources']['Fear/Greed'] = 'BUY'
            confluence['bullish'] += 2
        elif fg > 80:
            confluence['sources']['Fear/Greed'] = 'SELL'
            confluence['bearish'] += 3
        elif fg > 65:
            confluence['sources']['Fear/Greed'] = 'SELL'
            confluence['bearish'] += 2
        else:
            confluence['sources']['Fear/Greed'] = 'NEUTRAL'
        confluence['total'] += 1

    # Analyst Ratings
    if analyst_ratings:
        buy_pct = analyst_ratings.get('buy_pct', 50)
        if buy_pct > 80:
            confluence['sources']['Analysts'] = 'BUY'
            confluence['bullish'] += 2
        elif buy_pct > 60:
            confluence['sources']['Analysts'] = 'BUY'
            confluence['bullish'] += 1
        elif buy_pct < 20:
            confluence['sources']['Analysts'] = 'SELL'
            confluence['bearish'] += 2
        elif buy_pct < 40:
            confluence['sources']['Analysts'] = 'SELL'
            confluence['bearish'] += 1
        else:
            confluence['sources']['Analysts'] = 'NEUTRAL'
        confluence['total'] += 1

    # ===== CALCULATE FINAL SIGNAL =====

    total_weight = confluence['bullish'] + confluence['bearish']
    if total_weight > 0:
        bull_pct = (confluence['bullish'] / total_weight) * 100
        bear_pct = (confluence['bearish'] / total_weight) * 100

        if bull_pct > 55:
            confluence['signal'] = 'BUY'
            confluence['score'] = bull_pct
        elif bear_pct > 55:
            confluence['signal'] = 'SELL'
            confluence['score'] = bear_pct
        else:
            confluence['signal'] = 'NEUTRAL'
            confluence['score'] = 50
    else:
        confluence['signal'] = 'NEUTRAL'
        confluence['score'] = 50

    # ===== CONFIDENCE LEVEL =====

    num_sources = len(confluence['sources'])
    agreeing = sum(1 for s in confluence['sources'].values() if s == confluence['signal'])
    agreement_pct = (agreeing / max(1, num_sources)) * 100

    # More sources + higher agreement = higher confidence
    if agreement_pct >= 80 and num_sources >= 15:
        confluence['confidence'] = 'VERY HIGH'
    elif agreement_pct >= 70 and num_sources >= 12:
        confluence['confidence'] = 'HIGH'
    elif agreement_pct >= 60 and num_sources >= 8:
        confluence['confidence'] = 'MODERATE'
    elif agreement_pct >= 50:
        confluence['confidence'] = 'LOW'
    else:
        confluence['confidence'] = 'VERY LOW'

    # Store stats
    confluence['stats'] = {
        'total_sources': num_sources,
        'agreeing': agreeing,
        'agreement_pct': agreement_pct,
        'bull_weight': confluence['bullish'],
        'bear_weight': confluence['bearish']
    }

    return confluence

def calculate_risk(data):
    if data is None or len(data) < 20:
        return None

    return {
        'volatility': data['volatility_20'].iloc[-1] if 'volatility_20' in data else 0,
        'max_drawdown': data['drawdown'].min() if 'drawdown' in data else 0,
        'current_drawdown': data['drawdown'].iloc[-1] if 'drawdown' in data else 0,
        'atr_pct': data['atr_pct'].iloc[-1] if 'atr_pct' in data else 0,
    }

def scan_industry(stocks, progress_cb=None):
    results = []
    for i, symbol in enumerate(stocks):
        if progress_cb: progress_cb((i + 1) / len(stocks))
        try:
            data = fetch_stock_data(symbol, period="3mo")
            if data is None or len(data) < 50: continue

            data = calculate_indicators(data)
            confluence = calculate_confluence(data, None, 0, None, None)

            latest = data.iloc[-1]
            prev = data.iloc[-2]

            results.append({
                'Symbol': symbol,
                'Price': latest['close'],
                'Change': ((latest['close'] / prev['close']) - 1) * 100,
                'RSI': latest.get('rsi', 0),
                'Signal': confluence.get('signal', 'NEUTRAL'),
                'Score': confluence.get('score', 50)
            })
        except:
            continue
        time.sleep(0.1)
    return results

def render_full_panel(symbol, panel_id=0, is_compact=False):
    """Render a full analysis panel for split view"""
    data = fetch_stock_data(symbol, period="3mo")
    if data is None or len(data) < 50:
        st.error(f"No data for {symbol}")
        return

    data = calculate_indicators(data)
    latest = data.iloc[-1]
    prev = data.iloc[-2]
    price = latest['close']
    change = ((price / prev['close']) - 1) * 100

    # Get company info
    stock_info = get_stock_info(symbol)
    company_name = stock_info.get('name', symbol) if stock_info else symbol
    sector = stock_info.get('sector', '') if stock_info else ''

    # Get analysis data
    confluence = calculate_confluence(data, None, 0, None, None)
    signal = confluence['signal']
    score = confluence['score']
    risk = calculate_risk(data)

    # Header with company name and signal
    signal_color = "#10b981" if signal == "BUY" else "#ef4444" if signal == "SELL" else "#f59e0b"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1a1f2e 0%, #151922 100%); padding: 15px; border-radius: 10px; border-left: 5px solid {signal_color}; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <p style="margin: 0; font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px;">{symbol} {('| ' + sector) if sector else ''}</p>
                <h2 style="margin: 5px 0 0 0; font-size: 22px; font-weight: 800; color: #fff;">{company_name}</h2>
            </div>
            <span style="font-size: 18px; font-weight: 700; color: {signal_color}; background: rgba(0,0,0,0.3); padding: 5px 15px; border-radius: 20px;">{signal} {score:.0f}%</span>
        </div>
        <div style="margin-top: 10px;">
            <span style="font-size: 28px; font-weight: 700; color: #fff;">${price:.2f}</span>
            <span style="font-size: 16px; font-weight: 600; color: {'#10b981' if change >= 0 else '#ef4444'}; margin-left: 15px;">{change:+.2f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        rsi = latest.get('rsi', 0)
        rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
        st.metric("RSI (14)", f"{rsi:.1f}", rsi_status)
    with m2:
        macd_h = latest.get('macd_hist', 0)
        st.metric("MACD", "Bullish" if macd_h > 0 else "Bearish")
    with m3:
        if risk:
            st.metric("Volatility", f"{risk['volatility']:.1f}%")
    with m4:
        adx = latest.get('adx', 0)
        st.metric("ADX", f"{adx:.1f}", "Strong" if adx > 25 else "Weak")

    # Chart with tabs
    chart_height = 250 if is_compact else 350
    tab_chart, tab_ind, tab_levels = st.tabs(["Chart", "Indicators", "Levels"])

    with tab_chart:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=data.index[-60:], open=data['open'][-60:], high=data['high'][-60:],
            low=data['low'][-60:], close=data['close'][-60:],
            increasing_line_color='#10b981', decreasing_line_color='#ef4444', showlegend=False
        ), row=1, col=1)

        # Bollinger Bands
        fig.add_trace(go.Scatter(x=data.index[-60:], y=data['bb_upper'][-60:], line=dict(color='rgba(107,114,128,0.5)', width=1), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index[-60:], y=data['bb_lower'][-60:], line=dict(color='rgba(107,114,128,0.5)', width=1), fill='tonexty', fillcolor='rgba(107,114,128,0.1)', showlegend=False), row=1, col=1)

        # SMAs
        fig.add_trace(go.Scatter(x=data.index[-60:], y=data['sma_20'][-60:], line=dict(color='#f59e0b', width=1), name='SMA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index[-60:], y=data['sma_50'][-60:], line=dict(color='#3b82f6', width=1), name='SMA50'), row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=data.index[-60:], y=data['rsi'][-60:], line=dict(color='#8b5cf6', width=1), showlegend=False), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(239,68,68,0.5)", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(16,185,129,0.5)", row=2, col=1)

        fig.update_layout(
            height=chart_height, template='plotly_dark', paper_bgcolor='#0e1117', plot_bgcolor='#0e1117',
            xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=5, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10))
        )
        st.plotly_chart(fig, use_container_width=True, key=f"main_chart_{panel_id}")

    with tab_ind:
        ind1, ind2 = st.columns(2)
        with ind1:
            st.markdown("**Momentum**")
            st.markdown(f"- RSI: {latest.get('rsi', 0):.1f}")
            st.markdown(f"- Stochastic: {latest.get('stoch_k', 0):.1f}")
            st.markdown(f"- MFI: {latest.get('mfi', 0):.1f}")
            st.markdown(f"- CCI: {latest.get('cci', 0):.1f}")
        with ind2:
            st.markdown("**Trend**")
            st.markdown(f"- MACD: {'Bullish' if latest.get('macd_hist', 0) > 0 else 'Bearish'}")
            st.markdown(f"- ADX: {latest.get('adx', 0):.1f}")
            st.markdown(f"- Above SMA20: {'Yes' if price > latest.get('sma_20', 0) else 'No'}")
            st.markdown(f"- Above SMA50: {'Yes' if price > latest.get('sma_50', 0) else 'No'}")

    with tab_levels:
        lv1, lv2 = st.columns(2)
        with lv1:
            st.markdown("**Support**")
            st.markdown(f"- S1: ${latest.get('s1', 0):.2f}")
            st.markdown(f"- S2: ${latest.get('s2', 0):.2f}")
            st.markdown(f"- BB Lower: ${latest.get('bb_lower', 0):.2f}")
        with lv2:
            st.markdown("**Resistance**")
            st.markdown(f"- R1: ${latest.get('r1', 0):.2f}")
            st.markdown(f"- R2: ${latest.get('r2', 0):.2f}")
            st.markdown(f"- BB Upper: ${latest.get('bb_upper', 0):.2f}")

    # Signal sources (compact)
    st.markdown("**Signals:**")
    signals_html = ""
    for source, sig in list(confluence['sources'].items())[:6]:
        color = "#10b981" if sig == "BUY" else "#ef4444" if sig == "SELL" else "#6b7280"
        signals_html += f'<span style="display:inline-block;margin:2px;padding:3px 8px;background:#1a1f2e;border-radius:4px;border-left:2px solid {color};font-size:11px;"><b>{source}</b>: <span style="color:{color}">{sig}</span></span>'
    st.markdown(signals_html, unsafe_allow_html=True)

# ===== UI =====

# Header
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #2d3748; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 24px;">TRADING SIGNALS PRO</h1>
    <span style="color: #6b7280; font-size: 14px;">""" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</span>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### NAVIGATION")
    mode = st.radio("", ["Analysis", "Scanner", "Market Overview"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### MARKET")
    market = st.selectbox("", ["Stocks", "Crypto", "Forex"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### VIEW MODE")
    view_mode = st.radio("", ["Normal", "2-Split", "4-Split"], label_visibility="collapsed", horizontal=True)

    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (30s)")

    if market == "Crypto":
        fg = get_fear_greed_index()
        if fg:
            st.markdown("---")
            st.markdown("### FEAR & GREED INDEX")
            fg_color = "#10b981" if fg['value'] < 40 else "#ef4444" if fg['value'] > 60 else "#f59e0b"
            st.markdown(f"<h2 style='color: {fg_color}; margin: 0;'>{fg['value']}</h2>", unsafe_allow_html=True)
            st.caption(fg['label'])

# Main content
if mode == "Analysis":

    # Determine number of panels based on view mode
    if view_mode == "4-Split":
        num_panels = 4
    elif view_mode == "2-Split":
        num_panels = 2
    else:
        num_panels = 1

    # Symbol selection for split views
    if num_panels > 1:
        st.markdown(f"### SELECT {num_panels} SYMBOLS")

        symbols_selected = []

        if num_panels == 2:
            sel_cols = st.columns(2)
        else:  # 4-split
            sel_cols = st.columns(4)

        for i in range(num_panels):
            with sel_cols[i]:
                st.markdown(f"**Panel {i+1}**")
                if market == "Stocks":
                    ind_key = f"industry_{i}"
                    sym_key = f"symbol_{i}"
                    industry_sel = st.selectbox("Sector", list(INDUSTRIES.keys()), key=ind_key)
                    symbol_sel = st.selectbox("Symbol", INDUSTRIES[industry_sel], key=sym_key)
                elif market == "Crypto":
                    symbol_sel = st.selectbox("Symbol", CRYPTO_SYMBOLS, key=f"symbol_{i}")
                else:
                    symbol_sel = st.selectbox("Symbol", FOREX_PAIRS, key=f"symbol_{i}")
                symbols_selected.append(symbol_sel)

        analyze = st.button("ANALYZE ALL", use_container_width=True, type="primary")

        if analyze or auto_refresh:
            st.markdown("---")

            if num_panels == 2:
                col1, col2 = st.columns(2)
                with col1:
                    render_full_panel(symbols_selected[0], panel_id=0, is_compact=True)
                with col2:
                    render_full_panel(symbols_selected[1], panel_id=1, is_compact=True)
            else:  # 4-split
                # First row
                col1, col2 = st.columns(2)
                with col1:
                    render_full_panel(symbols_selected[0], panel_id=0, is_compact=True)
                with col2:
                    render_full_panel(symbols_selected[1], panel_id=1, is_compact=True)

                st.markdown("---")

                # Second row
                col3, col4 = st.columns(2)
                with col3:
                    render_full_panel(symbols_selected[2], panel_id=2, is_compact=True)
                with col4:
                    render_full_panel(symbols_selected[3], panel_id=3, is_compact=True)

    else:
        # Normal single view
        col_select, col_space = st.columns([1, 3])

        with col_select:
            if market == "Stocks":
                industry = st.selectbox("Sector", list(INDUSTRIES.keys()))
                symbol = st.selectbox("Symbol", INDUSTRIES[industry])
            elif market == "Crypto":
                symbol = st.selectbox("Symbol", CRYPTO_SYMBOLS)
            else:
                symbol = st.selectbox("Symbol", FOREX_PAIRS)

            analyze = st.button("ANALYZE", use_container_width=True, type="primary")

        if analyze or auto_refresh:
            with st.spinner("Analyzing..."):
                tf_data = fetch_multi_timeframe_data(symbol)
                data = tf_data.get('1D')

                if data is None or len(data) < 50:
                    st.error("Insufficient data for this symbol")
                    st.stop()

                data = calculate_indicators(data)
                keywords = [symbol.split('-')[0], symbol.replace('-USD', '')]
                articles, news_sentiment = fetch_news_sentiment(keywords)
                fg = get_fear_greed_index() if market == "Crypto" else None
                tv_analysis = get_tradingview_analysis(symbol)
                analyst_ratings = get_analyst_ratings(symbol)
                stock_info = get_stock_info(symbol)
                risk = calculate_risk(data)
                confluence = calculate_confluence(data, tv_analysis, news_sentiment, fg, analyst_ratings)

                latest = data.iloc[-1]
                prev = data.iloc[-2]
                price = latest['close']
                change = ((price / prev['close']) - 1) * 100

            # Results header
            st.markdown("---")

            # Company name header
            company_name = stock_info.get('name', symbol) if stock_info else symbol
            sector = stock_info.get('sector', '') if stock_info else ''
            signal = confluence['signal']
            score = confluence['score']
            signal_color = "#10b981" if signal == "BUY" else "#ef4444" if signal == "SELL" else "#f59e0b"

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1f2e 0%, #151922 100%); padding: 20px; border-radius: 12px; border-left: 6px solid {signal_color}; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <p style="margin: 0; font-size: 14px; color: #6b7280; text-transform: uppercase; letter-spacing: 2px;">{symbol} {('| ' + sector) if sector else ''}</p>
                        <h1 style="margin: 8px 0; font-size: 32px; font-weight: 800; color: #fff;">{company_name}</h1>
                        <div style="margin-top: 10px;">
                            <span style="font-size: 36px; font-weight: 700; color: #fff;">${price:,.2f}</span>
                            <span style="font-size: 18px; font-weight: 600; color: {'#10b981' if change >= 0 else '#ef4444'}; margin-left: 15px;">{change:+.2f}%</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="background: {signal_color}; padding: 15px 30px; border-radius: 12px;">
                            <p style="margin: 0; font-size: 28px; font-weight: 800; color: white;">{signal}</p>
                            <p style="margin: 5px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">{score:.0f}% Score</p>
                        </div>
                        <p style="margin: 10px 0 0 0; font-size: 14px; color: #9ca3af;">Confidence: <b style="color: #fff;">{confluence['confidence']}</b></p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Top metrics row
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                rsi_val = latest.get('rsi', 0)
                rsi_status = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"
                st.metric("RSI (14)", f"{rsi_val:.1f}", rsi_status)

            with col2:
                macd_h = latest.get('macd_hist', 0)
                st.metric("MACD", "Bullish" if macd_h > 0 else "Bearish")

            with col3:
                if risk:
                    st.metric("Volatility", f"{risk['volatility']:.1f}%")

            with col4:
                adx_val = latest.get('adx', 0)
                st.metric("ADX", f"{adx_val:.1f}", "Strong" if adx_val > 25 else "Weak")

            # Signal sources
            st.markdown("---")
            st.markdown("### SIGNAL SOURCES")

            source_cols = st.columns(min(8, len(confluence['sources'])))
            for i, (source, sig) in enumerate(confluence['sources'].items()):
                with source_cols[i % len(source_cols)]:
                    color = "#10b981" if sig == "BUY" else "#ef4444" if sig == "SELL" else "#6b7280"
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background: #1a1f2e; border-radius: 6px; border-left: 3px solid {color};">
                        <p style="margin: 0; font-size: 12px; color: #9ca3af;">{source}</p>
                        <p style="margin: 0; font-weight: 600; color: {color};">{sig}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Tabs
            st.markdown("---")
            tab1, tab2, tab3, tab4 = st.tabs(["CHART", "INDICATORS", "RISK", "NEWS"])

            with tab1:
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                                   row_heights=[0.6, 0.2, 0.2])

                # Candlestick
                fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'],
                    low=data['low'], close=data['close'], name='Price',
                    increasing_line_color='#10b981', decreasing_line_color='#ef4444'), row=1, col=1)

                # Bollinger Bands
                fig.add_trace(go.Scatter(x=data.index, y=data['bb_upper'], line=dict(color='#6b7280', width=1), name='BB', showlegend=False), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['bb_lower'], line=dict(color='#6b7280', width=1), fill='tonexty', fillcolor='rgba(107,114,128,0.1)', showlegend=False), row=1, col=1)

                # MAs
                fig.add_trace(go.Scatter(x=data.index, y=data['sma_20'], line=dict(color='#f59e0b', width=1), name='SMA 20'), row=1, col=1)
                fig.add_trace(go.Scatter(x=data.index, y=data['sma_50'], line=dict(color='#3b82f6', width=1), name='SMA 50'), row=1, col=1)

                # RSI
                fig.add_trace(go.Scatter(x=data.index, y=data['rsi'], line=dict(color='#8b5cf6', width=1), name='RSI'), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)

                # MACD
                colors = ['#10b981' if v >= 0 else '#ef4444' for v in data['macd_hist']]
                fig.add_trace(go.Bar(x=data.index, y=data['macd_hist'], marker_color=colors, name='MACD'), row=3, col=1)

                fig.update_layout(
                    height=600,
                    template='plotly_dark',
                    paper_bgcolor='#0e1117',
                    plot_bgcolor='#0e1117',
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=0, r=0, t=30, b=0)
                )

                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                col_m, col_t, col_v = st.columns(3)

                with col_m:
                    st.markdown("#### Momentum")
                    indicators = [
                        ("RSI (14)", latest.get('rsi', 0), 30, 70),
                        ("Stochastic", latest.get('stoch_k', 0), 20, 80),
                        ("MFI", latest.get('mfi', 0), 20, 80),
                        ("CCI", latest.get('cci', 0), -100, 100),
                        ("Williams %R", latest.get('williams_r', 0), -80, -20),
                    ]
                    for name, val, low, high in indicators:
                        if val:
                            status = "Oversold" if val < low else "Overbought" if val > high else "Neutral"
                            color = "#10b981" if val < low else "#ef4444" if val > high else "#6b7280"
                            st.markdown(f"**{name}**: <span style='color:{color}'>{val:.1f}</span> ({status})", unsafe_allow_html=True)

                with col_t:
                    st.markdown("#### Trend")
                    adx = latest.get('adx', 0)
                    st.markdown(f"**ADX**: {adx:.1f} ({'Strong' if adx > 25 else 'Weak'} trend)")
                    macd_h = latest.get('macd_hist', 0)
                    st.markdown(f"**MACD**: {'Bullish' if macd_h > 0 else 'Bearish'}")

                    st.markdown("**Price vs MAs:**")
                    for ma, col in [('SMA 20', 'sma_20'), ('SMA 50', 'sma_50'), ('SMA 200', 'sma_200')]:
                        if col in latest and not pd.isna(latest[col]):
                            above = price > latest[col]
                            st.markdown(f"- {ma}: {'Above' if above else 'Below'} (${latest[col]:.2f})")

                with col_v:
                    st.markdown("#### Volatility")
                    st.markdown(f"**ATR**: ${latest.get('atr', 0):.2f} ({latest.get('atr_pct', 0):.1f}%)")
                    st.markdown(f"**BB %B**: {latest.get('bb_pct', 0):.2f}")
                    if risk:
                        st.markdown(f"**20D Volatility**: {risk['volatility']:.1f}%")

            with tab3:
                if risk:
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.metric("20-Day Volatility", f"{risk['volatility']:.1f}%")
                        st.metric("Max Drawdown", f"{risk['max_drawdown']:.1f}%")
                    with col_r2:
                        st.metric("Current Drawdown", f"{risk['current_drawdown']:.1f}%")
                        st.metric("ATR %", f"{risk['atr_pct']:.2f}%")

                    # Drawdown chart
                    fig_dd = go.Figure()
                    fig_dd.add_trace(go.Scatter(x=data.index, y=data['drawdown'], fill='tozeroy',
                        fillcolor='rgba(239,68,68,0.3)', line=dict(color='#ef4444', width=1)))
                    fig_dd.update_layout(height=200, template='plotly_dark', paper_bgcolor='#0e1117',
                        plot_bgcolor='#0e1117', margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
                    st.plotly_chart(fig_dd, use_container_width=True)

            with tab4:
                st.markdown(f"**Sentiment Score**: {news_sentiment:.2f}")
                if articles:
                    for art in articles[:5]:
                        color = "#10b981" if art['sentiment'] > 0.1 else "#ef4444" if art['sentiment'] < -0.1 else "#6b7280"
                        st.markdown(f"""
                        <div style="padding: 10px; background: #1a1f2e; border-radius: 6px; margin: 5px 0; border-left: 3px solid {color};">
                            <p style="margin: 0; font-weight: 600;">{art['source']}</p>
                            <p style="margin: 5px 0; color: #9ca3af;">{art['title'][:100]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent news found")

            # Company info
            if stock_info and market == "Stocks":
                st.markdown("---")
                st.markdown("### COMPANY INFO")
                info_cols = st.columns(5)
                with info_cols[0]:
                    st.metric("Sector", stock_info.get('sector', 'N/A'))
                with info_cols[1]:
                    pe = stock_info.get('pe_ratio', 0)
                    st.metric("P/E", f"{pe:.1f}" if pe else "N/A")
                with info_cols[2]:
                    mc = stock_info.get('market_cap', 0)
                    st.metric("Market Cap", f"${mc/1e9:.1f}B" if mc else "N/A")
                with info_cols[3]:
                    st.metric("52W High", f"${stock_info.get('52w_high', 0):,.2f}")
                with info_cols[4]:
                    st.metric("52W Low", f"${stock_info.get('52w_low', 0):,.2f}")

elif mode == "Scanner":
    st.markdown("### SECTOR SCANNER")

    if market == "Stocks":
        industry = st.selectbox("Select Sector", list(INDUSTRIES.keys()))
        stocks = INDUSTRIES[industry]
    elif market == "Crypto":
        industry = "Crypto"
        stocks = CRYPTO_SYMBOLS
    else:
        industry = "Forex"
        stocks = FOREX_PAIRS

    st.caption(f"Scanning {len(stocks)} symbols...")

    if st.button("START SCAN", type="primary"):
        progress = st.progress(0)
        results = scan_industry(stocks, lambda p: progress.progress(p))
        progress.empty()

        if results:
            df = pd.DataFrame(results)
            st.session_state['scan_results'] = results

            buy_df = df[df['Signal'] == 'BUY'].sort_values('Score', ascending=False)
            sell_df = df[df['Signal'] == 'SELL'].sort_values('Score', ascending=False)
            neutral_df = df[df['Signal'] == 'NEUTRAL'].sort_values('Score', ascending=False)

            # Summary
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.metric("BUY Signals", len(buy_df), delta=None)
            with col_sum2:
                st.metric("SELL Signals", len(sell_df), delta=None)
            with col_sum3:
                st.metric("NEUTRAL", len(neutral_df), delta=None)

            st.markdown("---")

            # Tabs for signals
            tab_buy, tab_sell, tab_all = st.tabs(["BUY SIGNALS", "SELL SIGNALS", "ALL RESULTS"])

            with tab_buy:
                if not buy_df.empty:
                    for _, row in buy_df.iterrows():
                        with st.expander(f"**{row['Symbol']}** - ${row['Price']:.2f} ({row['Change']:+.1f}%) - Score: {row['Score']:.0f}%"):
                            # Fetch company info and detailed data
                            stock_info = get_stock_info(row['Symbol'])
                            company_name = stock_info.get('name', row['Symbol']) if stock_info else row['Symbol']
                            sector = stock_info.get('sector', '') if stock_info else ''

                            st.markdown(f"""
                            <div style="margin-bottom: 15px;">
                                <p style="margin: 0; font-size: 12px; color: #6b7280;">{row['Symbol']} {('| ' + sector) if sector else ''}</p>
                                <h3 style="margin: 5px 0; color: #fff;">{company_name}</h3>
                            </div>
                            """, unsafe_allow_html=True)

                            detail_data = fetch_stock_data(row['Symbol'], period="3mo")
                            if detail_data is not None and len(detail_data) >= 20:
                                detail_data = calculate_indicators(detail_data)
                                latest = detail_data.iloc[-1]

                                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                                with col_d1:
                                    st.metric("RSI", f"{latest.get('rsi', 0):.1f}")
                                with col_d2:
                                    st.metric("MACD", "Bullish" if latest.get('macd_hist', 0) > 0 else "Bearish")
                                with col_d3:
                                    st.metric("Volume", f"{latest.get('volume', 0)/1e6:.1f}M")
                                with col_d4:
                                    st.metric("ATR %", f"{latest.get('atr_pct', 0):.2f}%")

                                # Mini chart
                                fig_mini = go.Figure()
                                fig_mini.add_trace(go.Candlestick(
                                    x=detail_data.index[-30:],
                                    open=detail_data['open'][-30:],
                                    high=detail_data['high'][-30:],
                                    low=detail_data['low'][-30:],
                                    close=detail_data['close'][-30:],
                                    increasing_line_color='#10b981',
                                    decreasing_line_color='#ef4444'
                                ))
                                fig_mini.update_layout(
                                    height=250,
                                    template='plotly_dark',
                                    paper_bgcolor='#151922',
                                    plot_bgcolor='#151922',
                                    xaxis_rangeslider_visible=False,
                                    margin=dict(l=0, r=0, t=10, b=0),
                                    showlegend=False
                                )
                                st.plotly_chart(fig_mini, use_container_width=True)
                else:
                    st.info("No BUY signals found")

            with tab_sell:
                if not sell_df.empty:
                    for _, row in sell_df.iterrows():
                        with st.expander(f"**{row['Symbol']}** - ${row['Price']:.2f} ({row['Change']:+.1f}%) - Score: {row['Score']:.0f}%"):
                            # Fetch company info
                            stock_info = get_stock_info(row['Symbol'])
                            company_name = stock_info.get('name', row['Symbol']) if stock_info else row['Symbol']
                            sector = stock_info.get('sector', '') if stock_info else ''

                            st.markdown(f"""
                            <div style="margin-bottom: 15px;">
                                <p style="margin: 0; font-size: 12px; color: #6b7280;">{row['Symbol']} {('| ' + sector) if sector else ''}</p>
                                <h3 style="margin: 5px 0; color: #fff;">{company_name}</h3>
                            </div>
                            """, unsafe_allow_html=True)

                            detail_data = fetch_stock_data(row['Symbol'], period="3mo")
                            if detail_data is not None and len(detail_data) >= 20:
                                detail_data = calculate_indicators(detail_data)
                                latest = detail_data.iloc[-1]

                                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                                with col_d1:
                                    st.metric("RSI", f"{latest.get('rsi', 0):.1f}")
                                with col_d2:
                                    st.metric("MACD", "Bullish" if latest.get('macd_hist', 0) > 0 else "Bearish")
                                with col_d3:
                                    st.metric("Volume", f"{latest.get('volume', 0)/1e6:.1f}M")
                                with col_d4:
                                    st.metric("ATR %", f"{latest.get('atr_pct', 0):.2f}%")

                                fig_mini = go.Figure()
                                fig_mini.add_trace(go.Candlestick(
                                    x=detail_data.index[-30:],
                                    open=detail_data['open'][-30:],
                                    high=detail_data['high'][-30:],
                                    low=detail_data['low'][-30:],
                                    close=detail_data['close'][-30:],
                                    increasing_line_color='#10b981',
                                    decreasing_line_color='#ef4444'
                                ))
                                fig_mini.update_layout(
                                    height=250,
                                    template='plotly_dark',
                                    paper_bgcolor='#151922',
                                    plot_bgcolor='#151922',
                                    xaxis_rangeslider_visible=False,
                                    margin=dict(l=0, r=0, t=10, b=0),
                                    showlegend=False
                                )
                                st.plotly_chart(fig_mini, use_container_width=True)
                else:
                    st.info("No SELL signals found")

            with tab_all:
                st.dataframe(
                    df.style.format({'Price': '${:.2f}', 'Change': '{:+.2f}%', 'RSI': '{:.1f}', 'Score': '{:.0f}%'}),
                    use_container_width=True
                )

else:  # Market Overview
    st.markdown("### MARKET OVERVIEW")

    if market == "Stocks":
        industries_list = list(INDUSTRIES.items())
    elif market == "Crypto":
        industries_list = [("Crypto", CRYPTO_SYMBOLS)]
    else:
        industries_list = [("Forex", FOREX_PAIRS)]

    # Scan button
    if st.button("SCAN ALL SECTORS", type="primary"):
        progress = st.progress(0)
        overview = []
        sector_details = {}

        for i, (name, stocks) in enumerate(industries_list):
            progress.progress((i + 1) / len(industries_list))
            buy, sell, neutral = 0, 0, 0
            sector_stocks = []

            for sym in stocks[:10]:  # Top 10 per sector
                try:
                    data = fetch_stock_data(sym, period="3mo")
                    if data is not None and len(data) >= 50:
                        data = calculate_indicators(data)
                        conf = calculate_confluence(data, None, 0, None, None)
                        latest = data.iloc[-1]
                        prev = data.iloc[-2]
                        change = ((latest['close'] / prev['close']) - 1) * 100

                        stock_info = {
                            'symbol': sym,
                            'price': latest['close'],
                            'change': change,
                            'rsi': latest.get('rsi', 0),
                            'signal': conf['signal'],
                            'score': conf.get('score', 50)
                        }
                        sector_stocks.append(stock_info)

                        if conf['signal'] == 'BUY': buy += 1
                        elif conf['signal'] == 'SELL': sell += 1
                        else: neutral += 1
                except:
                    continue

            sector_details[name] = sector_stocks
            sentiment = 'Bullish' if buy > sell else 'Bearish' if sell > buy else 'Neutral'
            overview.append({
                'Sector': name,
                'Buy': buy,
                'Sell': sell,
                'Neutral': neutral,
                'Sentiment': sentiment
            })

        progress.empty()
        st.session_state['overview_data'] = overview
        st.session_state['sector_details'] = sector_details

    # Display results if available
    if 'overview_data' in st.session_state:
        overview = st.session_state['overview_data']
        sector_details = st.session_state.get('sector_details', {})
        df = pd.DataFrame(overview)

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Buy', x=df['Sector'], y=df['Buy'], marker_color='#10b981'))
        fig.add_trace(go.Bar(name='Sell', x=df['Sector'], y=df['Sell'], marker_color='#ef4444'))
        fig.add_trace(go.Bar(name='Neutral', x=df['Sector'], y=df['Neutral'], marker_color='#6b7280'))
        fig.update_layout(
            barmode='group',
            height=350,
            template='plotly_dark',
            paper_bgcolor='#0e1117',
            plot_bgcolor='#0e1117',
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### SECTOR DETAILS")
        st.caption("Click on a sector to see individual stocks")

        # Expandable sectors
        for sector_data in overview:
            sector_name = sector_data['Sector']
            sentiment = sector_data['Sentiment']
            sentiment_color = "#10b981" if sentiment == "Bullish" else "#ef4444" if sentiment == "Bearish" else "#f59e0b"

            with st.expander(f"**{sector_name}** - {sentiment} ({sector_data['Buy']} Buy / {sector_data['Sell']} Sell)"):
                if sector_name in sector_details:
                    stocks_in_sector = sector_details[sector_name]

                    if stocks_in_sector:
                        # Sort by signal
                        buy_stocks = [s for s in stocks_in_sector if s['signal'] == 'BUY']
                        sell_stocks = [s for s in stocks_in_sector if s['signal'] == 'SELL']
                        neutral_stocks = [s for s in stocks_in_sector if s['signal'] == 'NEUTRAL']

                        col_b, col_s = st.columns(2)

                        with col_b:
                            st.markdown("**BUY Signals:**")
                            for stock in buy_stocks:
                                st.markdown(f"""
                                <div style="padding: 8px 12px; background: #1a1f2e; border-left: 3px solid #10b981; margin: 4px 0; border-radius: 4px;">
                                    <span style="font-weight: 600; color: #fff;">{stock['symbol']}</span>
                                    <span style="float: right; color: #10b981;">${stock['price']:.2f} ({stock['change']:+.1f}%)</span>
                                    <br><span style="font-size: 12px; color: #9ca3af;">RSI: {stock['rsi']:.1f} | Score: {stock['score']:.0f}%</span>
                                </div>
                                """, unsafe_allow_html=True)

                        with col_s:
                            st.markdown("**SELL Signals:**")
                            for stock in sell_stocks:
                                st.markdown(f"""
                                <div style="padding: 8px 12px; background: #1a1f2e; border-left: 3px solid #ef4444; margin: 4px 0; border-radius: 4px;">
                                    <span style="font-weight: 600; color: #fff;">{stock['symbol']}</span>
                                    <span style="float: right; color: #ef4444;">${stock['price']:.2f} ({stock['change']:+.1f}%)</span>
                                    <br><span style="font-size: 12px; color: #9ca3af;">RSI: {stock['rsi']:.1f} | Score: {stock['score']:.0f}%</span>
                                </div>
                                """, unsafe_allow_html=True)

                        # Show individual stock charts on click
                        st.markdown("---")
                        selected_stock = st.selectbox(
                            "View chart for:",
                            [s['symbol'] for s in stocks_in_sector],
                            key=f"select_{sector_name}"
                        )

                        if selected_stock:
                            chart_data = fetch_stock_data(selected_stock, period="3mo")
                            if chart_data is not None and len(chart_data) >= 20:
                                chart_data = calculate_indicators(chart_data)

                                fig_stock = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.05, row_heights=[0.7, 0.3])

                                fig_stock.add_trace(go.Candlestick(
                                    x=chart_data.index,
                                    open=chart_data['open'],
                                    high=chart_data['high'],
                                    low=chart_data['low'],
                                    close=chart_data['close'],
                                    increasing_line_color='#10b981',
                                    decreasing_line_color='#ef4444',
                                    name='Price'
                                ), row=1, col=1)

                                # Add SMA
                                fig_stock.add_trace(go.Scatter(
                                    x=chart_data.index,
                                    y=chart_data['sma_20'],
                                    line=dict(color='#f59e0b', width=1),
                                    name='SMA 20'
                                ), row=1, col=1)

                                # RSI
                                fig_stock.add_trace(go.Scatter(
                                    x=chart_data.index,
                                    y=chart_data['rsi'],
                                    line=dict(color='#8b5cf6', width=1),
                                    name='RSI'
                                ), row=2, col=1)
                                fig_stock.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
                                fig_stock.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)

                                fig_stock.update_layout(
                                    height=400,
                                    template='plotly_dark',
                                    paper_bgcolor='#151922',
                                    plot_bgcolor='#151922',
                                    xaxis_rangeslider_visible=False,
                                    margin=dict(l=0, r=0, t=10, b=0),
                                    showlegend=False
                                )
                                st.plotly_chart(fig_stock, use_container_width=True)
                    else:
                        st.info("No data available for this sector")
                else:
                    st.info("Scan required to view details")

# Auto-refresh
if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
