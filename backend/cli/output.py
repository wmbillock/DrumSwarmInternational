"""Shared formatting for CLI output — tables, JSON, color."""

import json
import sys

# Try rich for fancy output, fall back to plain text
try:
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_json(data: dict | list) -> None:
    """Pretty-print JSON data."""
    if HAS_RICH:
        console.print_json(json.dumps(data, default=str))
    else:
        print(json.dumps(data, indent=2, default=str))


def print_table(headers: list[str], rows: list[list[str]], title: str | None = None) -> None:
    """Print a formatted table."""
    if HAS_RICH:
        table = Table(title=title)
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*[str(c) for c in row])
        console.print(table)
    else:
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        if headers:
            print("  ".join(f"{h:<15}" for h in headers))
            print("  ".join("-" * 15 for _ in headers))
        for row in rows:
            print("  ".join(f"{str(c):<15}" for c in row))
        print()


def print_success(msg: str) -> None:
    if HAS_RICH:
        console.print(f"[green]{msg}[/green]")
    else:
        print(f"OK: {msg}")


def print_error(msg: str) -> None:
    if HAS_RICH:
        console.print(f"[red]Error: {msg}[/red]")
    else:
        print(f"Error: {msg}", file=sys.stderr)


def print_info(msg: str) -> None:
    if HAS_RICH:
        console.print(f"[blue]{msg}[/blue]")
    else:
        print(msg)
