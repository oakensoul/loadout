"""Custom exception hierarchy for loadout."""

from __future__ import annotations


class LoadoutError(Exception):
    """Base exception for all loadout errors."""


class LoadoutConfigError(LoadoutError):
    """Raised when loadout configuration is invalid or missing."""


class LoadoutCommandError(LoadoutError):
    """Raised when a shell command fails during execution."""

    def __init__(
        self,
        message: str,
        *,
        cmd: str = "",
        exit_code: int | None = None,
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.cmd = cmd
        self.exit_code = exit_code
        self.stderr = stderr


class LoadoutBuildError(LoadoutError):
    """Raised when the dotfile build process fails."""
