# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Click CLI entry point for loadout."""

from __future__ import annotations

import sys
from importlib.metadata import version

import click

from loadout.exceptions import LoadoutCommandError, LoadoutError
from loadout.ui import error_panel, is_verbose, set_verbose


def _get_version() -> str:
    """Return the installed package version."""
    try:
        return version("oakensoul-loadout")
    except Exception:  # noqa: BLE001
        return "0.0.0-dev"


@click.group()
@click.version_option(version=_get_version(), prog_name="loadout")
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show what would be done without executing."
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Increase output detail.")
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
        from rich.markup import escape

        body = escape(str(exc))
        if isinstance(exc, LoadoutCommandError) and exc.stderr:
            body += f"\n\n[dim]{escape(exc.stderr.rstrip())}[/dim]"
        if is_verbose():
            import traceback

            body += f"\n\n[dim]{escape(traceback.format_exc().rstrip())}[/dim]"
        error_panel("Loadout Error", body)
        sys.exit(1)
    except Exception as exc:
        from rich.markup import escape

        body = escape(str(exc))
        if is_verbose():
            import traceback

            body += f"\n\n[dim]{escape(traceback.format_exc().rstrip())}[/dim]"
        error_panel("Unexpected Error", body)
        sys.exit(1)


@cli.command()
@click.option("--user", required=True, help="GitHub username.")
@click.option("--orgs", required=True, multiple=True, help="Org names (repeat for multiple).")
@click.option("--git-name", required=True, help="Full name for git config.")
@click.option("--git-email", required=True, help="Email for git config.")
@click.option(
    "--template",
    default="https://github.com/oakensoul/dotfiles-private-cookiecutter",
    help="Cookiecutter template URL or local path.",
)
@click.option("--create-repo", is_flag=True, default=False, help="Create GitHub repo via gh CLI.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without making changes.")
@click.pass_context
def scaffold(
    ctx: click.Context,
    user: str,
    orgs: tuple[str, ...],
    git_name: str,
    git_email: str,
    template: str,
    create_repo: bool,
    dry_run: bool,
) -> None:
    """Scaffold a new dotfiles-private repository.

    Uses cookiecutter to generate a private dotfiles repo from a template.
    Run this BEFORE 'loadout init'.

    Example: loadout scaffold --user=oakensoul --orgs=personal \\
             --git-name="Jane Doe" --git-email="jane@example.com"
    """
    from loadout.core import run_scaffold

    effective_dry_run = ctx.obj["dry_run"] or dry_run
    run_scaffold(
        user,
        list(orgs),
        git_name,
        git_email,
        template=template,
        create_repo=create_repo,
        dry_run=effective_dry_run,
    )


@cli.command()
@click.option("--user", required=True, help="GitHub username (owner of dotfiles repos).")
@click.option("--orgs", required=True, multiple=True, help="Org names (repeat for multiple).")
@click.pass_context
def init(ctx: click.Context, user: str, orgs: tuple[str, ...]) -> None:
    """Bootstrap a new machine for the given user and orgs.

    Clones dotfile repos, generates SSH keys, builds dotfiles, runs
    Homebrew bundle, and installs global packages.

    Example: loadout init --user=oakensoul --orgs=personal --orgs=splash
    """
    from loadout.core import run_init

    run_init(user, list(orgs), dry_run=ctx.obj["dry_run"])


@cli.command()
@click.pass_context
def update(ctx: click.Context) -> None:
    """Pull latest dotfile sources and rebuild configuration.

    Runs git pull on dotfile repos, rebuilds merged dotfiles,
    runs brew bundle, and installs global packages. Safe and idempotent.
    """
    from loadout.core import run_update

    run_update(dry_run=ctx.obj["dry_run"])


@cli.command()
@click.pass_context
def upgrade(ctx: click.Context) -> None:
    """Run full update then upgrade Homebrew packages.

    Includes everything in 'update' plus 'brew upgrade'. Run intentionally
    — upgrades can break things.
    """
    from loadout.core import run_upgrade

    run_upgrade(dry_run=ctx.obj["dry_run"])


@cli.command()
def check() -> None:
    """Run health checks — read-only, never mutates.

    Checks Homebrew, Git, Node, Python, 1Password CLI, GitHub SSH,
    Claude Code, Brewfile fragments, globals scripts, and Claude config.
    """
    from loadout.core import check_health

    check_health()


@cli.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Merge base + org fragments into final dotfiles.

    Applies per-file merge strategies (concat, git include, deep-merge,
    replace) and installs the result to ~/. Idempotent.
    """
    from loadout.core import run_build

    run_build(dry_run=ctx.obj["dry_run"])


@cli.command("globals")
@click.pass_context
def globals_cmd(ctx: click.Context) -> None:
    """Install non-Homebrew global packages.

    Installs Claude Code, NVM + Node LTS, pyenv + Python, and any npm/pip
    globals defined in org config files.
    """
    from loadout.core import run_globals

    run_globals(dry_run=ctx.obj["dry_run"])


@cli.command()
@click.argument("mode", type=click.Choice(["connected", "solo"]), default=None, required=False)
@click.pass_context
def display(ctx: click.Context, mode: str | None) -> None:
    """Switch macOS display profile.

    Auto-detects connected displays when no mode is given. Use 'connected'
    or 'solo' to force a specific profile.
    """
    from loadout.core import run_display

    run_display(mode=mode, dry_run=ctx.obj["dry_run"])
