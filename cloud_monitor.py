#!/usr/bin/env python3
"""
Cloud Portfolio Monitor - Runs on GitHub Actions
Reads watchlist from watchlist.json and sends SMS alerts via Twilio
"""

import os
import json
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

def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def load_watchlist():
    """Load watchlist from JSON file"""
    try:
        with open('watchlist.json', 'r') as f:
            data = json.load(f)
            return data.get('holdings', []) + data.get('watchlist', [])
    except Exception as e:
        log(f"Error loading watchlist: {e}")
        return []

def fetch_stock_data(symbol, period="3mo"):
    """Fetch stock data from Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            return None
        return data
    except Exception as e:
        log(f"Error fetching {symbol}: {e}")
        return None

def calculate_indicators(data):
    """Calculate technical indicators"""
    if not TA_AVAILABLE or data is None or len(data) < 20:
        return data

    try:
        # RSI
        data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=14).rsi()

        # MACD
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_Signal'] = macd.macd_signal()

        # Moving Averages
        data['SMA_20'] = ta.trend.SMAIndicator(data['Close'], window=20).sma_indicator()
        data['SMA_50'] = ta.trend.SMAIndicator(data['Close'], window=50).sma_indicator()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'], window=20)
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(data['High'], data['Low'], data['Close'])
        data['Stoch_K'] = stoch.stoch()

    except Exception as e:
        log(f"Error calculating indicators: {e}")

    return data

def calculate_signal(data):
    """Calculate trading signal and score"""
    if data is None or len(data) < 20:
        return "HOLD", 50

    try:
        latest = data.iloc[-1]
        score = 50

        # RSI
        if 'RSI' in data.columns and pd.notna(latest['RSI']):
            rsi = latest['RSI']
            if rsi < 30:
                score += 15
            elif rsi > 70:
                score -= 15
            elif rsi < 40:
                score += 5
            elif rsi > 60:
                score -= 5

        # MACD
        if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
            if pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']):
                if latest['MACD'] > latest['MACD_Signal']:
                    score += 10
                else:
                    score -= 10

        # Moving Averages
        if 'SMA_20' in data.columns and 'SMA_50' in data.columns:
            if pd.notna(latest['SMA_20']) and pd.notna(latest['SMA_50']):
                if latest['Close'] > latest['SMA_20'] > latest['SMA_50']:
                    score += 15
                elif latest['Close'] < latest['SMA_20'] < latest['SMA_50']:
                    score -= 15
                elif latest['Close'] > latest['SMA_20']:
                    score += 5
                elif latest['Close'] < latest['SMA_20']:
                    score -= 5

        # Bollinger Bands
        if 'BB_Upper' in data.columns and 'BB_Lower' in data.columns:
            if pd.notna(latest['BB_Upper']) and pd.notna(latest['BB_Lower']):
                if latest['Close'] < latest['BB_Lower']:
                    score += 10
                elif latest['Close'] > latest['BB_Upper']:
                    score -= 10

        # Stochastic
        if 'Stoch_K' in data.columns and pd.notna(latest['Stoch_K']):
            if latest['Stoch_K'] < 20:
                score += 10
            elif latest['Stoch_K'] > 80:
                score -= 10

        score = max(0, min(100, score))

        if score >= 65:
            signal = "BUY"
        elif score <= 35:
            signal = "SELL"
        else:
            signal = "HOLD"

        return signal, score

    except Exception as e:
        log(f"Error calculating signal: {e}")
        return "HOLD", 50

def send_sms(message):
    """Send SMS via Twilio using environment variables"""
    if not TWILIO_AVAILABLE:
        log(f"[NO SMS] {message}")
        return False

    try:
        sid = os.environ.get('TWILIO_SID')
        token = os.environ.get('TWILIO_TOKEN')
        from_phone = os.environ.get('TWILIO_FROM')
        to_phone = os.environ.get('TWILIO_TO')

        if not all([sid, token, from_phone, to_phone]):
            log("[SMS] Missing Twilio environment variables")
            log(f"[ALERT] {message}")
            return False

        client = TwilioClient(sid, token)
        client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        log(f"[SMS SENT] {message}")
        return True

    except Exception as e:
        log(f"[SMS ERROR] {e}")
        return False

def load_last_signals():
    """Load last signals from file"""
    try:
        with open('last_signals.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_last_signals(signals):
    """Save signals to file for next run"""
    try:
        with open('last_signals.json', 'w') as f:
            json.dump(signals, f)
    except Exception as e:
        log(f"Error saving signals: {e}")

def main():
    """Main check function"""
    log("=" * 50)
    log("CLOUD PORTFOLIO MONITOR")
    log("=" * 50)

    watchlist = load_watchlist()
    if not watchlist:
        log("No symbols to monitor")
        return

    log(f"Checking {len(watchlist)} symbols...")

    last_signals = load_last_signals()
    current_signals = {}
    alerts = []

    for item in watchlist:
        symbol = item.get('symbol', item) if isinstance(item, dict) else item

        data = fetch_stock_data(symbol)
        if data is None:
            continue

        data = calculate_indicators(data)
        signal, score = calculate_signal(data)
        current_price = data['Close'].iloc[-1]

        current_signals[symbol] = signal
        prev_signal = last_signals.get(symbol, "HOLD")

        # Check for SELL signal change
        if signal == "SELL" and prev_signal != "SELL":
            alert_msg = f"[SELL ALERT] {symbol}: Score {score:.0f}%, Price ${current_price:.2f}"
            alerts.append(alert_msg)
            log(f"[!] {symbol}: {signal} ({score:.0f}%) @ ${current_price:.2f} - ALERT!")
        else:
            log(f"    {symbol}: {signal} ({score:.0f}%) @ ${current_price:.2f}")

    # Send alerts
    if alerts:
        full_message = "Trading Signals Alert\n\n" + "\n".join(alerts)
        send_sms(full_message)
    else:
        log("No new SELL signals detected")

    # Save current signals for next run
    save_last_signals(current_signals)

    log("-" * 50)
    log("Check complete")

if __name__ == "__main__":
    main()
