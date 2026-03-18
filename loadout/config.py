"""Config model and path constants for loadout."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def _toml_escape(s: str) -> str:
    """Escape a string for inclusion in a TOML double-quoted value."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


@dataclass
class LoadoutConfig:
    """Central configuration for a loadout installation."""

    user: str = ""
    orgs: list[str] = field(default_factory=list)
    base_dir: Path | None = None

    def _home(self) -> Path:
        return self.base_dir if self.base_dir is not None else Path.home()

    @property
    def dotfiles_dir(self) -> Path:
        """Return the path to the main dotfiles directory."""
        return self._home() / ".dotfiles"

    @property
    def dotfiles_private_dir(self) -> Path:
        """Return the path to the private dotfiles directory."""
        return self._home() / ".dotfiles-private"

    @property
    def build_dir(self) -> Path:
        """Return the path to the build output directory."""
        return self.dotfiles_dir / "build"

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

    data = tomllib.loads(path.read_text(encoding="utf-8"))

    return LoadoutConfig(
        user=data.get("user", ""),
        orgs=data.get("orgs", []),
        base_dir=base_dir,
    )


def save_config(config: LoadoutConfig) -> None:
    """Write configuration to ``~/.dotfiles/.loadout.toml``.

    Uses manual TOML formatting to avoid an extra dependency.
    """
    path = config.config_path
    path.parent.mkdir(parents=True, exist_ok=True)

    user = _toml_escape(config.user)
    orgs_str = ", ".join(f'"{_toml_escape(o)}"' for o in config.orgs)

    lines: list[str] = [
        f'user = "{user}"',
        f"orgs = [{orgs_str}]",
        "",  # trailing newline
    ]

    path.write_text("\n".join(lines))
