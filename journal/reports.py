"""
Report Generator - Create trading reports
"""
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .database import JournalDB
from .trades import TradeJournal


class ReportGenerator:
    """Generate trading reports"""

    def __init__(self):
        self.journal = TradeJournal()
        self.console = Console()

    def daily_report(self, date: str = None):
        """Generate daily trading report"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        start = datetime.fromisoformat(date)
        end = start + timedelta(days=1)

        trades = self.journal.get_trades_by_date(start, end)

        self.console.print(Panel(
            f"[bold]Daglig Rapport - {date}[/bold]",
            box=box.DOUBLE
        ))

        if not trades:
            self.console.print("[yellow]Ingen handler denne dag[/yellow]")
            return

        # Trades table
        table = Table(title="Handler", box=box.SIMPLE)
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Antal")
        table.add_column("Pris")
        table.add_column("P&L")

        total_pnl = 0
        for trade in trades:
            pnl = trade.get("pnl") or 0
            total_pnl += pnl
            pnl_str = f"${pnl:,.2f}" if pnl else "-"
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"

            table.add_row(
                trade["symbol"],
                trade["side"].upper(),
                f"{trade['quantity']:.2f}",
                f"${trade['price']:,.2f}",
                f"[{pnl_color}]{pnl_str}[/{pnl_color}]"
            )

        self.console.print(table)

        # Summary
        self.console.print(f"\n[bold]Opsummering:[/bold]")
        self.console.print(f"  Handler: {len(trades)}")
        pnl_color = "green" if total_pnl > 0 else "red"
        self.console.print(
            f"  Total P&L: [{pnl_color}]${total_pnl:,.2f}[/{pnl_color}]"
        )

    def weekly_report(self):
        """Generate weekly trading report"""
        end = datetime.now()
        start = end - timedelta(days=7)

        trades = self.journal.get_trades_by_date(start, end)

        self.console.print(Panel(
            f"[bold]Ugentlig Rapport[/bold]\n"
            f"{start.strftime('%d/%m')} - {end.strftime('%d/%m/%Y')}",
            box=box.DOUBLE
        ))

        if not trades:
            self.console.print("[yellow]Ingen handler denne uge[/yellow]")
            return

        # Group by day
        by_day = {}
        for trade in trades:
            day = trade["timestamp"][:10]
            if day not in by_day:
                by_day[day] = {"trades": 0, "pnl": 0}
            by_day[day]["trades"] += 1
            by_day[day]["pnl"] += trade.get("pnl") or 0

        # Daily breakdown
        table = Table(title="Daglig Oversigt", box=box.SIMPLE)
        table.add_column("Dato")
        table.add_column("Handler")
        table.add_column("P&L")

        total_pnl = 0
        for day, data in sorted(by_day.items()):
            pnl = data["pnl"]
            total_pnl += pnl
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"

            table.add_row(
                day,
                str(data["trades"]),
                f"[{pnl_color}]${pnl:,.2f}[/{pnl_color}]"
            )

        self.console.print(table)

        # Summary
        winning = len([t for t in trades if (t.get("pnl") or 0) > 0])
        win_rate = (winning / len(trades) * 100) if trades else 0

        self.console.print(f"\n[bold]Opsummering:[/bold]")
        self.console.print(f"  Total handler: {len(trades)}")
        self.console.print(f"  Win rate: {win_rate:.1f}%")
        pnl_color = "green" if total_pnl > 0 else "red"
        self.console.print(
            f"  Total P&L: [{pnl_color}]${total_pnl:,.2f}[/{pnl_color}]"
        )

    def performance_report(self):
        """Generate overall performance report"""
        perf = self.journal.get_performance_summary()

        self.console.print(Panel(
            "[bold]Performance Rapport[/bold]",
            box=box.DOUBLE
        ))

        # Stats
        table = Table(box=box.SIMPLE)
        table.add_column("Metric")
        table.add_column("Værdi")

        table.add_row("Total handler", str(perf["total_trades"]))
        table.add_row("Køb", str(perf["buy_trades"]))
        table.add_row("Salg", str(perf["sell_trades"]))
        table.add_row("Vindende handler", str(perf["winning_trades"]))
        table.add_row("Tabende handler", str(perf["losing_trades"]))
        table.add_row("Win rate", f"{perf['win_rate']:.1f}%")

        pnl_color = "green" if perf["total_pnl"] > 0 else "red"
        table.add_row(
            "Total P&L",
            f"[{pnl_color}]${perf['total_pnl']:,.2f}[/{pnl_color}]"
        )
        table.add_row("Gennemsnit P&L", f"${perf['avg_pnl']:,.2f}")
        table.add_row(
            "Bedste handel",
            f"[green]${perf['best_trade_pnl']:,.2f}[/green]"
        )
        table.add_row(
            "Værste handel",
            f"[red]${perf['worst_trade_pnl']:,.2f}[/red]"
        )

        self.console.print(table)

    def strategy_report(self):
        """Generate strategy performance report"""
        strategies = self.journal.get_strategy_performance()

        self.console.print(Panel(
            "[bold]Strategi Rapport[/bold]",
            box=box.DOUBLE
        ))

        if not strategies:
            self.console.print("[yellow]Ingen strategier registreret[/yellow]")
            return

        table = Table(box=box.SIMPLE)
        table.add_column("Strategi")
        table.add_column("Handler")
        table.add_column("Win Rate")
        table.add_column("Total P&L")
        table.add_column("Gns. P&L")

        for name, data in strategies.items():
            pnl_color = "green" if data["total_pnl"] > 0 else "red"
            table.add_row(
                name,
                str(data["trades"]),
                f"{data['win_rate']:.1f}%",
                f"[{pnl_color}]${data['total_pnl']:,.2f}[/{pnl_color}]",
                f"${data['avg_pnl']:,.2f}"
            )

        self.console.print(table)
