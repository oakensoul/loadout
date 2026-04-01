# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Rich console helpers and shared UI patterns."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()
err_console = Console(stderr=True)

T = TypeVar("T")

# Module-level verbosity flag, set by the CLI layer.
_verbose: bool = False


def set_verbose(verbose: bool) -> None:
    """Set the global verbosity flag."""
    global _verbose  # noqa: PLW0603
    _verbose = verbose


def is_verbose() -> bool:
    """Return the current verbosity setting."""
    return _verbose


def status_line(icon: str, label: str, detail: str) -> None:
    """Print a formatted status line: icon  label  detail."""
    console.print(f"{icon}  {label}  {detail}")


def verbose_line(message: str) -> None:
    """Print a message only when verbose mode is enabled."""
    if _verbose:
        err_console.print(f"[dim]{message}[/dim]")


def section_header(title: str) -> None:
    """Print a visual section header using a Rich Rule."""
    console.print(Rule(title))


def error_panel(title: str, body: str) -> None:
    """Display a Rich error panel on stderr."""
    err_console.print(Panel(body, title=title, border_style="red"))


def run_step(description: str, fn: Callable[[], T], *, interactive: bool = False) -> T:
    """Run *fn* with a Rich spinner, show result icon, and return the value.

    Args:
        description: Human-readable label for this step.
        fn: Zero-argument callable to execute.
        interactive: If True, skip the spinner so subprocess prompts
            (sudo password, 1Password approval) are visible to the user.

    Displays a checkmark on success or an X on failure.
    Re-raises exceptions after displaying the error.
    """
    if interactive:
        console.print(f"[dim]▶[/dim]  {description}…")
        try:
            result = fn()
            console.print(f"[green]✓[/green]  {description}")
            return result
        except Exception:
            console.print(f"[red]✗[/red]  {description}")
            raise

    try:
        with console.status(f"  {description}…"):
            result = fn()
        console.print(f"[green]✓[/green]  {description}")
        return result
    except Exception:
        console.print(f"[red]✗[/red]  {description}")
        raise
