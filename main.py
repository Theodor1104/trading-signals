#!/usr/bin/env python3
"""
Trading Platform - Main Entry Point
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, FloatPrompt, IntPrompt
from rich import box

from config import (
    TradingMode, POPULAR_STOCKS, POPULAR_CRYPTO, POPULAR_FOREX
)
from data.fetcher import DataFetcher
from analysis.indicators import TechnicalAnalysis
from analysis.charts import TerminalChart
from analysis.scanner import MarketScanner
from trading.engine import TradingEngine
from trading.orders import OrderStatus
from journal.trades import TradeJournal
from journal.reports import ReportGenerator
from backtest.engine import Backtester
from backtest.strategies import AVAILABLE_STRATEGIES, SMAStrategy, RSIStrategy
from alerts.monitor import AlertMonitor, AlertType


console = Console()


class TradingApp:
    """Main trading application"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.engine = TradingEngine()
        self.scanner = MarketScanner()
        self.journal = TradeJournal()
        self.reports = ReportGenerator()
        self.backtester = Backtester()
        self.alerts = AlertMonitor()
        self.chart = TerminalChart()

    def run(self):
        """Main application loop"""
        self._show_welcome()

        while True:
            try:
                choice = self._main_menu()

                if choice == "1":
                    self._market_data_menu()
                elif choice == "2":
                    self._analysis_menu()
                elif choice == "3":
                    self._trading_menu()
                elif choice == "4":
                    self._backtest_menu()
                elif choice == "5":
                    self._journal_menu()
                elif choice == "6":
                    self._alerts_menu()
                elif choice == "7":
                    self._settings_menu()
                elif choice == "0" or choice.lower() == "q":
                    if Confirm.ask("Er du sikker på du vil afslutte?"):
                        console.print("[green]Farvel![/green]")
                        break
                else:
                    console.print("[red]Ugyldigt valg[/red]")

            except KeyboardInterrupt:
                console.print("\n[yellow]Afbrudt[/yellow]")
            except Exception as e:
                console.print(f"[red]Fejl: {e}[/red]")

    def _show_welcome(self):
        """Show welcome screen"""
        mode_text = "PAPER" if self.engine.is_paper else "LIVE"
        mode_color = "yellow" if self.engine.is_paper else "red"

        console.print(Panel(
            f"""
[bold cyan]Trading Platform[/bold cyan]

Mode: [{mode_color}]{mode_text}[/{mode_color}]
Balance: ${self.engine.get_balance():,.2f}

[dim]Brug menuen nedenfor til at navigere[/dim]
            """,
            title="Velkommen",
            box=box.DOUBLE
        ))

    def _main_menu(self) -> str:
        """Display main menu"""
        console.print("\n[bold]Hovedmenu[/bold]")
        console.print("1. Markedsdata")
        console.print("2. Teknisk analyse")
        console.print("3. Trading")
        console.print("4. Backtesting")
        console.print("5. Journal & Rapporter")
        console.print("6. Alerts")
        console.print("7. Indstillinger")
        console.print("0. Afslut")

        return Prompt.ask("\nVælg", default="1")

    # =====================
    # MARKET DATA
    # =====================
    def _market_data_menu(self):
        """Market data submenu"""
        while True:
            console.print("\n[bold]Markedsdata[/bold]")
            console.print("1. Hent pris")
            console.print("2. Populære aktier")
            console.print("3. Populære crypto")
            console.print("4. Populær forex")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self._get_price()
            elif choice == "2":
                self._show_prices(POPULAR_STOCKS, "stocks", "Populære Aktier")
            elif choice == "3":
                self._show_prices(POPULAR_CRYPTO, "crypto", "Populære Crypto")
            elif choice == "4":
                self._show_prices(POPULAR_FOREX, "forex", "Populær Forex")
            elif choice == "0":
                break

    def _get_price(self):
        """Get price for a specific symbol"""
        symbol = Prompt.ask("Symbol (f.eks. AAPL, BTC/USDT)")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        price = self.fetcher.get_price(symbol, market)
        if price:
            console.print(f"\n[green]{symbol}: ${price:,.4f}[/green]")
        else:
            console.print(f"[red]Kunne ikke finde {symbol}[/red]")

    def _show_prices(self, symbols: list, market: str, title: str):
        """Show prices for multiple symbols"""
        table = Table(title=title, box=box.SIMPLE)
        table.add_column("Symbol")
        table.add_column("Pris", justify="right")

        for symbol in symbols:
            price = self.fetcher.get_price(symbol, market)
            if price:
                table.add_row(symbol, f"${price:,.4f}")
            else:
                table.add_row(symbol, "[dim]N/A[/dim]")

        console.print(table)

    # =====================
    # ANALYSIS
    # =====================
    def _analysis_menu(self):
        """Technical analysis submenu"""
        while True:
            console.print("\n[bold]Teknisk Analyse[/bold]")
            console.print("1. Analyser symbol")
            console.print("2. Scan for signaler")
            console.print("3. Find oversold")
            console.print("4. Find overbought")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self._analyze_symbol()
            elif choice == "2":
                self._scan_signals()
            elif choice == "3":
                self._scan_oversold()
            elif choice == "4":
                self._scan_overbought()
            elif choice == "0":
                break

    def _analyze_symbol(self):
        """Analyze a specific symbol"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")
        period = Prompt.ask("Periode", choices=["1mo", "3mo", "6mo", "1y"], default="3mo")

        console.print(f"\n[dim]Henter data for {symbol}...[/dim]")

        data = self.fetcher.get_historical(symbol, market, period=period)
        if data is None or data.empty:
            console.print(f"[red]Kunne ikke finde data for {symbol}[/red]")
            return

        # Calculate indicators
        ta = TechnicalAnalysis(data)
        ta.add_all_indicators()

        # Show current values
        values = ta.get_current_values()
        signal = ta.generate_signal()

        console.print(Panel(f"[bold]{symbol}[/bold] - {market.upper()}", box=box.DOUBLE))

        table = Table(box=box.SIMPLE)
        table.add_column("Indikator")
        table.add_column("Værdi", justify="right")

        table.add_row("Pris", f"${values.get('price', 0):,.4f}")
        table.add_row("RSI", f"{values.get('rsi', 0):.1f}")
        table.add_row("MACD", f"{values.get('macd', 0):.4f}")
        table.add_row("SMA 20", f"${values.get('sma_20', 0):,.4f}")
        table.add_row("SMA 50", f"${values.get('sma_50', 0):,.4f}")
        table.add_row("SMA 200", f"${values.get('sma_200', 0):,.4f}")

        console.print(table)

        # Show signal
        signal_color = "green" if signal.type == "BUY" else "red" if signal.type == "SELL" else "yellow"
        console.print(f"\n[{signal_color}]Signal: {signal.type} ({signal.strength:.0f}%)[/{signal_color}]")
        console.print(f"[dim]{signal.reason}[/dim]")

        # Show chart
        if Confirm.ask("\nVis chart?", default=True):
            self.chart.multi_panel(ta.data, title=symbol)

    def _scan_signals(self):
        """Scan for buy/sell signals"""
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        symbols = {
            "stocks": POPULAR_STOCKS,
            "crypto": POPULAR_CRYPTO,
            "forex": POPULAR_FOREX
        }[market]

        console.print(f"\n[dim]Scanner {len(symbols)} symboler...[/dim]")

        results = self.scanner.scan_for_signals(symbols, market)

        table = Table(title="Signaler", box=box.SIMPLE)
        table.add_column("Symbol")
        table.add_column("Pris", justify="right")
        table.add_column("Signal")
        table.add_column("Styrke")
        table.add_column("Trend")

        for r in results[:10]:
            signal_color = "green" if r.signal.type == "BUY" else "red" if r.signal.type == "SELL" else "yellow"
            trend_color = "green" if r.trend == "UP" else "red" if r.trend == "DOWN" else "yellow"

            table.add_row(
                r.symbol,
                f"${r.price:,.4f}" if r.price else "N/A",
                f"[{signal_color}]{r.signal.type}[/{signal_color}]",
                f"{r.signal.strength:.0f}%",
                f"[{trend_color}]{r.trend}[/{trend_color}]"
            )

        console.print(table)

    def _scan_oversold(self):
        """Find oversold symbols"""
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        symbols = {
            "stocks": POPULAR_STOCKS,
            "crypto": POPULAR_CRYPTO,
            "forex": POPULAR_FOREX
        }[market]

        console.print(f"\n[dim]Scanner for oversold...[/dim]")

        results = self.scanner.scan_oversold(symbols, market)

        if not results:
            console.print("[yellow]Ingen oversold symboler fundet[/yellow]")
            return

        table = Table(title="Oversold (RSI < 30)", box=box.SIMPLE)
        table.add_column("Symbol")
        table.add_column("Pris", justify="right")
        table.add_column("RSI", justify="right")

        for r in results:
            table.add_row(
                r.symbol,
                f"${r.price:,.4f}" if r.price else "N/A",
                f"[green]{r.rsi:.1f}[/green]"
            )

        console.print(table)

    def _scan_overbought(self):
        """Find overbought symbols"""
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        symbols = {
            "stocks": POPULAR_STOCKS,
            "crypto": POPULAR_CRYPTO,
            "forex": POPULAR_FOREX
        }[market]

        console.print(f"\n[dim]Scanner for overbought...[/dim]")

        results = self.scanner.scan_overbought(symbols, market)

        if not results:
            console.print("[yellow]Ingen overbought symboler fundet[/yellow]")
            return

        table = Table(title="Overbought (RSI > 70)", box=box.SIMPLE)
        table.add_column("Symbol")
        table.add_column("Pris", justify="right")
        table.add_column("RSI", justify="right")

        for r in results:
            table.add_row(
                r.symbol,
                f"${r.price:,.4f}" if r.price else "N/A",
                f"[red]{r.rsi:.1f}[/red]"
            )

        console.print(table)

    # =====================
    # TRADING
    # =====================
    def _trading_menu(self):
        """Trading submenu"""
        while True:
            mode_text = "PAPER" if self.engine.is_paper else "LIVE"
            mode_color = "yellow" if self.engine.is_paper else "red"

            console.print(f"\n[bold]Trading[/bold] [{mode_color}]{mode_text}[/{mode_color}]")
            console.print("1. Køb")
            console.print("2. Sælg")
            console.print("3. Portfolio oversigt")
            console.print("4. Ordre historik")
            console.print("5. Nulstil konto (paper)")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self._buy()
            elif choice == "2":
                self._sell()
            elif choice == "3":
                self._show_portfolio()
            elif choice == "4":
                self._show_orders()
            elif choice == "5":
                self._reset_account()
            elif choice == "0":
                break

    def _buy(self):
        """Place a buy order"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        # Show current price
        price = self.fetcher.get_price(symbol, market)
        if price:
            console.print(f"Aktuel pris: ${price:,.4f}")
        else:
            console.print("[red]Kunne ikke finde prisen[/red]")
            return

        quantity = FloatPrompt.ask("Antal")
        notes = Prompt.ask("Noter (valgfrit)", default="")

        total = price * quantity
        console.print(f"\nTotal: ${total:,.2f}")

        if not Confirm.ask("Bekræft køb?"):
            return

        order = self.engine.buy(symbol, quantity, market, notes=notes)

        if order.status == OrderStatus.FILLED:
            console.print(f"[green]Køb gennemført! Pris: ${order.filled_price:,.4f}[/green]")
            self.journal.log_trade(order, notes=notes)
        else:
            console.print(f"[red]Ordre afvist: {order.status.value}[/red]")

    def _sell(self):
        """Place a sell order"""
        positions = self.engine.get_positions()

        if not positions:
            console.print("[yellow]Ingen positioner at sælge[/yellow]")
            return

        # Show positions
        console.print("\n[bold]Dine positioner:[/bold]")
        for symbol, pos in positions.items():
            console.print(f"  {symbol}: {pos.quantity:.4f} @ ${pos.avg_price:,.4f}")

        symbol = Prompt.ask("Symbol at sælge")

        if symbol not in positions:
            console.print(f"[red]Du har ikke {symbol}[/red]")
            return

        pos = positions[symbol]
        quantity = FloatPrompt.ask(f"Antal (max {pos.quantity:.4f})", default=pos.quantity)
        notes = Prompt.ask("Noter (valgfrit)", default="")

        if not Confirm.ask("Bekræft salg?"):
            return

        order = self.engine.sell(symbol, quantity, pos.market, notes=notes)

        if order.status == OrderStatus.FILLED:
            pnl = (order.filled_price - pos.avg_price) * quantity
            pnl_color = "green" if pnl > 0 else "red"
            console.print(f"[green]Salg gennemført! Pris: ${order.filled_price:,.4f}[/green]")
            console.print(f"P&L: [{pnl_color}]${pnl:,.2f}[/{pnl_color}]")
            self.journal.log_trade(order, notes=notes)
        else:
            console.print(f"[red]Ordre afvist: {order.status.value}[/red]")

    def _show_portfolio(self):
        """Show portfolio overview"""
        pnl_data = self.engine.get_pnl()

        console.print(Panel("[bold]Portfolio Oversigt[/bold]", box=box.DOUBLE))

        # Summary
        total_pnl = pnl_data["total_pnl"]
        pnl_color = "green" if total_pnl > 0 else "red"

        console.print(f"Portfolio værdi: ${pnl_data['portfolio_value']:,.2f}")
        console.print(f"Kontant: ${pnl_data['cash']:,.2f}")
        console.print(f"Total P&L: [{pnl_color}]${total_pnl:,.2f} ({pnl_data['total_pnl_percent']:.2f}%)[/{pnl_color}]")

        # Positions
        if pnl_data["positions"]:
            table = Table(title="Positioner", box=box.SIMPLE)
            table.add_column("Symbol")
            table.add_column("Antal", justify="right")
            table.add_column("Gns. pris", justify="right")
            table.add_column("Aktuel pris", justify="right")
            table.add_column("P&L", justify="right")

            for symbol, pos_pnl in pnl_data["positions"].items():
                pnl = pos_pnl["pnl"]
                pnl_color = "green" if pnl > 0 else "red"

                table.add_row(
                    symbol,
                    f"{pos_pnl['quantity']:.4f}",
                    f"${pos_pnl['avg_price']:,.4f}",
                    f"${pos_pnl['current_price']:,.4f}",
                    f"[{pnl_color}]${pnl:,.2f} ({pos_pnl['pnl_percent']:.2f}%)[/{pnl_color}]"
                )

            console.print(table)

    def _show_orders(self):
        """Show order history"""
        orders = self.engine.get_orders()

        if not orders:
            console.print("[yellow]Ingen ordrer endnu[/yellow]")
            return

        table = Table(title="Ordre Historik", box=box.SIMPLE)
        table.add_column("ID")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Antal")
        table.add_column("Pris")
        table.add_column("Status")
        table.add_column("Dato")

        for order in orders[-20:]:  # Last 20
            side_color = "green" if order.side.value == "buy" else "red"
            table.add_row(
                order.order_id,
                order.symbol,
                f"[{side_color}]{order.side.value.upper()}[/{side_color}]",
                f"{order.quantity:.4f}",
                f"${order.filled_price:,.4f}" if order.filled_price else "-",
                order.status.value,
                order.created_at.strftime("%d/%m %H:%M")
            )

        console.print(table)

    def _reset_account(self):
        """Reset paper trading account"""
        if not self.engine.is_paper:
            console.print("[red]Kan kun nulstille paper konto![/red]")
            return

        if not Confirm.ask("Er du sikker? Dette sletter alle positioner og nulstiller balancen"):
            return

        balance = FloatPrompt.ask("Ny startbalance", default=100000.0)
        self.engine.reset(balance)
        console.print(f"[green]Konto nulstillet med ${balance:,.2f}[/green]")

    # =====================
    # BACKTESTING
    # =====================
    def _backtest_menu(self):
        """Backtesting submenu"""
        while True:
            console.print("\n[bold]Backtesting[/bold]")
            console.print("1. Kør backtest")
            console.print("2. Sammenlign strategier")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self._run_backtest()
            elif choice == "2":
                self._compare_strategies()
            elif choice == "0":
                break

    def _run_backtest(self):
        """Run a backtest"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")
        period = Prompt.ask("Periode", choices=["3mo", "6mo", "1y", "2y"], default="1y")

        console.print("\n[bold]Tilgængelige strategier:[/bold]")
        console.print("  sma      - SMA Crossover (20/50)")
        console.print("  rsi      - RSI Overbought/Oversold")
        console.print("  macd     - MACD Crossover")
        console.print("  bollinger - Bollinger Bands")

        strategy_name = Prompt.ask("Strategi", choices=list(AVAILABLE_STRATEGIES.keys()), default="sma")
        capital = FloatPrompt.ask("Startkapital", default=10000.0)

        strategy_class = AVAILABLE_STRATEGIES[strategy_name]
        strategy = strategy_class()

        console.print(f"\n[dim]Kører backtest på {symbol}...[/dim]")

        result = self.backtester.run(
            symbol, market, strategy,
            initial_capital=capital,
            period=period
        )

        if result is None:
            console.print("[red]Kunne ikke køre backtest[/red]")
            return

        # Show results
        m = result.metrics

        console.print(Panel(f"[bold]Backtest: {symbol} - {strategy.name}[/bold]", box=box.DOUBLE))

        table = Table(box=box.SIMPLE)
        table.add_column("Metric")
        table.add_column("Værdi", justify="right")

        pnl_color = "green" if m.total_return > 0 else "red"

        table.add_row("Periode", f"{result.start_date.strftime('%d/%m/%Y')} - {result.end_date.strftime('%d/%m/%Y')}")
        table.add_row("Startkapital", f"${capital:,.2f}")
        table.add_row("Slutværdi", f"${result.final_value:,.2f}")
        table.add_row("Total afkast", f"[{pnl_color}]${m.total_return:,.2f} ({m.total_return_pct:.2f}%)[/{pnl_color}]")
        table.add_row("Årligt afkast", f"{m.annualized_return:.2f}%")
        table.add_row("Sharpe Ratio", f"{m.sharpe_ratio:.2f}")
        table.add_row("Max Drawdown", f"[red]{m.max_drawdown_pct:.2f}%[/red]")
        table.add_row("Total handler", str(m.total_trades))
        table.add_row("Win rate", f"{m.win_rate:.1f}%")
        table.add_row("Profit factor", f"{m.profit_factor:.2f}")

        console.print(table)

    def _compare_strategies(self):
        """Compare multiple strategies"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        strategies = [
            SMAStrategy(20, 50),
            RSIStrategy(),
            AVAILABLE_STRATEGIES["macd"](),
            AVAILABLE_STRATEGIES["bollinger"]()
        ]

        console.print(f"\n[dim]Sammenligner {len(strategies)} strategier...[/dim]")

        results = self.backtester.compare_strategies(symbol, market, strategies)

        if not results:
            console.print("[red]Kunne ikke sammenligne strategier[/red]")
            return

        table = Table(title=f"Strategi Sammenligning - {symbol}", box=box.SIMPLE)
        table.add_column("Strategi")
        table.add_column("Afkast", justify="right")
        table.add_column("Sharpe", justify="right")
        table.add_column("Win Rate", justify="right")
        table.add_column("Max DD", justify="right")

        for r in results:
            m = r.metrics
            pnl_color = "green" if m.total_return_pct > 0 else "red"

            table.add_row(
                r.strategy_name,
                f"[{pnl_color}]{m.total_return_pct:.2f}%[/{pnl_color}]",
                f"{m.sharpe_ratio:.2f}",
                f"{m.win_rate:.1f}%",
                f"[red]{m.max_drawdown_pct:.2f}%[/red]"
            )

        console.print(table)

    # =====================
    # JOURNAL
    # =====================
    def _journal_menu(self):
        """Journal submenu"""
        while True:
            console.print("\n[bold]Journal & Rapporter[/bold]")
            console.print("1. Daglig rapport")
            console.print("2. Ugentlig rapport")
            console.print("3. Performance rapport")
            console.print("4. Seneste handler")
            console.print("5. Tilføj note")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self.reports.daily_report()
            elif choice == "2":
                self.reports.weekly_report()
            elif choice == "3":
                self.reports.performance_report()
            elif choice == "4":
                self._show_recent_trades()
            elif choice == "5":
                self._add_note()
            elif choice == "0":
                break

    def _show_recent_trades(self):
        """Show recent trades"""
        trades = self.journal.get_recent_trades(20)

        if not trades:
            console.print("[yellow]Ingen handler registreret[/yellow]")
            return

        table = Table(title="Seneste Handler", box=box.SIMPLE)
        table.add_column("Dato")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Antal")
        table.add_column("Pris")
        table.add_column("P&L")

        for t in trades:
            side_color = "green" if t["side"] == "buy" else "red"
            pnl = t.get("pnl") or 0
            pnl_str = f"${pnl:,.2f}" if pnl else "-"
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"

            table.add_row(
                t["timestamp"][:10],
                t["symbol"],
                f"[{side_color}]{t['side'].upper()}[/{side_color}]",
                f"{t['quantity']:.4f}",
                f"${t['price']:,.4f}",
                f"[{pnl_color}]{pnl_str}[/{pnl_color}]"
            )

        console.print(table)

    def _add_note(self):
        """Add a journal note"""
        note = Prompt.ask("Note")
        self.journal.add_note(note)
        console.print("[green]Note tilføjet[/green]")

    # =====================
    # ALERTS
    # =====================
    def _alerts_menu(self):
        """Alerts submenu"""
        while True:
            console.print("\n[bold]Alerts[/bold]")
            console.print("1. Opret pris alert")
            console.print("2. Opret RSI alert")
            console.print("3. Vis aktive alerts")
            console.print("4. Slet alert")
            console.print("5. Start overvågning")
            console.print("6. Stop overvågning")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self._create_price_alert()
            elif choice == "2":
                self._create_rsi_alert()
            elif choice == "3":
                self._show_alerts()
            elif choice == "4":
                self._delete_alert()
            elif choice == "5":
                self.alerts.start_monitoring()
                console.print("[green]Overvågning startet[/green]")
            elif choice == "6":
                self.alerts.stop_monitoring()
                console.print("[yellow]Overvågning stoppet[/yellow]")
            elif choice == "0":
                break

    def _create_price_alert(self):
        """Create a price alert"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        price = self.fetcher.get_price(symbol, market)
        if price:
            console.print(f"Aktuel pris: ${price:,.4f}")

        direction = Prompt.ask("Retning", choices=["above", "below"], default="above")
        target = FloatPrompt.ask("Målpris")
        message = Prompt.ask("Besked (valgfrit)", default="")

        alert_type = AlertType.PRICE_ABOVE if direction == "above" else AlertType.PRICE_BELOW

        alert = self.alerts.add_alert(symbol, market, alert_type, target, message)
        console.print(f"[green]Alert oprettet: {alert.id}[/green]")

    def _create_rsi_alert(self):
        """Create an RSI alert"""
        symbol = Prompt.ask("Symbol")
        market = Prompt.ask("Marked", choices=["stocks", "crypto", "forex"], default="stocks")

        direction = Prompt.ask("Retning", choices=["above", "below"], default="below")
        threshold = FloatPrompt.ask("RSI grænse", default=30.0 if direction == "below" else 70.0)
        message = Prompt.ask("Besked (valgfrit)", default="")

        alert_type = AlertType.RSI_ABOVE if direction == "above" else AlertType.RSI_BELOW

        alert = self.alerts.add_alert(symbol, market, alert_type, threshold, message)
        console.print(f"[green]Alert oprettet: {alert.id}[/green]")

    def _show_alerts(self):
        """Show active alerts"""
        active = self.alerts.get_active_alerts()

        if not active:
            console.print("[yellow]Ingen aktive alerts[/yellow]")
            return

        table = Table(title="Aktive Alerts", box=box.SIMPLE)
        table.add_column("ID")
        table.add_column("Symbol")
        table.add_column("Type")
        table.add_column("Værdi")
        table.add_column("Besked")

        for a in active:
            table.add_row(
                a.id[:12],
                a.symbol,
                a.alert_type.value,
                f"{a.value:,.2f}",
                a.message or "-"
            )

        console.print(table)

    def _delete_alert(self):
        """Delete an alert"""
        self._show_alerts()

        alert_id = Prompt.ask("Alert ID at slette")

        # Find matching alert
        for alert in self.alerts.alerts:
            if alert.id.startswith(alert_id):
                if self.alerts.remove_alert(alert.id):
                    console.print(f"[green]Alert slettet[/green]")
                    return

        console.print("[red]Alert ikke fundet[/red]")

    # =====================
    # SETTINGS
    # =====================
    def _settings_menu(self):
        """Settings submenu"""
        while True:
            mode_text = "PAPER" if self.engine.is_paper else "LIVE"

            console.print("\n[bold]Indstillinger[/bold]")
            console.print(f"Aktuel mode: {mode_text}")
            console.print("1. Skift til Paper mode")
            console.print("2. Skift til Live mode")
            console.print("3. Ryd cache")
            console.print("0. Tilbage")

            choice = Prompt.ask("Vælg", default="0")

            if choice == "1":
                self.engine.set_mode(TradingMode.PAPER)
                console.print("[green]Skiftet til PAPER mode[/green]")
            elif choice == "2":
                if Confirm.ask("[red]ADVARSEL: Live mode bruger rigtige penge! Fortsæt?[/red]"):
                    self.engine.set_mode(TradingMode.LIVE)
                    console.print("[red]Skiftet til LIVE mode[/red]")
            elif choice == "3":
                self.fetcher.clear_cache()
                console.print("[green]Cache ryddet[/green]")
            elif choice == "0":
                break


def main():
    """Entry point"""
    app = TradingApp()
    app.run()


if __name__ == "__main__":
    main()
