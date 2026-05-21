#!/usr/bin/env python3
"""
Golden Opportunity Scanner - Finds stocks with extremely strong BUY signals
Runs on GitHub Actions and sends SMS alerts for exceptional opportunities
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime

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

# Stocks to scan for golden opportunities
SCAN_STOCKS = [
    # US Large Cap
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "CRM",
    "ORCL", "INTC", "CSCO", "ADBE", "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "UBER",
    # Finance
    "JPM", "BAC", "GS", "MS", "V", "MA", "AXP",
    # Healthcare
    "JNJ", "PFE", "UNH", "MRK", "ABBV", "LLY", "BMY",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY",
    # Consumer
    "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD",
    # Industrial
    "CAT", "DE", "BA", "HON", "GE", "MMM",
    # Danish
    "NOVO-B.CO", "MAERSK-B.CO", "DSV.CO", "VWS.CO", "ORSTED.CO", "CARL-B.CO",
    # UK
    "RR.L",
    # Crypto
    "BTC-USD", "ETH-USD", "SOL-USD", "RENDER-USD",
]

# Minimum score to be considered a golden opportunity
GOLDEN_THRESHOLD = 85

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def fetch_data(symbol, period="3mo"):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return None
        return data
    except:
        return None

def calculate_indicators(data):
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
        data['SMA_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator()
        data['EMA_12'] = ta.trend.EMAIndicator(data['Close'], window=12).ema_indicator()
        data['EMA_26'] = ta.trend.EMAIndicator(data['Close'], window=26).ema_indicator()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'], window=20)
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()
        data['BB_Mid'] = bb.bollinger_mavg()

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(data['High'], data['Low'], data['Close'])
        data['Stoch_K'] = stoch.stoch()
        data['Stoch_D'] = stoch.stoch_signal()

        # ADX (trend strength)
        adx = ta.trend.ADXIndicator(data['High'], data['Low'], data['Close'])
        data['ADX'] = adx.adx()
        data['DI_Plus'] = adx.adx_pos()
        data['DI_Minus'] = adx.adx_neg()

        # Volume
        data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()

    except Exception as e:
        log(f"Indicator error: {e}")

    return data

def calculate_golden_score(data):
    """Calculate score with focus on strong upward momentum"""
    if data is None or len(data) < 50:
        return 0, []

    try:
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        score = 50
        reasons = []

        # RSI - look for oversold bouncing up or strong momentum
        if 'RSI' in data.columns and pd.notna(latest['RSI']):
            rsi = latest['RSI']
            rsi_prev = prev['RSI'] if pd.notna(prev['RSI']) else rsi

            if 30 < rsi < 50 and rsi > rsi_prev:
                score += 15
                reasons.append(f"RSI recovering ({rsi:.0f})")
            elif 50 < rsi < 70:
                score += 10
                reasons.append(f"RSI bullish ({rsi:.0f})")
            elif rsi < 30:
                score += 5
                reasons.append(f"RSI oversold ({rsi:.0f})")

        # MACD - bullish crossover or positive histogram
        if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
            if pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']):
                macd_diff = latest['MACD'] - latest['MACD_Signal']
                macd_diff_prev = prev['MACD'] - prev['MACD_Signal'] if pd.notna(prev['MACD']) else macd_diff

                # Fresh bullish crossover
                if macd_diff > 0 and macd_diff_prev <= 0:
                    score += 20
                    reasons.append("MACD bullish crossover!")
                elif macd_diff > 0:
                    score += 10
                    reasons.append("MACD bullish")

                # Histogram increasing
                if 'MACD_Hist' in data.columns:
                    hist = latest['MACD_Hist']
                    hist_prev = prev['MACD_Hist'] if pd.notna(prev['MACD_Hist']) else hist
                    if hist > hist_prev and hist > 0:
                        score += 5
                        reasons.append("MACD momentum increasing")

        # Moving Averages - price above all MAs in uptrend
        if 'SMA_20' in data.columns and 'SMA_50' in data.columns:
            if pd.notna(latest['SMA_20']) and pd.notna(latest['SMA_50']):
                price = latest['Close']
                if price > latest['SMA_20'] > latest['SMA_50']:
                    score += 15
                    reasons.append("Strong uptrend (Price > SMA20 > SMA50)")
                elif price > latest['SMA_20']:
                    score += 8
                    reasons.append("Above SMA20")

        # EMA crossover
        if 'EMA_12' in data.columns and 'EMA_26' in data.columns:
            if pd.notna(latest['EMA_12']) and pd.notna(latest['EMA_26']):
                if latest['EMA_12'] > latest['EMA_26']:
                    ema_diff_prev = prev['EMA_12'] - prev['EMA_26'] if pd.notna(prev['EMA_12']) else 1
                    if ema_diff_prev <= 0:
                        score += 15
                        reasons.append("EMA golden cross!")
                    else:
                        score += 5

        # Bollinger Bands - bouncing off lower band
        if 'BB_Lower' in data.columns and 'BB_Upper' in data.columns:
            if pd.notna(latest['BB_Lower']):
                price = latest['Close']
                bb_range = latest['BB_Upper'] - latest['BB_Lower']
                bb_position = (price - latest['BB_Lower']) / bb_range if bb_range > 0 else 0.5

                if bb_position < 0.3 and price > prev['Close']:
                    score += 10
                    reasons.append("Bouncing from BB lower")

        # Stochastic - oversold and turning up
        if 'Stoch_K' in data.columns and 'Stoch_D' in data.columns:
            if pd.notna(latest['Stoch_K']) and pd.notna(latest['Stoch_D']):
                k, d = latest['Stoch_K'], latest['Stoch_D']
                k_prev = prev['Stoch_K'] if pd.notna(prev['Stoch_K']) else k

                if k < 30 and k > k_prev:
                    score += 10
                    reasons.append("Stochastic oversold reversal")
                elif k > d and k_prev <= prev['Stoch_D']:
                    score += 8
                    reasons.append("Stochastic bullish cross")

        # ADX - strong trend
        if 'ADX' in data.columns and 'DI_Plus' in data.columns and 'DI_Minus' in data.columns:
            if pd.notna(latest['ADX']) and pd.notna(latest['DI_Plus']):
                if latest['ADX'] > 25 and latest['DI_Plus'] > latest['DI_Minus']:
                    score += 10
                    reasons.append(f"Strong bullish trend (ADX {latest['ADX']:.0f})")

        # Volume confirmation
        if 'Volume_SMA' in data.columns and pd.notna(latest['Volume_SMA']):
            if latest['Volume'] > latest['Volume_SMA'] * 1.5:
                score += 5
                reasons.append("High volume confirmation")

        # Price momentum (last 5 days)
        if len(data) >= 5:
            five_day_return = (latest['Close'] / data['Close'].iloc[-5] - 1) * 100
            if 2 < five_day_return < 15:
                score += 5
                reasons.append(f"5-day momentum +{five_day_return:.1f}%")

        score = min(100, max(0, score))
        return score, reasons

    except Exception as e:
        log(f"Score error: {e}")
        return 0, []

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
    log("GOLDEN OPPORTUNITY SCANNER")
    log(f"Scanning {len(SCAN_STOCKS)} stocks for scores >= {GOLDEN_THRESHOLD}%")
    log("=" * 60)

    golden_opportunities = []

    for symbol in SCAN_STOCKS:
        try:
            data = fetch_data(symbol)
            if data is None:
                continue

            data = calculate_indicators(data)
            score, reasons = calculate_golden_score(data)
            price = data['Close'].iloc[-1]

            if score >= GOLDEN_THRESHOLD:
                golden_opportunities.append({
                    'symbol': symbol,
                    'score': score,
                    'price': price,
                    'reasons': reasons
                })
                log(f"[GOLDEN] {symbol}: {score}% @ ${price:.2f}")
                for r in reasons:
                    log(f"         - {r}")
            elif score >= 70:
                log(f"[WATCH]  {symbol}: {score}%")

        except Exception as e:
            continue

    log("-" * 60)

    if golden_opportunities:
        # Sort by score
        golden_opportunities.sort(key=lambda x: x['score'], reverse=True)

        log(f"Found {len(golden_opportunities)} GOLDEN OPPORTUNITIES!")

        # Build SMS message
        msg_lines = ["[GOLDEN OPPORTUNITY ALERT]", ""]
        for opp in golden_opportunities[:5]:  # Top 5
            msg_lines.append(f"{opp['symbol']}: {opp['score']}%")
            msg_lines.append(f"  ${opp['price']:.2f}")
            msg_lines.append(f"  {', '.join(opp['reasons'][:2])}")
            msg_lines.append("")

        msg_lines.append("Alt peger op - tjek dem nu!")

        message = "\n".join(msg_lines)
        send_sms(message)
    else:
        log("No golden opportunities found this scan")

    log("Scan complete")

if __name__ == "__main__":
    main()
