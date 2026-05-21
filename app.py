"""
Trading Signals Pro - Professional Multi-Source Analysis Platform
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
import ta
import requests
import feedparser
from textblob import TextBlob
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io

# Database
from journal.database import JournalDB

# PDF/Excel exports
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Twilio for SMS
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Initialize database
db = JournalDB()

# Set default SMS number for alerts if not already set
if not db.get_setting('twilio_to'):
    db.set_setting('twilio_to', '+45 53 89 11 04')

def sync_watchlist_to_github():
    """Sync watchlist and holdings to watchlist.json for GitHub Actions"""
    try:
        watchlist = db.get_watchlist()
        holdings = db.get_holdings()

        data = {
            "watchlist": [{"symbol": w['symbol'], "market": w['market']} for w in watchlist],
            "holdings": [{"symbol": h['symbol'], "market": h['market'], "quantity": h['quantity'], "avg_price": h['avg_price']} for h in holdings],
            "last_updated": datetime.now().isoformat()
        }

        # Save to JSON only - push manually with: git push origin main
        with open('watchlist.json', 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass  # Silent fail

# TradingView Technical Analysis
try:
    from tradingview_ta import TA_Handler, Interval, Exchange
    TRADINGVIEW_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AVAILABLE = False

from config import (
    INDUSTRIES, ALL_STOCKS, CRYPTO_SYMBOLS, FOREX_PAIRS,
    NEWS_RSS_FEEDS, API_ENDPOINTS, REFRESH_INTERVAL, COMPANY_NAMES
)

# ===== CURRENCY HELPER =====
def get_currency(symbol):
    """Get currency symbol based on stock symbol"""
    if symbol.endswith('.CO'):
        return 'kr'  # Danish Krone
    elif symbol.endswith('.L'):
        return '£'   # British Pound
    elif '=X' in symbol:
        return ''    # Forex - no symbol
    else:
        return '$'   # USD (US stocks, Crypto)

def format_price(price, symbol):
    """Format price with correct currency"""
    currency = get_currency(symbol)
    if currency == 'kr':
        return f"{price:,.2f} kr"
    elif currency == '£':
        return f"£{price:,.2f}"
    else:
        return f"${price:,.2f}"

# ===== SEARCH FUNCTION =====
def search_symbols(query, market="Stocks"):
    """Search for symbols by name or symbol"""
    if not query or len(query) < 1:
        return []

    query = query.upper().strip()
    query_lower = query.lower()
    results = []

    # Get symbols based on market
    if market == "Stocks":
        symbols = ALL_STOCKS
    elif market == "Crypto":
        symbols = CRYPTO_SYMBOLS
    else:
        symbols = FOREX_PAIRS

    for sym in symbols:
        # Check symbol match
        if query in sym.upper():
            name = COMPANY_NAMES.get(sym, sym)
            results.append({"symbol": sym, "name": name, "match": "symbol"})
        # Check name match
        elif sym in COMPANY_NAMES:
            if query_lower in COMPANY_NAMES[sym].lower():
                results.append({"symbol": sym, "name": COMPANY_NAMES[sym], "match": "name"})

    # Sort: exact symbol matches first, then by symbol length
    results.sort(key=lambda x: (0 if x['match'] == 'symbol' and x['symbol'].startswith(query) else 1, len(x['symbol'])))
    return results[:15]  # Limit to 15 results

def get_all_searchable_symbols(market="Stocks"):
    """Get all symbols with their names for dropdown"""
    if market == "Stocks":
        symbols = ALL_STOCKS
    elif market == "Crypto":
        symbols = CRYPTO_SYMBOLS
    else:
        symbols = FOREX_PAIRS

    options = []
    for sym in symbols:
        name = COMPANY_NAMES.get(sym, "")
        if name:
            options.append(f"{sym} - {name}")
        else:
            options.append(sym)
    return sorted(options)

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

# ===== PASSWORD PROTECTION (DISABLED FOR DEV) =====
# def check_password():
#     return True

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
        # Try multiple fields for company name
        name = info.get('shortName') or info.get('longName') or info.get('name') or symbol
        return {
            'name': name,
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
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
        return {'name': symbol, 'sector': '', 'industry': '', 'market_cap': 0, 'pe_ratio': 0, 'forward_pe': 0, 'dividend_yield': 0, 'beta': 0, '52w_high': 0, '52w_low': 0, 'avg_volume': 0}

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

    # Auto-log signal to history
    try:
        db.log_signal(symbol, market, signal, score, price)
    except:
        pass  # Silently fail if logging doesn't work

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
            <span style="font-size: 28px; font-weight: 700; color: #fff;">{format_price(price, symbol)}</span>
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
    mode = st.radio("", ["Dashboard", "Analysis", "Scanner", "Market Overview", "Portfolio", "Tools", "Alerts", "Calendar"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### MARKET")
    market = st.selectbox("", ["Stocks", "Crypto", "Forex"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### VIEW MODE")
    view_mode = st.radio("", ["Normal", "2-Split", "4-Split"], label_visibility="collapsed", horizontal=True)

    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)

    if market == "Crypto":
        fg = get_fear_greed_index()
        if fg:
            st.markdown("---")
            st.markdown("### FEAR & GREED INDEX")
            fg_color = "#10b981" if fg['value'] < 40 else "#ef4444" if fg['value'] > 60 else "#f59e0b"
            st.markdown(f"<h2 style='color: {fg_color}; margin: 0;'>{fg['value']}</h2>", unsafe_allow_html=True)
            st.caption(fg['label'])

# Main content

# ===== AUTOMATED DASHBOARD =====
if mode == "Dashboard":
    st.markdown("### AUTOMATED TRADING DASHBOARD")
    st.caption("Alt du behøver på ét sted - opdateres automatisk")

    # Auto-scan function for dashboard
    @st.cache_data(ttl=300)
    def auto_scan_opportunities(symbols, limit=10):
        """Automatically scan for best opportunities"""
        results = []
        for sym in symbols[:50]:  # Limit for speed
            try:
                data = fetch_stock_data(sym, period="3mo")
                if data is None or len(data) < 20:
                    continue
                data = calculate_indicators(data)
                conf = calculate_confluence(data, None, 0, None, None)
                latest = data.iloc[-1]
                prev = data.iloc[-2]
                price = latest['close']
                change = ((price / prev['close']) - 1) * 100

                results.append({
                    'symbol': sym,
                    'price': price,
                    'change': change,
                    'signal': conf['signal'],
                    'score': conf['score'],
                    'rsi': latest.get('rsi', 50),
                    'confidence': conf.get('confidence', 'MODERATE')
                })
            except:
                continue
        return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]

    # Dashboard layout
    col_main, col_side = st.columns([3, 1])

    with col_side:
        # Market Sentiment
        st.markdown("#### MARKET PULSE")
        fg = get_fear_greed_index()
        if fg:
            fg_color = "#10b981" if fg['value'] < 40 else "#ef4444" if fg['value'] > 60 else "#f59e0b"
            st.markdown(f"""
            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
                <p style="margin: 0; color: #6b7280; font-size: 11px;">FEAR & GREED</p>
                <h2 style="margin: 5px 0; color: {fg_color};">{fg['value']}</h2>
                <p style="margin: 0; color: {fg_color}; font-size: 12px;">{fg['label']}</p>
            </div>
            """, unsafe_allow_html=True)

        # Portfolio Summary
        holdings = db.get_holdings()
        if holdings:
            total_value = 0
            total_pnl = 0
            for h in holdings:
                try:
                    ticker = yf.Ticker(h['symbol'])
                    current = ticker.history(period="1d")['Close'].iloc[-1]
                    value = current * h['quantity']
                    cost = h['avg_price'] * h['quantity']
                    total_value += value
                    total_pnl += (value - cost)
                except:
                    pass

            pnl_color = "#10b981" if total_pnl >= 0 else "#ef4444"
            st.markdown(f"""
            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
                <p style="margin: 0; color: #6b7280; font-size: 11px;">DIN PORTFOLIO</p>
                <h3 style="margin: 5px 0; color: #fff;">${total_value:,.0f}</h3>
                <p style="margin: 0; color: {pnl_color}; font-size: 14px;">{'+' if total_pnl >= 0 else ''}${total_pnl:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        # Active Alerts
        active_alerts = db.get_alerts(active_only=True)
        st.markdown(f"""
        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 10px;">
            <p style="margin: 0; color: #6b7280; font-size: 11px;">AKTIVE ALERTS</p>
            <h3 style="margin: 5px 0; color: #fff;">{len(active_alerts)}</h3>
        </div>
        """, unsafe_allow_html=True)

        # Watchlist count
        watchlist = db.get_watchlist()
        st.markdown(f"""
        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
            <p style="margin: 0; color: #6b7280; font-size: 11px;">WATCHLIST</p>
            <h3 style="margin: 5px 0; color: #fff;">{len(watchlist)}</h3>
        </div>
        """, unsafe_allow_html=True)

    with col_main:
        # Auto-scan button
        if st.button("SCAN FOR OPPORTUNITIES", type="primary", use_container_width=True):
            st.session_state['dashboard_scanned'] = True

        if st.session_state.get('dashboard_scanned', False) or True:
            with st.spinner("Scanner markeder for de bedste muligheder..."):
                # Scan stocks
                top_stocks = auto_scan_opportunities(ALL_STOCKS[:100])
                top_crypto = auto_scan_opportunities(CRYPTO_SYMBOLS)

            # TOP BUY OPPORTUNITIES
            st.markdown("#### TOP BUY SIGNALS")
            buy_opps = [r for r in top_stocks + top_crypto if r['signal'] == 'BUY' and r['score'] >= 60]
            buy_opps = sorted(buy_opps, key=lambda x: x['score'], reverse=True)[:5]

            if buy_opps:
                for opp in buy_opps:
                    score_color = "#10b981" if opp['score'] >= 70 else "#f59e0b"
                    conf_badge = "[HOT]" if opp['confidence'] == 'VERY HIGH' else "[+]" if opp['confidence'] == 'HIGH' else ""

                    col_o1, col_o2, col_o3, col_o4, col_o5 = st.columns([2, 2, 1.5, 2, 1.5])
                    with col_o1:
                        st.markdown(f"**{opp['symbol']}** {conf_badge}")
                    with col_o2:
                        st.markdown(format_price(opp['price'], opp['symbol']))
                    with col_o3:
                        chg_color = "#10b981" if opp['change'] >= 0 else "#ef4444"
                        st.markdown(f"<span style='color:{chg_color}'>{opp['change']:+.1f}%</span>", unsafe_allow_html=True)
                    with col_o4:
                        st.markdown(f"<span style='color:{score_color}'>BUY {opp['score']:.0f}%</span>", unsafe_allow_html=True)
                    with col_o5:
                        if st.button("+ Watch", key=f"add_{opp['symbol']}"):
                            market_type = "Crypto" if "-USD" in opp['symbol'] else "Stocks"
                            db.add_to_watchlist(opp['symbol'], market_type)
                            sync_watchlist_to_github()
                            st.rerun()
            else:
                st.info("Ingen stærke køb signaler fundet lige nu.")

            st.markdown("---")

            # TOP SELL SIGNALS (for watchlist)
            st.markdown("#### SELL SIGNALS (Watchlist)")
            watchlist_symbols = [w['symbol'] for w in watchlist]
            if watchlist_symbols:
                watchlist_scan = auto_scan_opportunities(watchlist_symbols, limit=20)
                sell_signals = [r for r in watchlist_scan if r['signal'] == 'SELL']

                if sell_signals:
                    for sig in sell_signals[:5]:
                        col_s1, col_s2, col_s3, col_s4 = st.columns([2, 2, 2, 2])
                        with col_s1:
                            st.markdown(f"**{sig['symbol']}**")
                        with col_s2:
                            st.markdown(format_price(sig['price'], sig['symbol']))
                        with col_s3:
                            st.markdown(f"<span style='color:#ef4444'>SELL {sig['score']:.0f}%</span>", unsafe_allow_html=True)
                        with col_s4:
                            st.markdown(f"RSI: {sig['rsi']:.0f}")
                else:
                    st.success("OK - Ingen sælg signaler i din watchlist")
            else:
                st.caption("Tilføj aktier til watchlist for at få sælg alerts")

            st.markdown("---")

            # QUICK ACTIONS
            st.markdown("#### QUICK ACTIONS")
            col_act1, col_act2, col_act3, col_act4 = st.columns(4)
            with col_act1:
                if st.button("Full Scan", use_container_width=True):
                    st.session_state['go_to'] = 'Scanner'
                    st.rerun()
            with col_act2:
                if st.button("Portfolio", use_container_width=True):
                    st.session_state['go_to'] = 'Portfolio'
                    st.rerun()
            with col_act3:
                if st.button("Alerts", use_container_width=True):
                    st.session_state['go_to'] = 'Alerts'
                    st.rerun()
            with col_act4:
                if st.button("Backtest", use_container_width=True):
                    st.session_state['go_to'] = 'Tools'
                    st.rerun()

            # TODAY'S MOVERS from watchlist
            if watchlist_symbols:
                st.markdown("---")
                st.markdown("#### WATCHLIST TODAY")
                watchlist_data = auto_scan_opportunities(watchlist_symbols, limit=20)
                if watchlist_data:
                    for item in watchlist_data[:8]:
                        signal_color = "#10b981" if item['signal'] == "BUY" else "#ef4444" if item['signal'] == "SELL" else "#f59e0b"
                        chg_color = "#10b981" if item['change'] >= 0 else "#ef4444"

                        col_w1, col_w2, col_w3, col_w4 = st.columns([2, 2, 2, 2])
                        with col_w1:
                            st.markdown(f"**{item['symbol']}**")
                        with col_w2:
                            st.markdown(format_price(item['price'], item['symbol']))
                        with col_w3:
                            st.markdown(f"<span style='color:{chg_color}'>{item['change']:+.2f}%</span>", unsafe_allow_html=True)
                        with col_w4:
                            st.markdown(f"<span style='color:{signal_color}'>{item['signal']} {item['score']:.0f}%</span>", unsafe_allow_html=True)

elif mode == "Analysis":

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
                            <span style="font-size: 36px; font-weight: 700; color: #fff;">{format_price(price, symbol)}</span>
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
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["CHART", "INDICATORS", "RISK", "NEWS", "INSIDERS", "OPTIONS"])

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

            with tab5:
                # Insider Trading Data
                if market == "Stocks":
                    try:
                        ticker = yf.Ticker(symbol)
                        insider_purchases = ticker.insider_purchases
                        insider_transactions = ticker.insider_transactions

                        if insider_purchases is not None and not insider_purchases.empty:
                            st.markdown("#### INSIDER PURCHASES (Last 6 Months)")

                            # Calculate net insider activity
                            total_buys = insider_purchases[insider_purchases['Shares'] > 0]['Shares'].sum() if 'Shares' in insider_purchases.columns else 0
                            total_sells = abs(insider_purchases[insider_purchases['Shares'] < 0]['Shares'].sum()) if 'Shares' in insider_purchases.columns else 0

                            if total_buys > total_sells:
                                insider_signal = "Net Buying"
                                insider_color = "#10b981"
                            elif total_sells > total_buys:
                                insider_signal = "Net Selling"
                                insider_color = "#ef4444"
                            else:
                                insider_signal = "Neutral"
                                insider_color = "#f59e0b"

                            st.markdown(f"""
                            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; border-left: 3px solid {insider_color}; margin-bottom: 15px;">
                                <p style="margin: 0; color: #6b7280; font-size: 12px;">INSIDER SENTIMENT</p>
                                <h3 style="margin: 5px 0; color: {insider_color};">{insider_signal}</h3>
                            </div>
                            """, unsafe_allow_html=True)

                            st.dataframe(insider_purchases.head(10), use_container_width=True)

                        if insider_transactions is not None and not insider_transactions.empty:
                            st.markdown("#### RECENT TRANSACTIONS")
                            st.dataframe(insider_transactions.head(10), use_container_width=True)

                        if (insider_purchases is None or insider_purchases.empty) and (insider_transactions is None or insider_transactions.empty):
                            st.info("No insider trading data available for this symbol.")

                    except Exception as e:
                        st.info("Insider trading data not available.")
                else:
                    st.info("Insider trading data is only available for stocks.")

            with tab6:
                # Options Data
                if market == "Stocks":
                    try:
                        ticker = yf.Ticker(symbol)
                        options_dates = ticker.options

                        if options_dates:
                            st.markdown("#### OPTIONS OVERVIEW")

                            # Get nearest expiration
                            nearest_exp = options_dates[0]
                            opt_chain = ticker.option_chain(nearest_exp)

                            calls = opt_chain.calls
                            puts = opt_chain.puts

                            # Put/Call Ratio
                            total_call_vol = calls['volume'].sum() if 'volume' in calls.columns else 0
                            total_put_vol = puts['volume'].sum() if 'volume' in puts.columns else 0
                            pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0

                            if pc_ratio < 0.7:
                                pc_sentiment = "Bullish"
                                pc_color = "#10b981"
                            elif pc_ratio > 1.0:
                                pc_sentiment = "Bearish"
                                pc_color = "#ef4444"
                            else:
                                pc_sentiment = "Neutral"
                                pc_color = "#f59e0b"

                            col_opt1, col_opt2, col_opt3 = st.columns(3)
                            with col_opt1:
                                st.markdown(f"""
                                <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                                    <p style="margin: 0; color: #6b7280; font-size: 11px;">PUT/CALL RATIO</p>
                                    <h3 style="margin: 5px 0; color: {pc_color};">{pc_ratio:.2f}</h3>
                                    <p style="margin: 0; color: {pc_color}; font-size: 12px;">{pc_sentiment}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_opt2:
                                avg_iv_calls = calls['impliedVolatility'].mean() * 100 if 'impliedVolatility' in calls.columns else 0
                                st.markdown(f"""
                                <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                                    <p style="margin: 0; color: #6b7280; font-size: 11px;">AVG IV (CALLS)</p>
                                    <h3 style="margin: 5px 0; color: #fff;">{avg_iv_calls:.1f}%</h3>
                                </div>
                                """, unsafe_allow_html=True)
                            with col_opt3:
                                total_oi = calls['openInterest'].sum() + puts['openInterest'].sum() if 'openInterest' in calls.columns else 0
                                st.markdown(f"""
                                <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                                    <p style="margin: 0; color: #6b7280; font-size: 11px;">OPEN INTEREST</p>
                                    <h3 style="margin: 5px 0; color: #fff;">{total_oi:,.0f}</h3>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("---")
                            st.markdown(f"**Expiration: {nearest_exp}**")

                            opt_tabs = st.tabs(["CALLS", "PUTS"])
                            with opt_tabs[0]:
                                display_cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
                                display_cols = [c for c in display_cols if c in calls.columns]
                                st.dataframe(calls[display_cols].head(15), use_container_width=True)
                            with opt_tabs[1]:
                                display_cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
                                display_cols = [c for c in display_cols if c in puts.columns]
                                st.dataframe(puts[display_cols].head(15), use_container_width=True)
                        else:
                            st.info("No options data available for this symbol.")
                    except Exception as e:
                        st.info("Options data not available.")
                else:
                    st.info("Options data is only available for stocks.")

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

    scanner_tabs = st.tabs(["Simple Scan", "Advanced Filters"])

    with scanner_tabs[0]:
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
                                stock_info = get_stock_info(row['Symbol'])
                                company_name = stock_info.get('name', row['Symbol']) if stock_info else row['Symbol']
                                st.markdown(f"**{company_name}**")
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
                    else:
                        st.info("No BUY signals found")

                with tab_sell:
                    if not sell_df.empty:
                        for _, row in sell_df.iterrows():
                            with st.expander(f"**{row['Symbol']}** - ${row['Price']:.2f} ({row['Change']:+.1f}%) - Score: {row['Score']:.0f}%"):
                                stock_info = get_stock_info(row['Symbol'])
                                company_name = stock_info.get('name', row['Symbol']) if stock_info else row['Symbol']
                                st.markdown(f"**{company_name}**")
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
                    else:
                        st.info("No SELL signals found")

                with tab_all:
                    st.dataframe(
                        df.style.format({'Price': '${:.2f}', 'Change': '{:+.2f}%', 'RSI': '{:.1f}', 'Score': '{:.0f}%'}),
                        use_container_width=True
                    )

    with scanner_tabs[1]:
        st.markdown("#### ADVANCED FILTERS")
        st.markdown("Build custom filters to find specific opportunities.")

        # Filter presets
        st.markdown("**Quick Presets:**")
        col_preset1, col_preset2, col_preset3, col_preset4 = st.columns(4)
        with col_preset1:
            preset_oversold = st.button("Oversold (RSI<30)")
        with col_preset2:
            preset_overbought = st.button("Overbought (RSI>70)")
        with col_preset3:
            preset_bullish = st.button("Bullish MACD")
        with col_preset4:
            preset_volume = st.button("High Volume")

        st.markdown("---")
        st.markdown("**Custom Filters:**")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_rsi = st.checkbox("RSI Filter")
            if filter_rsi:
                rsi_op = st.selectbox("RSI", ["<", ">"], key="rsi_op")
                rsi_val = st.number_input("Value", value=30, key="rsi_val")
        with col_f2:
            filter_macd = st.checkbox("MACD Filter")
            if filter_macd:
                macd_op = st.selectbox("MACD Histogram", ["Positive", "Negative"], key="macd_op")
        with col_f3:
            filter_price = st.checkbox("Price vs SMA")
            if filter_price:
                price_sma = st.selectbox("Price is", ["Above SMA 20", "Below SMA 20", "Above SMA 50", "Below SMA 50"], key="price_sma")

        # Scan with filters
        if market == "Stocks":
            adv_industry = st.selectbox("Scan Sector", ["All"] + list(INDUSTRIES.keys()), key="adv_industry")
            if adv_industry == "All":
                adv_stocks = ALL_STOCKS[:100]  # Limit for performance
            else:
                adv_stocks = INDUSTRIES[adv_industry]
        elif market == "Crypto":
            adv_stocks = CRYPTO_SYMBOLS
        else:
            adv_stocks = FOREX_PAIRS

        run_adv_scan = st.button("RUN ADVANCED SCAN", type="primary", key="adv_scan_btn")

        # Apply presets
        if preset_oversold:
            filter_rsi = True
            rsi_op = "<"
            rsi_val = 30
            run_adv_scan = True
        elif preset_overbought:
            filter_rsi = True
            rsi_op = ">"
            rsi_val = 70
            run_adv_scan = True
        elif preset_bullish:
            filter_macd = True
            macd_op = "Positive"
            run_adv_scan = True
        elif preset_volume:
            run_adv_scan = True

        if run_adv_scan:
            with st.spinner("Scanning with filters..."):
                adv_results = []
                progress = st.progress(0)

                for idx, sym in enumerate(adv_stocks):
                    progress.progress((idx + 1) / len(adv_stocks))
                    try:
                        data = fetch_stock_data(sym, period="3mo")
                        if data is None or len(data) < 20:
                            continue
                        data = calculate_indicators(data)
                        latest = data.iloc[-1]

                        # Apply filters
                        passes = True

                        if filter_rsi:
                            rsi_val_check = locals().get('rsi_val', 30)
                            rsi_op_check = locals().get('rsi_op', '<')
                            if rsi_op_check == "<" and latest.get('rsi', 50) >= rsi_val_check:
                                passes = False
                            elif rsi_op_check == ">" and latest.get('rsi', 50) <= rsi_val_check:
                                passes = False

                        if filter_macd:
                            macd_op_check = locals().get('macd_op', 'Positive')
                            if macd_op_check == "Positive" and latest.get('macd_hist', 0) <= 0:
                                passes = False
                            elif macd_op_check == "Negative" and latest.get('macd_hist', 0) >= 0:
                                passes = False

                        if filter_price:
                            price_sma_check = locals().get('price_sma', 'Above SMA 20')
                            if "Above SMA 20" in price_sma_check and latest['close'] <= latest.get('sma_20', 0):
                                passes = False
                            elif "Below SMA 20" in price_sma_check and latest['close'] >= latest.get('sma_20', float('inf')):
                                passes = False
                            elif "Above SMA 50" in price_sma_check and latest['close'] <= latest.get('sma_50', 0):
                                passes = False
                            elif "Below SMA 50" in price_sma_check and latest['close'] >= latest.get('sma_50', float('inf')):
                                passes = False

                        if passes:
                            conf = calculate_confluence(data, None, 0, None, None)
                            adv_results.append({
                                'Symbol': sym,
                                'Price': latest['close'],
                                'RSI': latest.get('rsi', 0),
                                'MACD': 'Bullish' if latest.get('macd_hist', 0) > 0 else 'Bearish',
                                'Signal': conf['signal'],
                                'Score': conf['score']
                            })
                    except:
                        continue

                progress.empty()

                if adv_results:
                    st.success(f"Found {len(adv_results)} matches!")
                    adv_df = pd.DataFrame(adv_results)
                    st.dataframe(adv_df, use_container_width=True)
                else:
                    st.info("No symbols match your filters.")

elif mode == "Market Overview":
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
                                    <span style="float: right; color: #10b981;">{format_price(stock['price'], stock['symbol'])} ({stock['change']:+.1f}%)</span>
                                    <br><span style="font-size: 12px; color: #9ca3af;">RSI: {stock['rsi']:.1f} | Score: {stock['score']:.0f}%</span>
                                </div>
                                """, unsafe_allow_html=True)

                        with col_s:
                            st.markdown("**SELL Signals:**")
                            for stock in sell_stocks:
                                st.markdown(f"""
                                <div style="padding: 8px 12px; background: #1a1f2e; border-left: 3px solid #ef4444; margin: 4px 0; border-radius: 4px;">
                                    <span style="font-weight: 600; color: #fff;">{stock['symbol']}</span>
                                    <span style="float: right; color: #ef4444;">{format_price(stock['price'], stock['symbol'])} ({stock['change']:+.1f}%)</span>
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

# ===== PORTFOLIO PAGE =====
elif mode == "Portfolio":
    st.markdown("### PORTFOLIO")

    portfolio_tab = st.tabs(["Watchlist", "Holdings", "Performance"])

    with portfolio_tab[0]:
        st.markdown("#### MY WATCHLIST")

        # Add to watchlist
        col_add1, col_add2, col_add3 = st.columns([2, 2, 1])
        with col_add2:
            add_market = st.selectbox("Market", ["Stocks", "Crypto", "Forex"], key="watchlist_market", label_visibility="collapsed")
        with col_add1:
            # Get searchable options based on market
            search_options = get_all_searchable_symbols(add_market)
            selected_option = st.selectbox(
                "Search symbol or company name",
                options=[""] + search_options,
                key="watchlist_symbol_search",
                label_visibility="collapsed",
                placeholder="Type to search (e.g. Apple, AAPL)..."
            )
        with col_add3:
            if st.button("Add", type="primary"):
                if selected_option:
                    # Extract symbol from "SYMBOL - Company Name" format
                    symbol_upper = selected_option.split(" - ")[0].strip().upper()
                    if add_market == "Crypto" and not symbol_upper.endswith("-USD"):
                        symbol_upper = f"{symbol_upper}-USD"
                    if db.add_to_watchlist(symbol_upper, add_market):
                        st.success(f"Added {symbol_upper}")
                        sync_watchlist_to_github()
                        st.rerun()

        # Display watchlist
        watchlist = db.get_watchlist()
        if watchlist:
            for item in watchlist:
                try:
                    ticker = yf.Ticker(item['symbol'])
                    hist = ticker.history(period="2d")
                    if len(hist) >= 2:
                        price = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        change = ((price / prev) - 1) * 100
                    else:
                        price = hist['Close'].iloc[-1] if len(hist) > 0 else 0
                        change = 0

                    # Get signal
                    data = fetch_stock_data(item['symbol'], period="3mo")
                    signal = "N/A"
                    score = 0
                    if data is not None and len(data) >= 20:
                        data = calculate_indicators(data)
                        conf = calculate_confluence(data, None, 0, None, None)
                        signal = conf['signal']
                        score = conf['score']

                    signal_color = "#10b981" if signal == "BUY" else "#ef4444" if signal == "SELL" else "#f59e0b"

                    col_w1, col_w2, col_w3, col_w4, col_w5 = st.columns([2, 2, 2, 2, 1])
                    with col_w1:
                        st.markdown(f"**{item['symbol']}**")
                    with col_w2:
                        st.markdown(format_price(price, item['symbol']))
                    with col_w3:
                        delta_color = "#10b981" if change >= 0 else "#ef4444"
                        st.markdown(f"<span style='color: {delta_color}'>{change:+.2f}%</span>", unsafe_allow_html=True)
                    with col_w4:
                        st.markdown(f"<span style='color: {signal_color}'>{signal} {score:.0f}%</span>", unsafe_allow_html=True)
                    with col_w5:
                        if st.button("X", key=f"rm_{item['id']}"):
                            db.remove_from_watchlist(item['symbol'], item['market'])
                            sync_watchlist_to_github()
                            st.rerun()
                except Exception as e:
                    col_w1, col_w2 = st.columns([4, 1])
                    with col_w1:
                        st.markdown(f"**{item['symbol']}** - Error loading data")
                    with col_w2:
                        if st.button("X", key=f"rm_{item['id']}"):
                            db.remove_from_watchlist(item['symbol'], item['market'])
                            sync_watchlist_to_github()
                            st.rerun()
        else:
            st.info("Your watchlist is empty. Add symbols above to get started.")

    with portfolio_tab[1]:
        st.markdown("#### MY HOLDINGS")

        # Add holding
        st.markdown("**Add Position**")
        col_h0, col_h1, col_h2, col_h3, col_h4 = st.columns([1.5, 2.5, 1.5, 1.5, 1])
        with col_h0:
            hold_market = st.selectbox("Market", ["Stocks", "Crypto", "Forex"], key="hold_market", label_visibility="collapsed")
        with col_h1:
            # Searchable symbol dropdown
            hold_options = get_all_searchable_symbols(hold_market)
            hold_selected = st.selectbox(
                "Search symbol",
                options=[""] + hold_options,
                key="hold_sym_search",
                label_visibility="collapsed",
                placeholder="Type to search..."
            )
        with col_h2:
            hold_qty = st.number_input("Shares", min_value=0.0, step=1.0, key="hold_qty", label_visibility="collapsed")
        with col_h3:
            hold_price = st.number_input("Avg Price", min_value=0.0, step=0.01, key="hold_price", label_visibility="collapsed")
        with col_h4:
            if st.button("Add", key="add_holding", type="primary"):
                if hold_selected and hold_qty > 0 and hold_price > 0:
                    symbol_upper = hold_selected.split(" - ")[0].strip().upper()
                    if hold_market == "Crypto" and not symbol_upper.endswith("-USD"):
                        symbol_upper = f"{symbol_upper}-USD"
                    db.add_holding(symbol_upper, hold_market, hold_qty, hold_price)
                    st.success(f"Added {hold_qty} {symbol_upper}")
                    sync_watchlist_to_github()
                    st.rerun()

        st.markdown("---")

        # Holdings summary
        holdings = db.get_holdings()
        if holdings:
            total_value = 0
            total_cost = 0
            holdings_data = []

            for h in holdings:
                try:
                    ticker = yf.Ticker(h['symbol'])
                    current_price = ticker.history(period="1d")['Close'].iloc[-1]
                    value = current_price * h['quantity']
                    cost = h['avg_price'] * h['quantity']
                    pnl = value - cost
                    pnl_pct = (pnl / cost) * 100 if cost > 0 else 0

                    total_value += value
                    total_cost += cost

                    holdings_data.append({
                        'id': h['id'],
                        'symbol': h['symbol'],
                        'quantity': h['quantity'],
                        'avg_price': h['avg_price'],
                        'current_price': current_price,
                        'value': value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
                except:
                    holdings_data.append({
                        'id': h['id'],
                        'symbol': h['symbol'],
                        'quantity': h['quantity'],
                        'avg_price': h['avg_price'],
                        'current_price': 0,
                        'value': 0,
                        'pnl': 0,
                        'pnl_pct': 0
                    })

            total_pnl = total_value - total_cost
            total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0

            # Summary cards
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown(f"""
                <div style="background: #1a1f2e; padding: 20px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">TOTAL VALUE</p>
                    <h2 style="margin: 5px 0; color: #fff;">${total_value:,.2f}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_s2:
                pnl_color = "#10b981" if total_pnl >= 0 else "#ef4444"
                st.markdown(f"""
                <div style="background: #1a1f2e; padding: 20px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">TOTAL P&L</p>
                    <h2 style="margin: 5px 0; color: {pnl_color};">${total_pnl:+,.2f}</h2>
                </div>
                """, unsafe_allow_html=True)
            with col_s3:
                st.markdown(f"""
                <div style="background: #1a1f2e; padding: 20px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">RETURN</p>
                    <h2 style="margin: 5px 0; color: {pnl_color};">{total_pnl_pct:+.2f}%</h2>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # Holdings table
            for h in holdings_data:
                pnl_color = "#10b981" if h['pnl'] >= 0 else "#ef4444"
                col_t1, col_t2, col_t3, col_t4, col_t5, col_t6 = st.columns([2, 1.5, 1.5, 1.5, 2, 1])
                with col_t1:
                    st.markdown(f"**{h['symbol']}**")
                with col_t2:
                    st.markdown(f"{h['quantity']:.2f}")
                with col_t3:
                    st.markdown(format_price(h['avg_price'], h['symbol']))
                with col_t4:
                    st.markdown(format_price(h['current_price'], h['symbol']))
                with col_t5:
                    currency = get_currency(h['symbol'])
                    if currency == 'kr':
                        st.markdown(f"<span style='color: {pnl_color}'>{h['pnl']:+,.2f} kr ({h['pnl_pct']:+.2f}%)</span>", unsafe_allow_html=True)
                    elif currency == '£':
                        st.markdown(f"<span style='color: {pnl_color}'>£{h['pnl']:+,.2f} ({h['pnl_pct']:+.2f}%)</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color: {pnl_color}'>${h['pnl']:+,.2f} ({h['pnl_pct']:+.2f}%)</span>", unsafe_allow_html=True)
                with col_t6:
                    if st.button("Sell", key=f"sell_{h['id']}"):
                        db.remove_holding(h['id'])
                        sync_watchlist_to_github()
                        st.rerun()
        else:
            st.info("No holdings yet. Add your first position above.")

    with portfolio_tab[2]:
        st.markdown("#### PERFORMANCE")
        holdings = db.get_holdings()
        if holdings:
            # Pie chart of holdings
            labels = [h['symbol'] for h in holdings]
            values = []
            for h in holdings:
                try:
                    ticker = yf.Ticker(h['symbol'])
                    price = ticker.history(period="1d")['Close'].iloc[-1]
                    values.append(price * h['quantity'])
                except:
                    values.append(h['avg_price'] * h['quantity'])

            fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig_pie.update_layout(
                template='plotly_dark',
                paper_bgcolor='#0e1117',
                plot_bgcolor='#0e1117',
                height=400
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Add holdings to see performance charts.")

# ===== TOOLS PAGE =====
elif mode == "Tools":
    st.markdown("### TOOLS")

    tools_tab = st.tabs(["Backtest", "Correlation", "Export"])

    with tools_tab[0]:
        st.markdown("#### BACKTESTING")

        col_bt1, col_bt2, col_bt3, col_bt4 = st.columns([2, 2, 2, 1])
        with col_bt1:
            bt_symbol = st.text_input("Symbol", value="AAPL", key="bt_symbol")
        with col_bt2:
            bt_strategy = st.selectbox("Strategy", ["SMA Crossover", "RSI Strategy", "MACD Strategy", "Bollinger Bands"])
        with col_bt3:
            bt_period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"])
        with col_bt4:
            bt_capital = st.number_input("Capital", value=10000, step=1000)

        if st.button("RUN BACKTEST", type="primary"):
            with st.spinner("Running backtest..."):
                symbol = bt_symbol.upper().strip()
                data = fetch_stock_data(symbol, period=bt_period)

                if data is not None and len(data) >= 50:
                    data = calculate_indicators(data)

                    # Simple backtest logic
                    trades = []
                    position = None
                    equity = [bt_capital]

                    for i in range(50, len(data)):
                        row = data.iloc[i]
                        prev_row = data.iloc[i-1]

                        # Strategy signals
                        buy_signal = False
                        sell_signal = False

                        if bt_strategy == "SMA Crossover":
                            buy_signal = row['sma_20'] > row['sma_50'] and prev_row['sma_20'] <= prev_row['sma_50']
                            sell_signal = row['sma_20'] < row['sma_50'] and prev_row['sma_20'] >= prev_row['sma_50']
                        elif bt_strategy == "RSI Strategy":
                            buy_signal = row['rsi'] < 30 and prev_row['rsi'] >= 30
                            sell_signal = row['rsi'] > 70 and prev_row['rsi'] <= 70
                        elif bt_strategy == "MACD Strategy":
                            buy_signal = row['macd_hist'] > 0 and prev_row['macd_hist'] <= 0
                            sell_signal = row['macd_hist'] < 0 and prev_row['macd_hist'] >= 0
                        elif bt_strategy == "Bollinger Bands":
                            buy_signal = row['close'] < row['bb_lower'] and prev_row['close'] >= prev_row['bb_lower']
                            sell_signal = row['close'] > row['bb_upper'] and prev_row['close'] <= prev_row['bb_upper']

                        # Execute trades
                        if buy_signal and position is None:
                            position = {'entry': row['close'], 'date': data.index[i], 'shares': equity[-1] / row['close']}
                        elif sell_signal and position is not None:
                            pnl = (row['close'] - position['entry']) * position['shares']
                            trades.append({
                                'entry_date': position['date'].strftime('%Y-%m-%d'),
                                'exit_date': data.index[i].strftime('%Y-%m-%d'),
                                'entry': position['entry'],
                                'exit': row['close'],
                                'pnl': pnl,
                                'pnl_pct': ((row['close'] / position['entry']) - 1) * 100
                            })
                            equity.append(equity[-1] + pnl)
                            position = None
                        else:
                            equity.append(equity[-1])

                    # Calculate metrics
                    total_return = ((equity[-1] / bt_capital) - 1) * 100
                    winning_trades = len([t for t in trades if t['pnl'] > 0])
                    win_rate = (winning_trades / len(trades)) * 100 if trades else 0

                    returns = pd.Series(equity).pct_change().dropna()
                    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

                    max_dd = 0
                    peak = equity[0]
                    for e in equity:
                        if e > peak:
                            peak = e
                        dd = (peak - e) / peak * 100
                        if dd > max_dd:
                            max_dd = dd

                    # Save to database
                    db.save_backtest(symbol, bt_strategy, bt_period, total_return, win_rate,
                                     sharpe, max_dd, json.dumps(trades), json.dumps(equity))

                    # Display results
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        ret_color = "#10b981" if total_return >= 0 else "#ef4444"
                        st.markdown(f"""
                        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                            <p style="margin: 0; color: #6b7280; font-size: 11px;">TOTAL RETURN</p>
                            <h3 style="margin: 5px 0; color: {ret_color};">{total_return:+.2f}%</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_r2:
                        st.markdown(f"""
                        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                            <p style="margin: 0; color: #6b7280; font-size: 11px;">WIN RATE</p>
                            <h3 style="margin: 5px 0; color: #fff;">{win_rate:.1f}%</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_r3:
                        st.markdown(f"""
                        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                            <p style="margin: 0; color: #6b7280; font-size: 11px;">SHARPE RATIO</p>
                            <h3 style="margin: 5px 0; color: #fff;">{sharpe:.2f}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_r4:
                        st.markdown(f"""
                        <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                            <p style="margin: 0; color: #6b7280; font-size: 11px;">MAX DRAWDOWN</p>
                            <h3 style="margin: 5px 0; color: #ef4444;">-{max_dd:.2f}%</h3>
                        </div>
                        """, unsafe_allow_html=True)

                    # Equity curve
                    st.markdown("---")
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(y=equity, mode='lines', name='Equity',
                                                 line=dict(color='#3b82f6', width=2)))
                    fig_eq.update_layout(
                        title="Equity Curve",
                        template='plotly_dark',
                        paper_bgcolor='#0e1117',
                        plot_bgcolor='#0e1117',
                        height=300
                    )
                    st.plotly_chart(fig_eq, use_container_width=True)

                    # Trades table
                    if trades:
                        st.markdown("#### TRADES")
                        trades_df = pd.DataFrame(trades)
                        st.dataframe(trades_df, use_container_width=True)
                else:
                    st.error("Could not fetch enough data for backtest")

    with tools_tab[1]:
        st.markdown("#### CORRELATION ANALYSIS")

        # Symbol selection
        st.markdown("**Select symbols to compare:**")
        if 'corr_symbols' not in st.session_state:
            st.session_state.corr_symbols = ['AAPL', 'MSFT', 'GOOGL']

        col_cs1, col_cs2 = st.columns([4, 1])
        with col_cs1:
            corr_input = st.text_input("Add symbol", placeholder="e.g. NVDA", key="corr_add")
        with col_cs2:
            if st.button("Add", key="add_corr"):
                if corr_input and corr_input.upper() not in st.session_state.corr_symbols:
                    st.session_state.corr_symbols.append(corr_input.upper())
                    st.rerun()

        # Display selected symbols
        st.markdown(" | ".join([f"**{s}**" for s in st.session_state.corr_symbols]))

        corr_period = st.selectbox("Period", ["3mo", "6mo", "1y"], key="corr_period")

        if st.button("CALCULATE CORRELATION", type="primary"):
            with st.spinner("Calculating..."):
                prices = {}
                for sym in st.session_state.corr_symbols:
                    data = fetch_stock_data(sym, period=corr_period)
                    if data is not None:
                        prices[sym] = data['close']

                if len(prices) >= 2:
                    df_prices = pd.DataFrame(prices)
                    corr_matrix = df_prices.pct_change().corr()

                    # Heatmap
                    fig_corr = px.imshow(corr_matrix,
                                         labels=dict(color="Correlation"),
                                         x=corr_matrix.columns,
                                         y=corr_matrix.columns,
                                         color_continuous_scale='RdYlGn',
                                         zmin=-1, zmax=1)
                    fig_corr.update_layout(
                        template='plotly_dark',
                        paper_bgcolor='#0e1117',
                        height=400
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)

                    # Interpretation
                    st.markdown("#### INTERPRETATION")
                    for i, sym1 in enumerate(corr_matrix.columns):
                        for j, sym2 in enumerate(corr_matrix.columns):
                            if i < j:
                                corr_val = corr_matrix.iloc[i, j]
                                if abs(corr_val) > 0.7:
                                    level = "highly"
                                elif abs(corr_val) > 0.4:
                                    level = "moderately"
                                else:
                                    level = "weakly"
                                direction = "positively" if corr_val > 0 else "negatively"
                                st.markdown(f"- **{sym1}** and **{sym2}** are {level} {direction} correlated ({corr_val:.2f})")
                else:
                    st.error("Need at least 2 valid symbols")

    with tools_tab[2]:
        st.markdown("#### EXPORT ANALYSIS")

        exp_symbol = st.text_input("Symbol to export", value="AAPL", key="exp_symbol")
        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            if st.button("Export to Excel", type="primary"):
                symbol = exp_symbol.upper().strip()
                data = fetch_stock_data(symbol, period="6mo")
                if data is not None:
                    data = calculate_indicators(data)

                    # Create Excel buffer
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        data.to_excel(writer, sheet_name='Price Data')

                        # Summary sheet
                        latest = data.iloc[-1]
                        summary = pd.DataFrame({
                            'Metric': ['Symbol', 'Price', 'RSI', 'MACD', 'SMA 20', 'SMA 50'],
                            'Value': [symbol, latest['close'], latest.get('rsi', 0),
                                      latest.get('macd', 0), latest.get('sma_20', 0), latest.get('sma_50', 0)]
                        })
                        summary.to_excel(writer, sheet_name='Summary', index=False)

                    buffer.seek(0)
                    st.download_button(
                        label="Download Excel",
                        data=buffer,
                        file_name=f"{symbol}_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("Could not fetch data")

        with col_exp2:
            if st.button("Export to CSV"):
                symbol = exp_symbol.upper().strip()
                data = fetch_stock_data(symbol, period="6mo")
                if data is not None:
                    data = calculate_indicators(data)
                    csv = data.to_csv()
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"{symbol}_data_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Could not fetch data")

# ===== ALERTS PAGE =====
elif mode == "Alerts":
    st.markdown("### ALERTS")

    alerts_tab = st.tabs(["Create Alert", "Active Alerts", "Settings"])

    with alerts_tab[0]:
        st.markdown("#### CREATE NEW ALERT")

        col_a1, col_a2, col_a3, col_a4 = st.columns([2, 2, 2, 1.5])
        with col_a1:
            alert_symbol = st.text_input("Symbol", placeholder="AAPL", key="alert_sym")
        with col_a2:
            alert_type = st.selectbox("Alert Type", [
                "Price Above", "Price Below",
                "RSI Above 70", "RSI Below 30",
                "Signal Changes to BUY", "Signal Changes to SELL"
            ])
        with col_a3:
            if "Price" in alert_type:
                alert_value = st.number_input("Price", min_value=0.0, step=0.01, key="alert_val")
            else:
                alert_value = 0
                st.text_input("Value", value="Auto", disabled=True)
        with col_a4:
            alert_market = st.selectbox("Market", ["Stocks", "Crypto", "Forex"], key="alert_mkt")

        if st.button("CREATE ALERT", type="primary"):
            if alert_symbol:
                symbol = alert_symbol.upper().strip()
                if alert_market == "Crypto" and not symbol.endswith("-USD"):
                    symbol = f"{symbol}-USD"

                # Determine condition
                if "Above" in alert_type:
                    condition = "above"
                elif "Below" in alert_type:
                    condition = "below"
                elif "BUY" in alert_type:
                    condition = "signal_buy"
                else:
                    condition = "signal_sell"

                # Determine type
                if "Price" in alert_type:
                    a_type = "price"
                elif "RSI" in alert_type:
                    a_type = "rsi"
                    alert_value = 70 if "Above" in alert_type else 30
                else:
                    a_type = "signal"
                    alert_value = 0

                db.add_alert(symbol, alert_market, a_type, condition, alert_value)
                st.success(f"Alert created for {symbol}")
                st.rerun()

    with alerts_tab[1]:
        st.markdown("#### ACTIVE ALERTS")
        active_alerts = db.get_alerts(active_only=True)

        if active_alerts:
            for alert in active_alerts:
                alert_desc = f"{alert['alert_type'].upper()}"
                if alert['alert_type'] == 'price':
                    alert_desc = f"Price {alert['condition']} ${alert['value']:.2f}"
                elif alert['alert_type'] == 'rsi':
                    alert_desc = f"RSI {alert['condition']} {alert['value']:.0f}"
                elif alert['alert_type'] == 'signal':
                    alert_desc = f"Signal changes to {'BUY' if 'buy' in alert['condition'] else 'SELL'}"

                col_al1, col_al2, col_al3, col_al4 = st.columns([2, 3, 2, 1])
                with col_al1:
                    st.markdown(f"**{alert['symbol']}**")
                with col_al2:
                    st.markdown(alert_desc)
                with col_al3:
                    st.caption(f"Created: {alert['created_at'][:10]}")
                with col_al4:
                    if st.button("Delete", key=f"del_alert_{alert['id']}"):
                        db.remove_alert(alert['id'])
                        st.rerun()
        else:
            st.info("No active alerts. Create one above.")

        st.markdown("---")
        st.markdown("#### TRIGGERED ALERTS")
        triggered = db.get_triggered_alerts(limit=20)
        if triggered:
            for alert in triggered:
                st.markdown(f"- **{alert['symbol']}** - {alert['alert_type']} alert triggered at {alert['triggered_at'][:16]}")
        else:
            st.caption("No triggered alerts yet.")

    with alerts_tab[2]:
        st.markdown("#### NOTIFICATION SETTINGS")

        st.markdown("**Email Notifications (Gmail)**")
        email = db.get_setting('email', '')
        email_input = st.text_input("Gmail Address", value=email, placeholder="your@gmail.com")
        app_password = st.text_input("App Password", type="password", placeholder="Gmail App Password",
                                      help="Create an App Password in your Google Account settings")

        if st.button("Save Email Settings"):
            db.set_setting('email', email_input)
            if app_password:
                db.set_setting('email_password', app_password)
            st.success("Email settings saved!")

        st.markdown("---")
        st.markdown("**SMS Notifications (Twilio)**")
        st.caption("Requires a Twilio account (free trial available)")

        twilio_sid = db.get_setting('twilio_sid', '')
        twilio_token = db.get_setting('twilio_token', '')
        twilio_from = db.get_setting('twilio_from', '')
        twilio_to = db.get_setting('twilio_to', '')

        col_tw1, col_tw2 = st.columns(2)
        with col_tw1:
            sid_input = st.text_input("Account SID", value=twilio_sid)
            from_input = st.text_input("Twilio Phone Number", value=twilio_from, placeholder="+1234567890")
        with col_tw2:
            token_input = st.text_input("Auth Token", value=twilio_token, type="password")
            to_input = st.text_input("Your Phone Number", value=twilio_to, placeholder="+1234567890")

        if st.button("Save SMS Settings"):
            db.set_setting('twilio_sid', sid_input)
            db.set_setting('twilio_token', token_input)
            db.set_setting('twilio_from', from_input)
            db.set_setting('twilio_to', to_input)
            st.success("SMS settings saved!")

# ===== CALENDAR PAGE =====
elif mode == "Calendar":
    st.markdown("### CALENDAR")

    calendar_tab = st.tabs(["Earnings", "Signal History"])

    with calendar_tab[0]:
        st.markdown("#### EARNINGS CALENDAR")

        # Get earnings from watchlist or input
        watchlist = db.get_watchlist()
        watchlist_symbols = [w['symbol'] for w in watchlist]

        if watchlist_symbols:
            st.markdown("**Earnings for your watchlist:**")

            earnings_data = []
            for sym in watchlist_symbols:
                try:
                    ticker = yf.Ticker(sym)
                    cal = ticker.calendar
                    if cal is not None and not cal.empty:
                        if 'Earnings Date' in cal.columns:
                            earnings_date = cal['Earnings Date'].iloc[0]
                            earnings_data.append({
                                'Symbol': sym,
                                'Earnings Date': earnings_date.strftime('%Y-%m-%d') if hasattr(earnings_date, 'strftime') else str(earnings_date),
                                'EPS Estimate': cal.get('EPS Estimate', [None])[0] if 'EPS Estimate' in cal.columns else None
                            })
                except:
                    pass

            if earnings_data:
                df_earnings = pd.DataFrame(earnings_data)
                df_earnings = df_earnings.sort_values('Earnings Date')
                st.dataframe(df_earnings, use_container_width=True)
            else:
                st.info("No upcoming earnings found for watchlist symbols.")
        else:
            st.info("Add symbols to your watchlist to see their earnings dates.")

        st.markdown("---")
        st.markdown("**Check specific symbol:**")
        earn_symbol = st.text_input("Symbol", placeholder="AAPL", key="earn_check")
        if earn_symbol:
            try:
                ticker = yf.Ticker(earn_symbol.upper())
                cal = ticker.calendar
                if cal is not None and not cal.empty:
                    st.dataframe(cal, use_container_width=True)
                else:
                    st.info("No earnings data available")
            except Exception as e:
                st.error(f"Error: {e}")

    with calendar_tab[1]:
        st.markdown("#### SIGNAL HISTORY")

        # Accuracy summary
        accuracy = db.get_signal_accuracy()
        col_acc1, col_acc2, col_acc3 = st.columns(3)
        with col_acc1:
            st.markdown(f"""
            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #6b7280; font-size: 11px;">BUY ACCURACY</p>
                <h3 style="margin: 5px 0; color: #10b981;">{accuracy['buy_accuracy']:.1f}%</h3>
                <p style="margin: 0; color: #6b7280; font-size: 10px;">{accuracy['buy_correct']}/{accuracy['buy_total']} correct</p>
            </div>
            """, unsafe_allow_html=True)
        with col_acc2:
            st.markdown(f"""
            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #6b7280; font-size: 11px;">SELL ACCURACY</p>
                <h3 style="margin: 5px 0; color: #ef4444;">{accuracy['sell_accuracy']:.1f}%</h3>
                <p style="margin: 0; color: #6b7280; font-size: 10px;">{accuracy['sell_correct']}/{accuracy['sell_total']} correct</p>
            </div>
            """, unsafe_allow_html=True)
        with col_acc3:
            total = accuracy['buy_total'] + accuracy['sell_total']
            st.markdown(f"""
            <div style="background: #1a1f2e; padding: 15px; border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #6b7280; font-size: 11px;">TOTAL SIGNALS</p>
                <h3 style="margin: 5px 0; color: #fff;">{total}</h3>
                <p style="margin: 0; color: #6b7280; font-size: 10px;">tracked</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Signal log
        signals = db.get_signal_history(limit=50)
        if signals:
            st.markdown("**Recent Signals:**")
            for sig in signals:
                signal_color = "#10b981" if sig['signal'] == "BUY" else "#ef4444" if sig['signal'] == "SELL" else "#f59e0b"
                result_icon = ""
                if sig['result'] == 'correct':
                    result_icon = " [OK]"
                elif sig['result'] == 'incorrect':
                    result_icon = " [X]"

                col_sig1, col_sig2, col_sig3, col_sig4 = st.columns([2, 2, 2, 2])
                with col_sig1:
                    st.markdown(f"**{sig['symbol']}**")
                with col_sig2:
                    st.markdown(f"<span style='color: {signal_color}'>{sig['signal']} {sig['score']:.0f}%</span>", unsafe_allow_html=True)
                with col_sig3:
                    st.markdown(format_price(sig['price'], sig['symbol']))
                with col_sig4:
                    st.caption(f"{sig['timestamp'][:10]}{result_icon}")
        else:
            st.info("No signals logged yet. Signals are automatically logged when you analyze symbols.")

# Auto-refresh
if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
