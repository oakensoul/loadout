"""Config model and path constants for loadout."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LoadoutConfig:
    """Central configuration for a loadout installation."""

    user: str = ""
    orgs: list[str] = field(default_factory=list)

    @property
    def dotfiles_dir(self) -> Path:
        """Return the path to the main dotfiles directory."""
        return Path.home() / ".dotfiles"

    @property
    def dotfiles_private_dir(self) -> Path:
        """Return the path to the private dotfiles directory."""
        return Path.home() / ".dotfiles-private"

    @property
    def build_dir(self) -> Path:
        """Return the path to the build output directory."""
        return self.dotfiles_dir / "build"

    @property
    def config_path(self) -> Path:
        """Return the path to the loadout TOML config file."""
        return self.dotfiles_dir / ".loadout.toml"


def load_config() -> LoadoutConfig:
    """Read configuration from ``~/.dotfiles/.loadout.toml``.

    Returns a default :class:`LoadoutConfig` when the file does not exist.
    """
    cfg = LoadoutConfig()
    path = cfg.config_path
    if not path.exists():
        return cfg

    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    return LoadoutConfig(
        user=data.get("user", ""),
        orgs=data.get("orgs", []),
    )


def save_config(config: LoadoutConfig) -> None:
    """Write configuration to ``~/.dotfiles/.loadout.toml``.

    Uses manual TOML formatting to avoid an extra dependency.
    """
    path = config.config_path
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f'user = "{config.user}"')
    orgs_str = ", ".join(f'"{o}"' for o in config.orgs)
    lines.append(f"orgs = [{orgs_str}]")
    lines.append("")  # trailing newline

    path.write_text("\n".join(lines))
