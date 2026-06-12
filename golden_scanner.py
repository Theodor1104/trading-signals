#!/usr/bin/env python3
"""
Golden Opportunity Scanner v3.0 - Self-Learning AI Signal Detection
Features:
- Confluence-based scoring with 15+ technical indicators
- Price pattern recognition (candlestick patterns)
- Relative strength vs market (SPY)
- SELF-LEARNING: Tracks signal outcomes and adjusts weights automatically
- Learns which indicators are most predictive for each stock type
"""

import os
import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Technical analysis
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False

# Twilio for SMS
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# ============================================================================
# SELF-LEARNING SYSTEM
# ============================================================================

LEARNING_FILE = Path(__file__).parent / "signal_learning.json"
DEFAULT_WEIGHTS = {
    "RSI_OVERSOLD": 1.0,
    "RSI_RECOVERY": 1.0,
    "MACD_CROSS": 1.0,
    "MACD_MOMENTUM": 1.0,
    "STOCH_CROSS": 1.0,
    "EMA_CROSS": 1.0,
    "TREND_ABOVE_MA": 1.0,
    "GOLDEN_CROSS": 1.0,
    "ADX_BULLISH": 1.0,
    "SUPPORT_BOUNCE": 1.0,
    "HAMMER": 1.0,
    "ENGULFING": 1.0,
    "MORNING_STAR": 1.0,
    "THREE_SOLDIERS": 1.0,
    "VOLUME_BREAKOUT": 1.0,
    "RELATIVE_STRENGTH": 1.0,
    "WILLIAMS_R": 1.0,
    "CCI_OVERSOLD": 1.0,
}

class LearningSystem:
    """
    Self-learning system that tracks signal outcomes and adjusts weights.

    How it works:
    1. Every signal generated is logged with its indicators and score
    2. Outcomes are tracked at 1d, 5d, 10d, 20d after signal
    3. Accuracy is calculated for each indicator type
    4. Weights are adjusted: accurate indicators get higher weights
    5. System learns which patterns work best over time
    """

    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        """Load learning data from file"""
        if LEARNING_FILE.exists():
            try:
                with open(LEARNING_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass

        # Initialize default structure
        return {
            "weights": DEFAULT_WEIGHTS.copy(),
            "signals": [],  # Historical signals
            "indicator_stats": {},  # Accuracy stats per indicator
            "last_updated": None,
            "total_signals": 0,
            "version": "3.0"
        }

    def save_data(self):
        """Save learning data to file"""
        self.data["last_updated"] = datetime.now().isoformat()
        try:
            with open(LEARNING_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            log(f"Could not save learning data: {e}")

    def log_signal(self, symbol, signal_type, score, indicators_used, price, reasons):
        """
        Log a signal for future outcome tracking

        Args:
            symbol: Stock symbol
            signal_type: BUY, STRONG_BUY, etc.
            score: Signal score
            indicators_used: List of indicator names that contributed
            price: Price at signal time
            reasons: List of signal reasons
        """
        signal_entry = {
            "id": f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "symbol": symbol,
            "signal": signal_type,
            "score": score,
            "indicators": indicators_used,
            "price_at_signal": price,
            "reasons": reasons[:5],  # Keep top 5 reasons
            "timestamp": datetime.now().isoformat(),
            "outcomes": {
                "1d": None,
                "5d": None,
                "10d": None,
                "20d": None
            },
            "checked": False
        }

        self.data["signals"].append(signal_entry)
        self.data["total_signals"] += 1

        # Keep only last 1000 signals to prevent file bloat
        if len(self.data["signals"]) > 1000:
            self.data["signals"] = self.data["signals"][-1000:]

    def update_outcomes(self):
        """
        Check and update outcomes for past signals.
        This should be run periodically to track how signals performed.
        """
        updated = 0
        now = datetime.now()

        for signal in self.data["signals"]:
            if signal.get("checked"):
                continue

            signal_time = datetime.fromisoformat(signal["timestamp"])
            days_since = (now - signal_time).days

            # Skip if signal is too recent
            if days_since < 1:
                continue

            # Try to fetch current price
            try:
                ticker = yf.Ticker(signal["symbol"])
                hist = ticker.history(period="1mo")

                if hist.empty:
                    continue

                signal_price = signal["price_at_signal"]

                # Check each outcome period
                for period, days in [("1d", 1), ("5d", 5), ("10d", 10), ("20d", 20)]:
                    if signal["outcomes"][period] is None and days_since >= days:
                        # Find price 'days' after signal
                        try:
                            future_date = signal_time + timedelta(days=days)
                            # Find closest trading day
                            mask = hist.index >= future_date.strftime('%Y-%m-%d')
                            if mask.any():
                                future_price = hist[mask]['Close'].iloc[0]
                                pct_change = ((future_price / signal_price) - 1) * 100
                                signal["outcomes"][period] = {
                                    "price": float(future_price),
                                    "change_pct": round(pct_change, 2),
                                    "profitable": pct_change > 0
                                }
                                updated += 1
                        except:
                            pass

                # Mark as fully checked if all outcomes filled or signal is old enough
                if days_since >= 25:
                    signal["checked"] = True

            except:
                continue

        if updated > 0:
            log(f"[LEARNING] Updated {updated} signal outcomes")
            self.calculate_indicator_accuracy()
            self.adjust_weights()

    def calculate_indicator_accuracy(self):
        """
        Calculate accuracy for each indicator based on historical outcomes.
        Accuracy = % of signals where indicator was present that were profitable.
        """
        indicator_results = {ind: {"wins": 0, "total": 0} for ind in DEFAULT_WEIGHTS.keys()}

        for signal in self.data["signals"]:
            # Use 5-day outcome as primary measure
            outcome = signal["outcomes"].get("5d")
            if outcome is None:
                continue

            is_profitable = outcome["profitable"]

            # Track for each indicator used in this signal
            for indicator in signal.get("indicators", []):
                if indicator in indicator_results:
                    indicator_results[indicator]["total"] += 1
                    if is_profitable:
                        indicator_results[indicator]["wins"] += 1

        # Calculate accuracy percentages
        self.data["indicator_stats"] = {}
        for ind, stats in indicator_results.items():
            if stats["total"] >= 5:  # Need at least 5 samples for meaningful accuracy
                accuracy = (stats["wins"] / stats["total"]) * 100
                self.data["indicator_stats"][ind] = {
                    "accuracy": round(accuracy, 1),
                    "samples": stats["total"],
                    "wins": stats["wins"]
                }

    def adjust_weights(self):
        """
        Adjust indicator weights based on historical accuracy.

        Weight adjustment formula:
        - Baseline accuracy assumed to be 50%
        - Indicators with >60% accuracy get boosted
        - Indicators with <40% accuracy get reduced
        - Weights are bounded between 0.5 and 2.0
        """
        baseline = 50.0

        for ind, stats in self.data.get("indicator_stats", {}).items():
            if stats["samples"] < 10:
                continue  # Need enough samples

            accuracy = stats["accuracy"]

            # Calculate weight adjustment
            # accuracy 70% -> weight 1.4
            # accuracy 50% -> weight 1.0
            # accuracy 30% -> weight 0.6
            adjustment = (accuracy - baseline) / 50.0  # -1 to +1 range
            new_weight = 1.0 + adjustment

            # Bound weights
            new_weight = max(0.5, min(2.0, new_weight))

            # Smooth adjustment (don't change too fast)
            old_weight = self.data["weights"].get(ind, 1.0)
            self.data["weights"][ind] = round(0.7 * old_weight + 0.3 * new_weight, 2)

        self.save_data()

    def get_weight(self, indicator):
        """Get current weight for an indicator"""
        return self.data["weights"].get(indicator, 1.0)

    def get_stats_summary(self):
        """Get summary of learning stats"""
        stats = self.data.get("indicator_stats", {})
        if not stats:
            return "No learning data yet"

        # Sort by accuracy
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]["accuracy"], reverse=True)

        lines = ["TOP PERFORMING INDICATORS:"]
        for ind, s in sorted_stats[:5]:
            lines.append(f"  {ind}: {s['accuracy']:.0f}% accuracy ({s['samples']} samples)")

        if len(sorted_stats) > 5:
            lines.append("\nLOWEST PERFORMING:")
            for ind, s in sorted_stats[-3:]:
                lines.append(f"  {ind}: {s['accuracy']:.0f}% accuracy ({s['samples']} samples)")

        return "\n".join(lines)

# Global learning system instance
learning = LearningSystem()

# Stocks to scan - 200+ stocks across all major sectors
SCAN_STOCKS = [
    # ===== US MEGA CAP TECH =====
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "SPCX",

    # ===== US LARGE CAP TECH =====
    "AMD", "NFLX", "CRM", "ADBE", "INTC", "CSCO", "QCOM", "TXN", "IBM", "NOW",
    "INTU", "AMAT", "MU", "LRCX", "ADI", "KLAC", "SNPS", "CDNS", "MRVL", "PANW",
    "CRWD", "FTNT", "ZS", "DDOG", "NET", "SNOW", "MDB", "TEAM", "WDAY", "SPLK",

    # ===== FINTECH & PAYMENTS =====
    "PYPL", "SQ", "SHOP", "COIN", "HOOD", "SOFI", "AFRM", "UPST", "NU", "MELI",

    # ===== HIGH GROWTH TECH =====
    "PLTR", "UBER", "LYFT", "ABNB", "DASH", "RBLX", "U", "PATH", "DOCN", "CFLT",
    "GTLB", "ESTC", "HUBS", "VEEV", "BILL", "PCTY", "PAYC", "ZI", "TTD", "ROKU",

    # ===== SEMICONDUCTORS =====
    "TSM", "ASML", "ARM", "SMCI", "ON", "NXPI", "MCHP", "SWKS", "QRVO", "WOLF",

    # ===== AI & ROBOTICS =====
    "CRWV", "AI", "BBAI", "SOUN", "GFAI", "PRCT", "PATH", "ISRG", "NUVA", "IRTC",

    # ===== FINANCE - BANKS =====
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC", "SCHW",
    "COF", "AXP", "DFS", "SYF", "ALLY",

    # ===== FINANCE - INSURANCE =====
    "BRK-B", "PGR", "TRV", "AIG", "MET", "PRU", "AFL", "ALL", "CB", "HIG",

    # ===== FINANCE - ASSET MGMT =====
    "BLK", "SPGI", "ICE", "CME", "MCO", "MSCI", "NDAQ", "CBOE", "FDS", "MORN",

    # ===== PAYMENTS =====
    "V", "MA", "FIS", "FISV", "GPN", "FI", "WEX", "FOUR",

    # ===== HEALTHCARE - PHARMA =====
    "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "AMGN", "GILD", "REGN", "VRTX",
    "BIIB", "MRNA", "BNTX", "AZN", "NVO", "SNY", "GSK", "TAK", "NVS", "RHHBY",

    # ===== HEALTHCARE - BIOTECH =====
    "SGEN", "ALNY", "ILMN", "EXAS", "DXCM", "ALGN", "PODD", "HOLX", "IDXX", "TECH",

    # ===== HEALTHCARE - SERVICES =====
    "UNH", "CVS", "CI", "ELV", "HCA", "HUM", "CNC", "MOH", "DVA", "THC",

    # ===== HEALTHCARE - DEVICES =====
    "ABT", "MDT", "SYK", "BSX", "EW", "ZBH", "BAX", "BDX", "ISRG", "TFX",

    # ===== ENERGY - OIL & GAS =====
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "MPC", "VLO", "PSX", "PXD",
    "DVN", "FANG", "HES", "HAL", "BKR", "MRO", "APA", "OVV", "CTRA", "MTDR",

    # ===== ENERGY - RENEWABLE =====
    "ENPH", "SEDG", "FSLR", "RUN", "NOVA", "SPWR", "JKS", "DQ", "ARRY", "MAXN",
    "NEE", "AES", "CEG", "VST", "NRG", "ORA", "BEP", "CWEN", "BEPC", "AQN",

    # ===== CONSUMER - RETAIL =====
    "WMT", "COST", "TGT", "HD", "LOW", "TJX", "ROST", "DG", "DLTR", "BBY",
    "ULTA", "ORLY", "AZO", "AAP", "KMX", "AN", "CVNA", "EBAY", "ETSY", "W",

    # ===== CONSUMER - RESTAURANTS =====
    "MCD", "SBUX", "CMG", "DPZ", "YUM", "QSR", "DARDEN", "TXRH", "WING", "CAVA",

    # ===== CONSUMER - APPAREL =====
    "NKE", "LULU", "GPS", "ANF", "AEO", "URBN", "RL", "PVH", "HBI", "VFC",

    # ===== CONSUMER - LUXURY =====
    "LVMUY", "HESAY", "CFRUY", "PPRUY",

    # ===== CONSUMER - FOOD & BEV =====
    "KO", "PEP", "MDLZ", "KHC", "GIS", "K", "CPB", "SJM", "HSY", "MKC",
    "STZ", "BUD", "TAP", "SAM", "DEO", "BF-B",

    # ===== INDUSTRIAL - MANUFACTURING =====
    "CAT", "DE", "HON", "GE", "MMM", "EMR", "ITW", "PH", "ROK", "ETN",
    "DOV", "IR", "XYL", "AME", "ROP", "CMI", "PCAR", "AGCO", "TTC", "OSK",

    # ===== INDUSTRIAL - AEROSPACE =====
    "BA", "RTX", "LMT", "NOC", "GD", "TXT", "HII", "LHX", "TDG", "HEI",

    # ===== INDUSTRIAL - TRANSPORT =====
    "UNP", "CSX", "NSC", "UPS", "FDX", "ODFL", "XPO", "JBHT", "LSTR", "SAIA",
    "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "SAVE",

    # ===== TELECOM =====
    "T", "VZ", "TMUS", "LUMN", "FYBR", "USM", "TDS",

    # ===== MEDIA & ENTERTAINMENT =====
    "DIS", "CMCSA", "WBD", "PARA", "FOX", "FOXA", "NWSA", "NWS", "LYV", "MSGS",
    "SPOT", "SIRI", "IHRT", "TME", "SE", "BILI", "IQ",

    # ===== GAMING =====
    "ATVI", "EA", "TTWO", "RBLX", "DKNG", "PENN", "MGM", "CZR", "WYNN", "LVS",

    # ===== REAL ESTATE =====
    "AMT", "PLD", "CCI", "EQIX", "SPG", "PSA", "O", "WELL", "AVB", "EQR",
    "VTR", "DLR", "ARE", "BXP", "SLG", "VNO", "KIM", "REG", "FRT", "HST",

    # ===== MATERIALS =====
    "LIN", "APD", "SHW", "ECL", "DD", "DOW", "LYB", "PPG", "NEM", "FCX",
    "NUE", "STLD", "CLF", "X", "AA", "CENX", "ATI", "CMC", "RS", "WOR",

    # ===== UTILITIES =====
    "NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "WEC", "ES",
    "ED", "DTE", "AEE", "CMS", "CNP", "NI", "PNW", "OGE", "NRG", "EVRG",

    # ===== DANISH / NORDIC =====
    "NOVO-B.CO", "MAERSK-B.CO", "DSV.CO", "VWS.CO", "ORSTED.CO", "CARL-B.CO",
    "GN.CO", "COLO-B.CO", "PNDORA.CO", "TRYG.CO", "AMBU-B.CO", "CHR.CO",
    "JYSK.CO", "RBREW.CO", "ROCK-B.CO", "SIM.CO", "SCHO.CO", "NZYM-B.CO",
    "HH.CO", "FLS.CO", "DEMANT.CO", "BAVA.CO", "NKT.CO",

    # ===== UK =====
    "RR.L", "SHEL.L", "BP.L", "AZN.L", "GSK.L", "ULVR.L", "DGE.L", "RIO.L",
    "HSBA.L", "LLOY.L", "BARC.L", "NWG.L", "STAN.L", "LGEN.L", "AV.L",
    "VOD.L", "BT-A.L", "IAG.L", "EZJ.L",

    # ===== GERMAN =====
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "BAS.DE", "BAYN.DE", "MBG.DE",
    "BMW.DE", "VOW3.DE", "ADS.DE", "MRK.DE", "HEN3.DE", "RWE.DE", "EON.DE",

    # ===== CRYPTO =====
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "AVAX-USD",
    "DOGE-USD", "DOT-USD", "MATIC-USD", "LINK-USD", "SHIB-USD", "UNI-USD",
    "ATOM-USD", "LTC-USD", "XLM-USD", "NEAR-USD", "APT-USD", "ARB-USD", "OP-USD",
    "RENDER-USD", "INJ-USD", "SEI-USD", "SUI-USD", "TIA-USD", "JUP-USD", "WIF-USD",

    # ===== CRYPTO STOCKS =====
    "MSTR", "MARA", "RIOT", "CLSK", "HUT", "BITF", "CIFR", "IREN", "CORZ", "BTBT",
]

# Signal thresholds - only alert for very strong signals
GOLDEN_THRESHOLD = 90  # SMS alert threshold - very strong buy only
GOOD_THRESHOLD = 75    # Regular buy signal (no SMS)

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def fetch_data(symbol, period="6mo"):
    """Fetch more data for better pattern recognition"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty or len(data) < 60:
            return None
        return data
    except:
        return None

def fetch_market_data():
    """Get SPY data for relative strength comparison"""
    try:
        spy = yf.Ticker("SPY")
        return spy.history(period="3mo")
    except:
        return None

def calculate_indicators(data):
    """Calculate all technical indicators"""
    if not TA_AVAILABLE or data is None or len(data) < 50:
        return data

    try:
        # RSI
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()

        # MACD
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()
        data['MACD_Hist'] = macd.macd_diff()

        # Moving Averages
        data['SMA_10'] = ta.trend.SMAIndicator(data['Close'], window=10).sma_indicator()
        data['SMA_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator()
        data['SMA_200'] = ta.trend.SMAIndicator(data['Close'], window=200).sma_indicator()
        data['EMA_9'] = ta.trend.EMAIndicator(data['Close'], window=9).ema_indicator()
        data['EMA_21'] = ta.trend.EMAIndicator(data['Close'], window=21).ema_indicator()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'], window=20, window_dev=2)
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()
        data['BB_Mid'] = bb.bollinger_mavg()
        data['BB_Width'] = (data['BB_Upper'] - data['BB_Lower']) / data['BB_Mid']

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(data['High'], data['Low'], data['Close'])
        data['Stoch_K'] = stoch.stoch()
        data['Stoch_D'] = stoch.stoch_signal()

        # ADX
        adx = ta.trend.ADXIndicator(data['High'], data['Low'], data['Close'])
        data['ADX'] = adx.adx()
        data['DI_Plus'] = adx.adx_pos()
        data['DI_Minus'] = adx.adx_neg()

        # ATR for volatility
        data['ATR'] = ta.volatility.AverageTrueRange(data['High'], data['Low'], data['Close']).average_true_range()

        # Volume indicators
        data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']

        # OBV for volume trend
        data['OBV'] = ta.volume.OnBalanceVolumeIndicator(data['Close'], data['Volume']).on_balance_volume()
        data['OBV_SMA'] = data['OBV'].rolling(window=20).mean()

        # Williams %R
        data['Williams_R'] = ta.momentum.WilliamsRIndicator(data['High'], data['Low'], data['Close']).williams_r()

        # CCI
        data['CCI'] = ta.trend.CCIIndicator(data['High'], data['Low'], data['Close']).cci()

        # Price changes
        data['Change_1d'] = data['Close'].pct_change(1) * 100
        data['Change_5d'] = data['Close'].pct_change(5) * 100
        data['Change_20d'] = data['Close'].pct_change(20) * 100

    except Exception as e:
        log(f"Indicator error: {e}")

    return data

def detect_candlestick_patterns(data):
    """Detect bullish candlestick patterns with learned weights"""
    if len(data) < 3:
        return []

    patterns = []

    try:
        # Get last 3 candles
        c0 = data.iloc[-1]  # Current
        c1 = data.iloc[-2]  # Previous
        c2 = data.iloc[-3]  # 2 days ago

        body_0 = c0['Close'] - c0['Open']
        body_1 = c1['Close'] - c1['Open']
        range_0 = c0['High'] - c0['Low']
        range_1 = c1['High'] - c1['Low']

        # Hammer: Small body at top, long lower shadow
        if range_0 > 0:
            lower_shadow = min(c0['Open'], c0['Close']) - c0['Low']
            upper_shadow = c0['High'] - max(c0['Open'], c0['Close'])
            body_size = abs(body_0)

            if lower_shadow > body_size * 2 and upper_shadow < body_size * 0.5:
                weight = learning.get_weight("HAMMER")
                patterns.append(("HAMMER", 15 * weight, "Hammer pattern - reversal signal"))

        # Bullish Engulfing: Current green candle engulfs previous red
        if body_1 < 0 and body_0 > 0:  # Previous red, current green
            if c0['Open'] <= c1['Close'] and c0['Close'] >= c1['Open']:
                weight = learning.get_weight("ENGULFING")
                patterns.append(("ENGULFING", 20 * weight, "Bullish engulfing - strong reversal"))

        # Morning Star: Down, small body, up
        if len(data) >= 3:
            body_2 = c2['Close'] - c2['Open']
            if body_2 < 0 and abs(body_1) < abs(body_2) * 0.3 and body_0 > abs(body_2) * 0.5:
                weight = learning.get_weight("MORNING_STAR")
                patterns.append(("MORNING_STAR", 25 * weight, "Morning star - major reversal"))

        # Dragonfly Doji: Open = Close at top, long lower shadow
        if range_0 > 0 and abs(body_0) < range_0 * 0.1:
            lower_shadow = min(c0['Open'], c0['Close']) - c0['Low']
            if lower_shadow > range_0 * 0.6:
                patterns.append(("DRAGONFLY", 12, "Dragonfly doji - potential reversal"))

        # Three White Soldiers: Three consecutive green candles with higher closes
        if len(data) >= 3:
            if body_0 > 0 and body_1 > 0 and body_2 > 0:
                if c0['Close'] > c1['Close'] > c2['Close']:
                    weight = learning.get_weight("THREE_SOLDIERS")
                    patterns.append(("THREE_SOLDIERS", 18 * weight, "Three white soldiers - bullish continuation"))

    except Exception as e:
        pass

    return patterns

def calculate_relative_strength(data, spy_data):
    """Calculate relative strength vs SPY with learned weights"""
    if data is None or spy_data is None or len(data) < 20 or len(spy_data) < 20:
        return 0, "N/A", False

    try:
        # Align dates
        stock_change = (data['Close'].iloc[-1] / data['Close'].iloc[-20] - 1) * 100
        spy_change = (spy_data['Close'].iloc[-1] / spy_data['Close'].iloc[-20] - 1) * 100

        rs = stock_change - spy_change
        weight = learning.get_weight("RELATIVE_STRENGTH")

        if rs > 10:
            return 15 * weight, f"Strong RS +{rs:.1f}% vs SPY", True
        elif rs > 5:
            return 10 * weight, f"Good RS +{rs:.1f}% vs SPY", True
        elif rs > 0:
            return 5 * weight, f"Positive RS +{rs:.1f}% vs SPY", True
        else:
            return 0, f"Weak RS {rs:.1f}% vs SPY", False

    except:
        return 0, "N/A", False

def detect_support_bounce(data):
    """Detect if price is bouncing off support with learned weights"""
    if data is None or len(data) < 20:
        return 0, None, False

    try:
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        weight = learning.get_weight("SUPPORT_BOUNCE")

        # Check BB lower bounce
        if pd.notna(latest['BB_Lower']):
            bb_range = latest['BB_Upper'] - latest['BB_Lower']
            if bb_range > 0:
                bb_pos = (latest['Close'] - latest['BB_Lower']) / bb_range
                if bb_pos < 0.25 and latest['Close'] > prev['Close']:
                    return 15 * weight, "Bouncing off BB lower support", True

        # Check SMA support
        if pd.notna(latest['SMA_50']) and pd.notna(prev['SMA_50']):
            # Price touched SMA50 and bounced
            if prev['Low'] <= prev['SMA_50'] * 1.01 and latest['Close'] > latest['SMA_50']:
                return 12 * weight, "Bouncing off SMA50 support", True

        # Check SMA20 support
        if pd.notna(latest['SMA_20']) and pd.notna(prev['SMA_20']):
            if prev['Low'] <= prev['SMA_20'] * 1.01 and latest['Close'] > latest['SMA_20']:
                return 8 * weight, "Bouncing off SMA20 support", True

    except:
        pass

    return 0, None, False

def detect_fresh_crossovers(data):
    """Detect crossovers that happened in the last 1-3 days with learned weights"""
    if data is None or len(data) < 5:
        return []

    signals = []

    try:
        # Check last 3 days for fresh crossovers
        for lookback in range(1, 4):
            if len(data) <= lookback:
                continue

            curr = data.iloc[-lookback]
            prev = data.iloc[-lookback-1]
            freshness = 4 - lookback  # More recent = higher multiplier

            # MACD Crossover
            if pd.notna(curr['MACD']) and pd.notna(curr['MACD_Signal']):
                if pd.notna(prev['MACD']) and pd.notna(prev['MACD_Signal']):
                    curr_diff = curr['MACD'] - curr['MACD_Signal']
                    prev_diff = prev['MACD'] - prev['MACD_Signal']

                    if curr_diff > 0 and prev_diff <= 0:
                        weight = learning.get_weight("MACD_CROSS")
                        score = 18 * freshness / 3 * weight
                        signals.append(("MACD_CROSS", score, f"MACD bullish cross ({lookback}d ago)"))

            # Stochastic Crossover from oversold
            if pd.notna(curr['Stoch_K']) and pd.notna(curr['Stoch_D']):
                if pd.notna(prev['Stoch_K']) and pd.notna(prev['Stoch_D']):
                    if curr['Stoch_K'] > curr['Stoch_D'] and prev['Stoch_K'] <= prev['Stoch_D']:
                        if curr['Stoch_K'] < 50:  # Coming from oversold
                            weight = learning.get_weight("STOCH_CROSS")
                            score = 15 * freshness / 3 * weight
                            signals.append(("STOCH_CROSS", score, f"Stoch bullish cross ({lookback}d ago)"))

            # EMA 9/21 Crossover
            if pd.notna(curr['EMA_9']) and pd.notna(curr['EMA_21']):
                if pd.notna(prev['EMA_9']) and pd.notna(prev['EMA_21']):
                    if curr['EMA_9'] > curr['EMA_21'] and prev['EMA_9'] <= prev['EMA_21']:
                        weight = learning.get_weight("EMA_CROSS")
                        score = 16 * freshness / 3 * weight
                        signals.append(("EMA_CROSS", score, f"EMA 9/21 golden cross ({lookback}d ago)"))

    except:
        pass

    return signals

def calculate_momentum_score(data):
    """Calculate momentum indicators score with learned weights"""
    if data is None or len(data) < 5:
        return 0, [], []

    score = 0
    reasons = []
    indicators_used = []

    try:
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # RSI Analysis - oversold recovery is most valuable
        if pd.notna(latest['RSI']):
            rsi = latest['RSI']
            rsi_prev = prev['RSI'] if pd.notna(prev['RSI']) else rsi

            # Oversold and recovering - BEST signal
            if rsi < 35 and rsi > rsi_prev:
                weight = learning.get_weight("RSI_RECOVERY")
                score += 20 * weight
                reasons.append(f"RSI oversold recovering ({rsi:.0f})")
                indicators_used.append("RSI_RECOVERY")
            elif 35 <= rsi < 45 and rsi > rsi_prev:
                weight = learning.get_weight("RSI_RECOVERY")
                score += 15 * weight
                reasons.append(f"RSI emerging from oversold ({rsi:.0f})")
                indicators_used.append("RSI_RECOVERY")
            elif rsi < 30:
                weight = learning.get_weight("RSI_OVERSOLD")
                score += 10 * weight
                reasons.append(f"RSI oversold ({rsi:.0f})")
                indicators_used.append("RSI_OVERSOLD")
            elif 45 <= rsi < 60:
                score += 8
                reasons.append(f"RSI neutral bullish ({rsi:.0f})")
            elif rsi >= 70:
                score -= 5  # Overbought - reduce score
                reasons.append(f"RSI overbought warning ({rsi:.0f})")

        # Williams %R - oversold recovery
        if pd.notna(latest['Williams_R']):
            wr = latest['Williams_R']
            wr_prev = prev['Williams_R'] if pd.notna(prev['Williams_R']) else wr

            if wr < -80 and wr > wr_prev:
                weight = learning.get_weight("WILLIAMS_R")
                score += 10 * weight
                reasons.append(f"Williams %R oversold reversal")
                indicators_used.append("WILLIAMS_R")

        # CCI - oversold recovery
        if pd.notna(latest['CCI']):
            cci = latest['CCI']
            if -200 < cci < -100:
                weight = learning.get_weight("CCI_OVERSOLD")
                score += 8 * weight
                reasons.append(f"CCI oversold ({cci:.0f})")
                indicators_used.append("CCI_OVERSOLD")

        # MACD Histogram momentum
        if pd.notna(latest['MACD_Hist']) and pd.notna(prev['MACD_Hist']):
            hist = latest['MACD_Hist']
            hist_prev = prev['MACD_Hist']

            # Histogram turning positive or accelerating
            if hist > 0 and hist > hist_prev:
                weight = learning.get_weight("MACD_MOMENTUM")
                score += 8 * weight
                reasons.append("MACD momentum accelerating")
                indicators_used.append("MACD_MOMENTUM")
            elif hist > hist_prev and hist_prev < 0:
                weight = learning.get_weight("MACD_MOMENTUM")
                score += 12 * weight
                reasons.append("MACD histogram turning up")
                indicators_used.append("MACD_MOMENTUM")

    except:
        pass

    return score, reasons, indicators_used

def calculate_trend_score(data):
    """Calculate trend alignment score with learned weights"""
    if data is None or len(data) < 50:
        return 0, [], []

    score = 0
    reasons = []
    indicators_used = []

    try:
        latest = data.iloc[-1]
        price = latest['Close']

        # Moving average alignment
        ma_above = 0
        ma_count = 0

        for ma in ['SMA_10', 'SMA_20', 'SMA_50', 'EMA_9', 'EMA_21']:
            if ma in data.columns and pd.notna(latest[ma]):
                ma_count += 1
                if price > latest[ma]:
                    ma_above += 1

        if ma_count > 0:
            ma_ratio = ma_above / ma_count
            if ma_ratio >= 0.8:
                weight = learning.get_weight("TREND_ABOVE_MA")
                score += 15 * weight
                reasons.append(f"Strong trend: above {ma_above}/{ma_count} MAs")
                indicators_used.append("TREND_ABOVE_MA")
            elif ma_ratio >= 0.6:
                weight = learning.get_weight("TREND_ABOVE_MA")
                score += 10 * weight
                reasons.append(f"Good trend: above {ma_above}/{ma_count} MAs")
                indicators_used.append("TREND_ABOVE_MA")
            elif ma_ratio <= 0.2:
                score -= 5  # Against trend

        # Golden cross check (SMA50 > SMA200)
        if pd.notna(latest.get('SMA_50')) and pd.notna(latest.get('SMA_200')):
            if latest['SMA_50'] > latest['SMA_200']:
                weight = learning.get_weight("GOLDEN_CROSS")
                score += 8 * weight
                reasons.append("Long-term uptrend (SMA50 > SMA200)")
                indicators_used.append("GOLDEN_CROSS")

        # ADX trend strength
        if pd.notna(latest['ADX']) and pd.notna(latest['DI_Plus']) and pd.notna(latest['DI_Minus']):
            adx = latest['ADX']
            if adx > 25:
                if latest['DI_Plus'] > latest['DI_Minus']:
                    weight = learning.get_weight("ADX_BULLISH")
                    score += 12 * weight
                    reasons.append(f"Strong bullish trend (ADX {adx:.0f})")
                    indicators_used.append("ADX_BULLISH")
                else:
                    score -= 8  # Strong bearish trend
            elif adx < 20:
                # Low ADX can be good for reversal plays
                pass

        # Price momentum
        if pd.notna(latest.get('Change_5d')):
            chg = latest['Change_5d']
            if 2 <= chg <= 15:
                score += 6
                reasons.append(f"5d momentum +{chg:.1f}%")
            elif chg < -10:
                score -= 5

    except:
        pass

    return score, reasons, indicators_used

def calculate_volume_score(data):
    """Calculate volume confirmation score with learned weights"""
    if data is None or len(data) < 20:
        return 1.0, [], []  # Return multiplier

    multiplier = 1.0
    reasons = []
    indicators_used = []

    try:
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # Volume ratio
        if pd.notna(latest['Volume_Ratio']):
            vr = latest['Volume_Ratio']

            if vr > 2.0 and latest['Close'] > prev['Close']:
                weight = learning.get_weight("VOLUME_BREAKOUT")
                multiplier = 1.0 + (0.3 * weight)  # Scale multiplier with weight
                reasons.append(f"High volume breakout ({vr:.1f}x avg)")
                indicators_used.append("VOLUME_BREAKOUT")
            elif vr > 1.5 and latest['Close'] > prev['Close']:
                multiplier = 1.15
                reasons.append(f"Above avg volume ({vr:.1f}x)")
            elif vr < 0.5:
                multiplier = 0.9
                reasons.append("Low volume warning")

        # OBV trend confirmation
        if pd.notna(latest['OBV']) and pd.notna(latest['OBV_SMA']):
            if latest['OBV'] > latest['OBV_SMA']:
                multiplier *= 1.05
                reasons.append("OBV confirms accumulation")

    except:
        pass

    return multiplier, reasons, indicators_used

def calculate_smart_score(data, spy_data=None):
    """
    Calculate intelligent confluence score with self-learning

    Philosophy:
    - Fresh signals (crossovers in last 1-3 days) are most valuable
    - Multiple confirmations multiply confidence
    - Oversold + reversal pattern is the holy grail
    - Volume confirms or denies the move
    - Relative strength shows market leadership
    - SELF-LEARNING: Weights adjust based on historical accuracy
    """
    if data is None or len(data) < 50:
        return 0, [], "NEUTRAL", []

    try:
        base_score = 0
        all_reasons = []
        all_indicators = []

        # 1. MOMENTUM INDICATORS (max ~40 points)
        momentum_score, momentum_reasons, momentum_indicators = calculate_momentum_score(data)
        base_score += momentum_score
        all_reasons.extend(momentum_reasons)
        all_indicators.extend(momentum_indicators)

        # 2. TREND ALIGNMENT (max ~35 points)
        trend_score, trend_reasons, trend_indicators = calculate_trend_score(data)
        base_score += trend_score
        all_reasons.extend(trend_reasons)
        all_indicators.extend(trend_indicators)

        # 3. FRESH CROSSOVERS - Most valuable! (max ~50 points)
        crossovers = detect_fresh_crossovers(data)
        for name, score, reason in crossovers:
            base_score += score
            all_reasons.append(reason)
            all_indicators.append(name)

        # 4. SUPPORT BOUNCE (max 15 points)
        support_score, support_reason, support_used = detect_support_bounce(data)
        base_score += support_score
        if support_reason:
            all_reasons.append(support_reason)
        if support_used:
            all_indicators.append("SUPPORT_BOUNCE")

        # 5. CANDLESTICK PATTERNS (max ~25 points)
        patterns = detect_candlestick_patterns(data)
        for name, score, reason in patterns:
            base_score += score
            all_reasons.append(reason)
            all_indicators.append(name)

        # 6. RELATIVE STRENGTH vs SPY (max 15 points)
        rs_score, rs_reason, rs_used = calculate_relative_strength(data, spy_data)
        base_score += rs_score
        if rs_reason != "N/A":
            all_reasons.append(rs_reason)
        if rs_used:
            all_indicators.append("RELATIVE_STRENGTH")

        # 7. VOLUME MULTIPLIER (0.9x to 1.3x)
        volume_mult, volume_reasons, volume_indicators = calculate_volume_score(data)
        all_reasons.extend(volume_reasons)
        all_indicators.extend(volume_indicators)

        # Apply volume multiplier
        final_score = base_score * volume_mult

        # Normalize to 0-100 scale
        # Max theoretical: ~180 * 1.3 = 234
        # Good score: 60-80
        # Great score: 80-100
        # Golden: 100+

        normalized_score = min(100, max(0, final_score * 0.55))  # Scale factor

        # Determine signal type - 90%+ for SMS alerts
        if normalized_score >= 90:
            signal = "STRONG BUY"  # Triggers SMS
        elif normalized_score >= 75:
            signal = "BUY"
        elif normalized_score >= 55:
            signal = "WATCH"
        elif normalized_score <= 30:
            signal = "AVOID"
        else:
            signal = "NEUTRAL"

        return normalized_score, all_reasons, signal, all_indicators

    except Exception as e:
        log(f"Score calculation error: {e}")
        return 0, [], "ERROR", []

def send_sms(message):
    if not TWILIO_AVAILABLE:
        log(f"[NO SMS] {message}")
        return False

    try:
        sid = os.environ.get('TWILIO_SID')
        token = os.environ.get('TWILIO_TOKEN')
        from_phone = os.environ.get('TWILIO_FROM')
        to_phone = os.environ.get('TWILIO_TO')

        if not all([sid, token, from_phone, to_phone]):
            log("[SMS] Missing Twilio credentials")
            return False

        client = TwilioClient(sid, token)
        client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        log(f"[SMS SENT]")
        return True
    except Exception as e:
        log(f"[SMS ERROR] {e}")
        return False

def main():
    log("=" * 60)
    log("GOLDEN OPPORTUNITY SCANNER v3.0")
    log("Self-Learning AI Signal Detection")
    log(f"Scanning {len(SCAN_STOCKS)} stocks")
    log(f"GOLDEN >= {GOLDEN_THRESHOLD}% | BUY >= {GOOD_THRESHOLD}%")
    log("=" * 60)

    # SELF-LEARNING: Update outcomes for past signals
    log("[LEARNING] Checking past signal outcomes...")
    learning.update_outcomes()

    # Show learning stats
    log("-" * 60)
    log(learning.get_stats_summary())
    log("-" * 60)

    # Fetch market data for relative strength
    spy_data = fetch_market_data()
    if spy_data is not None:
        log(f"SPY benchmark loaded: {len(spy_data)} days")

    golden_opportunities = []
    buy_signals = []

    for symbol in SCAN_STOCKS:
        try:
            data = fetch_data(symbol)
            if data is None:
                continue

            data = calculate_indicators(data)
            score, reasons, signal, indicators_used = calculate_smart_score(data, spy_data)
            price = data['Close'].iloc[-1]
            change = data['Change_1d'].iloc[-1] if 'Change_1d' in data.columns else 0

            if signal == "STRONG BUY" and score >= GOLDEN_THRESHOLD:
                golden_opportunities.append({
                    'symbol': symbol,
                    'score': score,
                    'price': price,
                    'change': change,
                    'reasons': reasons,
                    'signal': signal,
                    'indicators': indicators_used
                })
                log(f"[GOLDEN] {symbol}: {score:.0f}% @ ${price:.2f} ({change:+.1f}%)")
                for r in reasons[:5]:
                    log(f"         + {r}")

                # SELF-LEARNING: Log this signal for future tracking
                learning.log_signal(symbol, signal, score, indicators_used, price, reasons)

            elif signal in ["BUY", "STRONG BUY"] and score >= GOOD_THRESHOLD:
                buy_signals.append({
                    'symbol': symbol,
                    'score': score,
                    'price': price,
                    'change': change,
                    'reasons': reasons,
                    'signal': signal,
                    'indicators': indicators_used
                })
                log(f"[BUY]    {symbol}: {score:.0f}%")

                # SELF-LEARNING: Log this signal for future tracking
                learning.log_signal(symbol, signal, score, indicators_used, price, reasons)

            elif signal == "WATCH" and score >= 55:
                log(f"[WATCH]  {symbol}: {score:.0f}%")

        except Exception as e:
            continue

    log("-" * 60)

    # Report results
    if golden_opportunities:
        golden_opportunities.sort(key=lambda x: x['score'], reverse=True)
        log(f"GOLDEN OPPORTUNITIES: {len(golden_opportunities)}")

        msg_lines = ["[GOLDEN ALERT]", ""]
        for opp in golden_opportunities[:5]:
            msg_lines.append(f"{opp['symbol']}: {opp['score']:.0f}%")
            msg_lines.append(f"${opp['price']:.2f} ({opp['change']:+.1f}%)")
            msg_lines.append(f"{', '.join(opp['reasons'][:2])}")
            msg_lines.append("")

        msg_lines.append("Strong confluence - check now!")
        send_sms("\n".join(msg_lines))

    elif buy_signals:
        buy_signals.sort(key=lambda x: x['score'], reverse=True)
        log(f"BUY SIGNALS: {len(buy_signals)}")

        # Only SMS for top buy signals
        if buy_signals[0]['score'] >= 75:
            msg_lines = ["[BUY SIGNAL]", ""]
            for sig in buy_signals[:3]:
                msg_lines.append(f"{sig['symbol']}: {sig['score']:.0f}%")
            msg_lines.append("")
            msg_lines.append("Good setup detected")
            send_sms("\n".join(msg_lines))
    else:
        log("No strong signals found this scan")

    # SELF-LEARNING: Save all learning data
    learning.save_data()
    log(f"[LEARNING] Total signals tracked: {learning.data['total_signals']}")
    log("Scan complete")

if __name__ == "__main__":
    main()
