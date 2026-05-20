"""
Alert Monitor - Price and indicator alerts
"""
import json
import time
import threading
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import subprocess
import sys

from config import BASE_DIR
from data.fetcher import DataFetcher
from analysis.indicators import TechnicalAnalysis


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    MACD_CROSS_UP = "macd_cross_up"
    MACD_CROSS_DOWN = "macd_cross_down"


@dataclass
class Alert:
    """Represents an alert"""
    id: str
    symbol: str
    market: str
    alert_type: AlertType
    value: float
    message: str = ""
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "market": self.market,
            "alert_type": self.alert_type.value,
            "value": self.value,
            "message": self.message,
            "triggered": self.triggered,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        alert = cls(
            id=data["id"],
            symbol=data["symbol"],
            market=data["market"],
            alert_type=AlertType(data["alert_type"]),
            value=data["value"],
            message=data.get("message", ""),
            triggered=data.get("triggered", False),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        if data.get("triggered_at"):
            alert.triggered_at = datetime.fromisoformat(data["triggered_at"])
        return alert


class AlertMonitor:
    """Monitor and trigger alerts"""

    ALERTS_FILE = BASE_DIR / "alerts.json"

    def __init__(self):
        self.fetcher = DataFetcher()
        self.alerts: list[Alert] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._load_alerts()

    def _load_alerts(self):
        """Load alerts from file"""
        if self.ALERTS_FILE.exists():
            try:
                with open(self.ALERTS_FILE) as f:
                    data = json.load(f)
                    self.alerts = [Alert.from_dict(a) for a in data]
            except Exception:
                self.alerts = []

    def _save_alerts(self):
        """Save alerts to file"""
        with open(self.ALERTS_FILE, "w") as f:
            json.dump([a.to_dict() for a in self.alerts], f, indent=2)

    def add_alert(
        self,
        symbol: str,
        market: str,
        alert_type: AlertType,
        value: float,
        message: str = ""
    ) -> Alert:
        """Add a new alert"""
        alert_id = f"{symbol}_{alert_type.value}_{int(time.time())}"

        alert = Alert(
            id=alert_id,
            symbol=symbol,
            market=market,
            alert_type=alert_type,
            value=value,
            message=message
        )

        self.alerts.append(alert)
        self._save_alerts()
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID"""
        for i, alert in enumerate(self.alerts):
            if alert.id == alert_id:
                self.alerts.pop(i)
                self._save_alerts()
                return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        """Get all non-triggered alerts"""
        return [a for a in self.alerts if not a.triggered]

    def get_triggered_alerts(self) -> list[Alert]:
        """Get all triggered alerts"""
        return [a for a in self.alerts if a.triggered]

    def clear_triggered(self):
        """Remove all triggered alerts"""
        self.alerts = [a for a in self.alerts if not a.triggered]
        self._save_alerts()

    def add_callback(self, callback: Callable[[Alert], None]):
        """Add callback function called when alert triggers"""
        self._callbacks.append(callback)

    def check_alerts(self) -> list[Alert]:
        """Check all alerts and return newly triggered ones"""
        triggered = []

        for alert in self.alerts:
            if alert.triggered:
                continue

            if self._check_alert(alert):
                alert.triggered = True
                alert.triggered_at = datetime.now()
                triggered.append(alert)

                # Call callbacks
                for callback in self._callbacks:
                    try:
                        callback(alert)
                    except Exception:
                        pass

        if triggered:
            self._save_alerts()

        return triggered

    def _check_alert(self, alert: Alert) -> bool:
        """Check if a single alert should trigger"""
        try:
            if alert.alert_type in [AlertType.PRICE_ABOVE, AlertType.PRICE_BELOW]:
                price = self.fetcher.get_price(alert.symbol, alert.market)
                if price is None:
                    return False

                if alert.alert_type == AlertType.PRICE_ABOVE:
                    return price >= alert.value
                else:
                    return price <= alert.value

            elif alert.alert_type in [AlertType.RSI_ABOVE, AlertType.RSI_BELOW]:
                data = self.fetcher.get_historical(
                    alert.symbol, alert.market, period="1mo", interval="1d"
                )
                if data is None or data.empty:
                    return False

                ta = TechnicalAnalysis(data)
                ta.add_rsi()
                rsi = ta.data["rsi"].iloc[-1]

                if alert.alert_type == AlertType.RSI_ABOVE:
                    return rsi >= alert.value
                else:
                    return rsi <= alert.value

            # MACD cross alerts would need more complex logic
            # For now, just return False
            return False

        except Exception:
            return False

    def start_monitoring(self, interval: int = 60):
        """Start background monitoring thread"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()

    def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self, interval: int):
        """Background monitoring loop"""
        while self._running:
            triggered = self.check_alerts()

            for alert in triggered:
                self._notify(alert)

            time.sleep(interval)

    def _notify(self, alert: Alert):
        """Send notification for triggered alert"""
        message = (
            alert.message or
            f"{alert.symbol}: {alert.alert_type.value} {alert.value}"
        )

        # Try to send desktop notification
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{message}" with title "Trading Alert"'
                ], check=False)
            elif sys.platform == "linux":
                subprocess.run([
                    "notify-send", "Trading Alert", message
                ], check=False)
        except Exception:
            pass

        # Also print to console
        print(f"\n[ALERT] {message}")
