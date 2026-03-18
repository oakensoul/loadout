"""Rich console helpers and shared UI patterns."""

from __future__ import annotations

from typing import TypeVar

from collections.abc import Callable

from rich.console import Console
from rich.rule import Rule

console = Console()

T = TypeVar("T")


def status_line(icon: str, label: str, detail: str) -> None:
    """Print a formatted status line: icon  label  detail."""
    console.print(f"{icon}  {label}  {detail}")


def section_header(title: str) -> None:
    """Print a visual section header using a Rich Rule."""
    console.print(Rule(title))


def run_step(description: str, fn: Callable[[], T]) -> T:
    """Run *fn* with a Rich spinner, show result icon, and return the value.

    Displays a checkmark on success or an X on failure.
    Re-raises exceptions after displaying the error.
    """
    try:
        with console.status(f"  {description}…"):
            result = fn()
        console.print(f"[green]✓[/green]  {description}")
        return result
    except BaseException as exc:
        console.print(f"[red]✗[/red]  {description}")
        raise exc
