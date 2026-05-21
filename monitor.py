#!/usr/bin/env python3
"""
Portfolio Monitor - Background script for SMS alerts
Runs independently of Streamlit app.
Checks portfolio signals and sends SMS when SELL signal detected.
"""

import time
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
import pandas as pd
from journal.database import JournalDB

# Technical analysis
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    print("[WARNING] ta library not available", flush=True)

# Twilio for SMS
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("[WARNING] Twilio not installed - SMS disabled", flush=True)

# Configuration
CHECK_INTERVAL_MINUTES = 30  # Check every 30 minutes
MARKET_HOURS_ONLY = True     # Only check during market hours (9:30-16:00 ET)

# Track last signal to detect changes
last_signals = {}

def log(message):
    """Print with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def is_market_open():
    """Check if US market is open (rough check)"""
    if not MARKET_HOURS_ONLY:
        return True
    now = datetime.now()
    # Monday-Friday, 9:30-16:00 ET (adjust for your timezone)
    if now.weekday() >= 5:  # Weekend
        return False
    hour = now.hour
    # Assuming you're in a European timezone (CET/CEST)
    # US market: 15:30-22:00 CET
    if hour < 15 or hour >= 22:
        return False
    return True

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
        data['EMA_12'] = ta.trend.EMAIndicator(data['Close'], window=12).ema_indicator()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(data['Close'], window=20)
        data['BB_Upper'] = bb.bollinger_hband()
        data['BB_Lower'] = bb.bollinger_lband()

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(data['High'], data['Low'], data['Close'])
        data['Stoch_K'] = stoch.stoch()
        data['Stoch_D'] = stoch.stoch_signal()

    except Exception as e:
        log(f"Error calculating indicators: {e}")

    return data

def calculate_signal(data):
    """Calculate trading signal and score"""
    if data is None or len(data) < 20:
        return "HOLD", 50

    try:
        latest = data.iloc[-1]
        score = 50  # Start neutral

        # RSI
        if 'RSI' in data.columns and pd.notna(latest['RSI']):
            rsi = latest['RSI']
            if rsi < 30:
                score += 15  # Oversold = bullish
            elif rsi > 70:
                score -= 15  # Overbought = bearish
            elif rsi < 40:
                score += 5
            elif rsi > 60:
                score -= 5

        # MACD
        if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
            if pd.notna(latest['MACD']) and pd.notna(latest['MACD_Signal']):
                if latest['MACD'] > latest['MACD_Signal']:
                    score += 10  # Bullish crossover
                else:
                    score -= 10  # Bearish crossover

        # Moving Averages
        if 'SMA_20' in data.columns and 'SMA_50' in data.columns:
            if pd.notna(latest['SMA_20']) and pd.notna(latest['SMA_50']):
                if latest['Close'] > latest['SMA_20'] > latest['SMA_50']:
                    score += 15  # Strong uptrend
                elif latest['Close'] < latest['SMA_20'] < latest['SMA_50']:
                    score -= 15  # Strong downtrend
                elif latest['Close'] > latest['SMA_20']:
                    score += 5
                elif latest['Close'] < latest['SMA_20']:
                    score -= 5

        # Bollinger Bands
        if 'BB_Upper' in data.columns and 'BB_Lower' in data.columns:
            if pd.notna(latest['BB_Upper']) and pd.notna(latest['BB_Lower']):
                if latest['Close'] < latest['BB_Lower']:
                    score += 10  # Oversold
                elif latest['Close'] > latest['BB_Upper']:
                    score -= 10  # Overbought

        # Stochastic
        if 'Stoch_K' in data.columns:
            if pd.notna(latest['Stoch_K']):
                if latest['Stoch_K'] < 20:
                    score += 10
                elif latest['Stoch_K'] > 80:
                    score -= 10

        # Determine signal
        score = max(0, min(100, score))  # Clamp to 0-100

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

def send_sms(message, db):
    """Send SMS via Twilio"""
    if not TWILIO_AVAILABLE:
        log("[SMS DISABLED] " + message)
        return False

    try:
        sid = db.get_setting('twilio_sid')
        token = db.get_setting('twilio_token')
        from_phone = db.get_setting('twilio_from')
        to_phone = db.get_setting('twilio_to')

        if not all([sid, token, from_phone, to_phone]):
            log("[SMS] Missing Twilio settings - configure in app Settings")
            log("[ALERT] " + message)
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
        log("[ALERT] " + message)
        return False

def check_portfolio(db):
    """Check all holdings for SELL signals"""
    global last_signals

    holdings = db.get_holdings()
    if not holdings:
        log("No holdings to monitor")
        return

    log(f"Checking {len(holdings)} positions...")

    for holding in holdings:
        symbol = holding['symbol']
        qty = holding['quantity']
        avg_price = holding['avg_price']

        # Fetch and analyze
        data = fetch_stock_data(symbol)
        if data is None:
            continue

        data = calculate_indicators(data)
        signal, score = calculate_signal(data)

        current_price = data['Close'].iloc[-1]
        pnl_pct = ((current_price / avg_price) - 1) * 100

        # Check if signal changed to SELL
        prev_signal = last_signals.get(symbol, "HOLD")

        if signal == "SELL" and prev_signal != "SELL":
            # Signal just changed to SELL - send alert!
            message = (
                f"[SELL ALERT] {symbol}\n"
                f"Signal: SELL (Score: {score:.0f}%)\n"
                f"Price: ${current_price:.2f}\n"
                f"P&L: {pnl_pct:+.1f}%\n"
                f"Shares: {qty}"
            )
            send_sms(message, db)

        # Update last signal
        last_signals[symbol] = signal

        # Log status
        status = f"{symbol}: {signal} ({score:.0f}%) @ ${current_price:.2f} [{pnl_pct:+.1f}%]"
        if signal == "SELL":
            log(f"[!] {status}")
        else:
            log(f"    {status}")

        # Small delay between requests
        time.sleep(1)

def main():
    """Main monitoring loop"""
    log("=" * 50)
    log("PORTFOLIO MONITOR STARTED")
    log(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    log(f"Market hours only: {MARKET_HOURS_ONLY}")
    log("=" * 50)

    db = JournalDB()

    # Show SMS config status
    to_phone = db.get_setting('twilio_to')
    if to_phone:
        log(f"SMS alerts will be sent to: {to_phone}")
    else:
        log("SMS not configured - alerts will only show in console")

    log("")

    while True:
        try:
            if is_market_open():
                check_portfolio(db)
            else:
                log("Market closed - skipping check")

            log(f"Next check in {CHECK_INTERVAL_MINUTES} minutes...")
            log("-" * 40)
            time.sleep(CHECK_INTERVAL_MINUTES * 60)

        except KeyboardInterrupt:
            log("Monitor stopped by user")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    main()
