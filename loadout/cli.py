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
@click.pass_context
def init(ctx: click.Context, user: str, orgs: tuple[str, ...]) -> None:
    """Initialize loadout for a user and set of orgs."""
    from loadout.core import run_init

    run_init(user, list(orgs), dry_run=ctx.obj["dry_run"])


@cli.command()
def update() -> None:
    """Pull latest dotfile sources and rebuild configuration."""
    click.echo("Not yet implemented.", err=True)


@cli.command()
def upgrade() -> None:
    """Run Homebrew upgrade and update global packages."""
    click.echo("Not yet implemented.", err=True)


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
