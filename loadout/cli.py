"""Click CLI entry point for loadout."""

from __future__ import annotations

import sys

import click

from loadout.exceptions import LoadoutError
from loadout.ui import error_panel, is_verbose, set_verbose


@click.group()
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show what would be done without executing."
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Increase output detail."
)
@click.pass_context
def cli(ctx: click.Context, dry_run: bool, verbose: bool) -> None:
    """Loadout — machine configuration management.

    Orchestrates dotfile building, Homebrew, global package installs,
    and health checks across multiple user/org contexts.
    """
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    set_verbose(verbose)


def main() -> None:
    """CLI entry point with top-level error handling."""
    try:
        cli(standalone_mode=False)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.", err=True)
        sys.exit(130)
    except click.exceptions.Exit as exc:
        sys.exit(exc.exit_code)
    except click.ClickException as exc:
        exc.show()
        sys.exit(exc.exit_code)
    except LoadoutError as exc:
        body = str(exc)
        from loadout.exceptions import LoadoutCommandError

        if isinstance(exc, LoadoutCommandError) and exc.stderr:
            body += f"\n\n[dim]{exc.stderr.rstrip()}[/dim]"
        if is_verbose():
            import traceback

            body += f"\n\n[dim]{traceback.format_exc().rstrip()}[/dim]"
        error_panel("Loadout Error", body)
        sys.exit(1)
    except Exception as exc:
        body = str(exc)
        if is_verbose():
            import traceback

            body += f"\n\n[dim]{traceback.format_exc().rstrip()}[/dim]"
        error_panel("Unexpected Error", body)
        sys.exit(1)


@cli.command()
@click.option("--user", required=True, help="GitHub username for dotfile config.")
@click.option("--orgs", required=True, multiple=True, help="Org names (repeat for multiple).")
@click.pass_context
def init(ctx: click.Context, user: str, orgs: tuple[str, ...]) -> None:
    """Initialize loadout for a user and set of orgs."""
    from loadout.core import run_init

    run_init(user, list(orgs), dry_run=ctx.obj["dry_run"])


@cli.command()
@click.pass_context
def update(ctx: click.Context) -> None:
    """Pull latest dotfile sources and rebuild configuration."""
    from loadout.core import run_update

    run_update(dry_run=ctx.obj["dry_run"])


@cli.command()
@click.pass_context
def upgrade(ctx: click.Context) -> None:
    """Run Homebrew upgrade and update global packages."""
    from loadout.core import run_upgrade

    run_upgrade(dry_run=ctx.obj["dry_run"])


@cli.command()
def check() -> None:
    """Run health checks — warn only, never mutates."""
    from loadout.core import check_health

    check_health()


@cli.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Merge base + org fragments into final dotfiles."""
    from loadout.core import run_build

    run_build(dry_run=ctx.obj["dry_run"])


@cli.command("globals")
@click.pass_context
def globals_cmd(ctx: click.Context) -> None:
    """Install non-Homebrew globals (Claude Code, npm, pip)."""
    from loadout.core import run_globals

    run_globals(dry_run=ctx.obj["dry_run"])


@cli.command()
@click.argument("mode", type=click.Choice(["connected", "solo"]), default=None, required=False)
@click.pass_context
def display(ctx: click.Context, mode: str | None) -> None:
    """Switch macOS display profile."""
    from loadout.core import run_display

    run_display(mode=mode, dry_run=ctx.obj["dry_run"])
