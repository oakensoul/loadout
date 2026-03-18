"""Click CLI entry point for loadout."""

import click


@click.group()
def cli() -> None:
    """Loadout — machine configuration management.

    Orchestrates dotfile building, Homebrew, global package installs,
    and health checks across multiple user/org contexts.
    """
    pass


@cli.command()
@click.option("--user", required=True, help="GitHub username for dotfile config.")
@click.option("--orgs", required=True, help="Comma-separated list of org names.")
def init(user: str, orgs: str) -> None:
    """Initialize loadout for a user and set of orgs."""
    pass


@cli.command()
def update() -> None:
    """Pull latest dotfile sources and rebuild configuration."""
    pass


@cli.command()
def upgrade() -> None:
    """Run Homebrew upgrade and update global packages."""
    pass


@cli.command()
def check() -> None:
    """Run health checks — warn only, never mutates."""
    pass


@cli.command()
def build() -> None:
    """Merge base + org fragments into final dotfiles."""
    pass


@cli.command("globals")
def globals_cmd() -> None:
    """Install non-Homebrew globals (Claude Code, npm, pip)."""
    pass


@cli.command()
@click.argument("mode", type=click.Choice(["connected", "solo"]))
def display(mode: str) -> None:
    """Switch macOS display profile."""
    pass
