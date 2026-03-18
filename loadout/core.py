"""Core API facade — stable public interface for the AIDA plugin.

This module re-exports the functions that external consumers (like
aida-loadout-plugin) should import. It delegates to the specific
command modules and should not contain business logic itself.
"""


def check_health() -> None:
    """Run all health checks and return a summary.

    Delegates to :mod:`loadout.check` once implemented.
    """
    pass


def run_update() -> None:
    """Pull latest sources and rebuild configuration.

    Delegates to :mod:`loadout.build` and :mod:`loadout.globals` once implemented.
    """
    pass
