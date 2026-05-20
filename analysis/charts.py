"""
Terminal-based charts using plotext
"""
import plotext as plt
import pandas as pd
from typing import Optional


class TerminalChart:
    """Create charts in the terminal"""

    def __init__(self, width: int = 80, height: int = 25):
        self.width = width
        self.height = height

    def candlestick(
        self,
        data: pd.DataFrame,
        title: str = "Price Chart",
        show_volume: bool = True
    ):
        """
        Draw a candlestick-style chart

        Note: plotext doesn't support true candlesticks,
        so we use a line chart with high/low range
        """
        plt.clear_figure()
        plt.plotsize(self.width, self.height)

        dates = list(range(len(data)))

        # Plot close price as main line
        plt.plot(dates, data["close"].tolist(), label="Close")

        # Plot high and low as area
        plt.plot(dates, data["high"].tolist(), label="High", color="green")
        plt.plot(dates, data["low"].tolist(), label="Low", color="red")

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")

        plt.show()

    def line(
        self,
        data: pd.DataFrame,
        columns: list[str] = None,
        title: str = "Chart"
    ):
        """Draw a simple line chart"""
        plt.clear_figure()
        plt.plotsize(self.width, self.height)

        columns = columns or ["close"]
        dates = list(range(len(data)))

        for col in columns:
            if col in data.columns:
                plt.plot(dates, data[col].tolist(), label=col)

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Value")

        plt.show()

    def price_with_indicators(
        self,
        data: pd.DataFrame,
        indicators: list[str] = None,
        title: str = "Price & Indicators"
    ):
        """Draw price chart with technical indicators"""
        plt.clear_figure()
        plt.plotsize(self.width, self.height)

        dates = list(range(len(data)))

        # Always plot close price
        plt.plot(dates, data["close"].tolist(), label="Price")

        # Plot requested indicators
        indicators = indicators or ["sma_20", "sma_50"]
        colors = ["blue", "magenta", "cyan", "yellow"]

        for i, ind in enumerate(indicators):
            if ind in data.columns:
                values = data[ind].dropna().tolist()
                ind_dates = dates[-len(values):]
                plt.plot(
                    ind_dates,
                    values,
                    label=ind.upper(),
                    color=colors[i % len(colors)]
                )

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")

        plt.show()

    def rsi(self, data: pd.DataFrame, title: str = "RSI"):
        """Draw RSI indicator"""
        if "rsi" not in data.columns:
            print("RSI not calculated. Run add_rsi() first.")
            return

        plt.clear_figure()
        plt.plotsize(self.width, self.height // 2)

        dates = list(range(len(data)))
        rsi_values = data["rsi"].dropna().tolist()
        rsi_dates = dates[-len(rsi_values):]

        plt.plot(rsi_dates, rsi_values, label="RSI")

        # Add overbought/oversold lines
        plt.hline(70, color="red")
        plt.hline(30, color="green")

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("RSI")
        plt.ylim(0, 100)

        plt.show()

    def macd(self, data: pd.DataFrame, title: str = "MACD"):
        """Draw MACD indicator"""
        macd_col = "MACD_12_26_9"
        signal_col = "MACDs_12_26_9"
        hist_col = "MACDh_12_26_9"

        if macd_col not in data.columns:
            print("MACD not calculated. Run add_macd() first.")
            return

        plt.clear_figure()
        plt.plotsize(self.width, self.height // 2)

        dates = list(range(len(data)))
        macd_values = data[macd_col].dropna().tolist()
        signal_values = data[signal_col].dropna().tolist()
        macd_dates = dates[-len(macd_values):]

        plt.plot(macd_dates, macd_values, label="MACD")
        plt.plot(macd_dates[-len(signal_values):], signal_values, label="Signal")

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("MACD")
        plt.hline(0, color="gray")

        plt.show()

    def volume(self, data: pd.DataFrame, title: str = "Volume"):
        """Draw volume chart"""
        plt.clear_figure()
        plt.plotsize(self.width, self.height // 2)

        dates = list(range(len(data)))
        plt.bar(dates, data["volume"].tolist())

        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Volume")

        plt.show()

    def multi_panel(
        self,
        data: pd.DataFrame,
        title: str = "Analysis"
    ):
        """Draw multi-panel chart with price, RSI, and MACD"""
        # Price chart
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

        self.price_with_indicators(data, title="Price")

        if "rsi" in data.columns:
            print()
            self.rsi(data)

        if "MACD_12_26_9" in data.columns:
            print()
            self.macd(data)
