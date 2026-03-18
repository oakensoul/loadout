"""Click CLI entry point for loadout."""

import click


@click.group()
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show what would be done without executing."
)
@click.pass_context
def cli(ctx: click.Context, dry_run: bool) -> None:
    """Loadout — machine configuration management.

    Orchestrates dotfile building, Homebrew, global package installs,
    and health checks across multiple user/org contexts.
    """
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run


@cli.command()
@click.option("--user", required=True, help="GitHub username for dotfile config.")
@click.option("--orgs", required=True, multiple=True, help="Org names (repeat for multiple).")
def init(user: str, orgs: tuple[str, ...]) -> None:
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
@click.pass_context
def check(ctx: click.Context) -> None:
    """Run health checks — warn only, never mutates."""
    from loadout import ui
    from loadout.check import render_checks, run_checks
    from loadout.config import load_config

    config = load_config()
    ui.section_header("ENVIRONMENT")
    results = run_checks(config)
    render_checks(results)


@cli.command()
@click.pass_context
def build(ctx: click.Context) -> None:
    """Merge base + org fragments into final dotfiles."""
    from loadout.build import build_dotfiles
    from loadout.config import load_config

    config = load_config()
    build_dotfiles(config, dry_run=ctx.obj["dry_run"])


@cli.command("globals")
def globals_cmd() -> None:
    """Install non-Homebrew globals (Claude Code, npm, pip)."""
    pass


@cli.command()
@click.argument("mode", type=click.Choice(["connected", "solo"]))
def display(mode: str) -> None:
    """Switch macOS display profile."""
    pass
