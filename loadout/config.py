# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Config model and path constants for loadout."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from loadout.exceptions import LoadoutConfigError

_ORG_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_org_names(orgs: list[str]) -> None:
    """Validate that all org names contain only safe characters.

    Raises :class:`LoadoutConfigError` if any org name contains characters
    outside ``[a-zA-Z0-9_-]`` (path traversal protection).
    """
    for org in orgs:
        if not _ORG_NAME_RE.match(org):
            raise LoadoutConfigError(f"Invalid org name {org!r}: must match [a-zA-Z0-9_-]+")


def _toml_escape(s: str) -> str:
    """Escape a string for inclusion in a TOML double-quoted value."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


@dataclass
class LoadoutConfig:
    """Central configuration for a loadout installation."""

    user: str = ""
    orgs: list[str] = field(default_factory=list)
    base_dir: Path | None = None
    github_token_op_path: str = "op://Personal/GitHub Token/credential"  # noqa: S105 — 1Password reference path, not a password
    nvm_version: str = "0.40.1"
    pyenv_version: str = "3"

    @property
    def home(self) -> Path:
        """Return the effective home directory."""
        return self.base_dir if self.base_dir is not None else Path.home()

    @property
    def dotfiles_dir(self) -> Path:
        """Return the path to the main dotfiles directory."""
        return self.home / ".dotfiles"

    @property
    def dotfiles_private_dir(self) -> Path:
        """Return the path to the private dotfiles directory."""
        return self.home / ".dotfiles-private"

    @property
    def build_dir(self) -> Path:
        """Return the path to the build output directory."""
        return self.dotfiles_dir / "build"

    @property
    def claude_dir(self) -> Path:
        """Return the path to the Claude configuration directory."""
        return self.home / ".claude"

    @property
    def ssh_keys_config_path(self) -> Path:
        """Return the path to the SSH keys TOML config file."""
        return self.dotfiles_private_dir / "ssh" / "keys.toml"

    @property
    def config_path(self) -> Path:
        """Return the path to the loadout TOML config file."""
        return self.dotfiles_dir / ".loadout.toml"


def load_config(base_dir: Path | None = None) -> LoadoutConfig:
    """Read configuration from ``~/.dotfiles/.loadout.toml``.

    Args:
        base_dir: Override the home directory for all paths. Useful for testing.

    Returns a default :class:`LoadoutConfig` when the file does not exist.
    """
    cfg = LoadoutConfig(base_dir=base_dir)
    path = cfg.config_path
    if not path.exists():
        return cfg

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise LoadoutConfigError(f"Invalid TOML in {path}: {exc}") from exc

    orgs = data.get("orgs", [])
    _validate_org_names(orgs)

    defaults = LoadoutConfig()
    return LoadoutConfig(
        user=data.get("user", ""),
        orgs=orgs,
        base_dir=base_dir,
        github_token_op_path=data.get("github_token_op_path", defaults.github_token_op_path),
        nvm_version=data.get("nvm_version", defaults.nvm_version),
        pyenv_version=data.get("pyenv_version", defaults.pyenv_version),
    )


def save_config(config: LoadoutConfig) -> None:
    """Write configuration to ``~/.dotfiles/.loadout.toml``.

    Uses manual TOML formatting to avoid an extra dependency.
    """
    path = config.config_path
    path.parent.mkdir(parents=True, exist_ok=True)

    user = _toml_escape(config.user)
    orgs_str = ", ".join(f'"{_toml_escape(o)}"' for o in config.orgs)
    op_path = _toml_escape(config.github_token_op_path)
    nvm_ver = _toml_escape(config.nvm_version)
    pyenv_ver = _toml_escape(config.pyenv_version)

    lines: list[str] = [
        f'user = "{user}"',
        f"orgs = [{orgs_str}]",
        f'github_token_op_path = "{op_path}"',
        f'nvm_version = "{nvm_ver}"',
        f'pyenv_version = "{pyenv_ver}"',
        "",  # trailing newline
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
