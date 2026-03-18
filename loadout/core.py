"""Core API facade — stable public interface for the AIDA plugin.

This module re-exports the functions that external consumers (like
aida-loadout-plugin) should import. It delegates to the specific
command modules and should not contain business logic itself.
"""


def check_health() -> None:
    """Run all health checks and return a summary.

    Delegates to :mod:`loadout.check` once implemented.
    """
    from loadout.check import render_checks, run_checks
    from loadout.config import load_config

    config = load_config()
    results = run_checks(config)
    render_checks(results)


def run_build(*, dry_run: bool = False) -> None:
    """Merge base + org fragments into final dotfiles.

    Delegates to :mod:`loadout.build`.
    """
    from loadout.build import build_dotfiles
    from loadout.config import load_config

    config = load_config()
    build_dotfiles(config, dry_run=dry_run)


def run_globals(*, dry_run: bool = False) -> None:
    """Install non-Homebrew globals (Claude Code, npm, pip).

    Delegates to :mod:`loadout.globals`.
    """
    from loadout.config import load_config
    from loadout.globals import install_globals

    config = load_config()
    install_globals(config, dry_run=dry_run)


def run_display(mode: str | None = None, *, dry_run: bool = False) -> None:
    """Switch macOS display profile.

    Delegates to :mod:`loadout.display`.
    """
    from loadout.config import load_config
    from loadout.display import apply_display_profile

    config = load_config()
    apply_display_profile(config, mode=mode, dry_run=dry_run)


def run_init(user: str, orgs: list[str], *, dry_run: bool = False) -> None:
    """Full machine bootstrap flow.

    Delegates to :mod:`loadout.init`.
    """
    from loadout.init import run_init as _run_init

    _run_init(user, orgs, dry_run=dry_run)


def run_update() -> None:
    """Pull latest sources and rebuild configuration.

    Delegates to :mod:`loadout.build` and :mod:`loadout.globals` once implemented.
    """
    pass
