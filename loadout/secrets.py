# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Secrets provider abstraction for SSH key management."""

from __future__ import annotations

import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loadout import runner
from loadout.exceptions import SecretsProviderError


class SecretsProvider(Protocol):
    """Protocol for secrets providers."""

    def read(self, secret_path: str, *, dry_run: bool = False) -> str: ...


@dataclass
class OnePasswordProvider:
    """1Password CLI (op) secrets provider."""

    def read(self, secret_path: str, *, dry_run: bool = False) -> str:
        """Read a secret from 1Password via the ``op`` CLI."""
        if shutil.which("op") is None:
            raise SecretsProviderError("1Password CLI (op) not found")
        if dry_run:
            return "DRY_RUN_SECRET"
        result = runner.run(["op", "read", secret_path], capture=True)
        return result.stdout.strip()


def get_provider(provider_type: str) -> SecretsProvider:
    """Factory: returns a provider instance for the given type."""
    providers: dict[str, type[SecretsProvider]] = {
        "op": OnePasswordProvider,
    }
    if provider_type not in providers:
        raise SecretsProviderError(
            f"Unknown secrets provider: {provider_type!r}. "
            f"Available: {', '.join(sorted(providers))}"
        )
    return providers[provider_type]()


@dataclass
class SshKeyConfig:
    """Configuration for a single SSH key."""

    org: str
    filename: str
    secret_path: str


def load_ssh_key_config(dotfiles_private_dir: Path) -> tuple[str, list[SshKeyConfig]]:
    """Load SSH key config from dotfiles-private/ssh/keys.toml.

    Returns ``(provider_type, list_of_key_configs)``.
    Returns ``("op", [])`` if config doesn't exist.
    """
    config_path = dotfiles_private_dir / "ssh" / "keys.toml"
    if not config_path.exists():
        return ("op", [])

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    provider_type = data.get("provider", {}).get("type", "op")
    keys: list[SshKeyConfig] = []
    for org, key_data in data.get("keys", {}).items():
        keys.append(
            SshKeyConfig(
                org=org,
                filename=key_data["filename"],
                secret_path=key_data["secret_path"],
            )
        )
    return (provider_type, keys)
