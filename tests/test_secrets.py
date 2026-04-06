# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.secrets — secrets provider abstraction."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loadout.exceptions import SecretsProviderError
from loadout.secrets import (
    OnePasswordProvider,
    SshKeyConfig,
    get_provider,
    load_ssh_key_config,
)

# ---------------------------------------------------------------------------
# OnePasswordProvider
# ---------------------------------------------------------------------------


@patch("loadout.secrets.runner.run")
@patch("loadout.secrets.shutil.which", return_value="/usr/local/bin/op")
def test_op_provider_read_calls_op_cli(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """read() should call ``op read <path>`` and return stripped stdout."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=["op", "read", "op://vault/item/field"],
        returncode=0,
        stdout="secret-value\n",
        stderr="",
    )

    provider = OnePasswordProvider()
    result = provider.read("op://vault/item/field")

    assert result == "secret-value"
    mock_run.assert_called_once_with(["op", "read", "op://vault/item/field"], capture=True)


@patch("loadout.secrets.shutil.which", return_value="/usr/local/bin/op")
@patch("loadout.secrets.runner.run")
def test_op_provider_read_failure_propagates(mock_run: MagicMock, mock_which: MagicMock) -> None:
    """read() should propagate errors when op CLI fails."""
    from loadout.exceptions import LoadoutCommandError

    mock_run.side_effect = LoadoutCommandError("op read failed")

    provider = OnePasswordProvider()
    with pytest.raises(LoadoutCommandError, match="op read failed"):
        provider.read("op://vault/item/field")


@patch("loadout.secrets.shutil.which", return_value=None)
def test_op_provider_read_raises_when_op_not_found(mock_which: MagicMock) -> None:
    """read() should raise SecretsProviderError when op CLI is missing."""
    provider = OnePasswordProvider()

    with pytest.raises(SecretsProviderError, match="1Password CLI"):
        provider.read("op://vault/item/field")


# ---------------------------------------------------------------------------
# get_provider
# ---------------------------------------------------------------------------


def test_get_provider_op_returns_one_password_provider() -> None:
    """get_provider('op') should return a OnePasswordProvider instance."""
    provider = get_provider("op")
    assert isinstance(provider, OnePasswordProvider)


def test_get_provider_unknown_raises() -> None:
    """get_provider('unknown') should raise SecretsProviderError."""
    with pytest.raises(SecretsProviderError, match="Unknown secrets provider"):
        get_provider("unknown")


# ---------------------------------------------------------------------------
# load_ssh_key_config
# ---------------------------------------------------------------------------


def test_load_ssh_key_config_missing_file_returns_empty(tmp_path: Path) -> None:
    """Missing keys.toml should return ('op', [])."""
    provider_type, keys = load_ssh_key_config(tmp_path)

    assert provider_type == "op"
    assert keys == []


def test_load_ssh_key_config_valid_toml(tmp_path: Path) -> None:
    """Valid keys.toml should parse provider and key configs."""
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    (ssh_dir / "keys.toml").write_text(
        """\
[provider]
type = "op"

[keys.acme]
filename = "id_ed25519_acme"
secret_path = "op://Vault/acme-ssh/private_key"

[keys.personal]
filename = "id_ed25519_personal"
secret_path = "op://Personal/ssh/private_key"
""",
        encoding="utf-8",
    )

    provider_type, keys = load_ssh_key_config(tmp_path)

    assert provider_type == "op"
    assert len(keys) == 2
    assert all(isinstance(k, SshKeyConfig) for k in keys)

    orgs = {k.org for k in keys}
    assert orgs == {"acme", "personal"}


def test_load_ssh_key_config_multiple_keys(tmp_path: Path) -> None:
    """Multiple key entries should all be returned."""
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    (ssh_dir / "keys.toml").write_text(
        """\
[provider]
type = "op"

[keys.org1]
filename = "id_org1"
secret_path = "op://V/org1/key"

[keys.org2]
filename = "id_org2"
secret_path = "op://V/org2/key"

[keys.org3]
filename = "id_org3"
secret_path = "op://V/org3/key"
""",
        encoding="utf-8",
    )

    provider_type, keys = load_ssh_key_config(tmp_path)

    assert provider_type == "op"
    assert len(keys) == 3
    filenames = {k.filename for k in keys}
    assert filenames == {"id_org1", "id_org2", "id_org3"}


def test_load_ssh_key_config_missing_field_raises(tmp_path: Path) -> None:
    """Missing required field should raise SecretsProviderError."""
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    (ssh_dir / "keys.toml").write_text(
        """\
[keys.broken]
filename = "id_broken"
""",
        encoding="utf-8",
    )

    with pytest.raises(SecretsProviderError, match="missing required field"):
        load_ssh_key_config(tmp_path)


def test_load_ssh_key_config_defaults_provider_to_op(tmp_path: Path) -> None:
    """When [provider] section is missing, default to 'op'."""
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    (ssh_dir / "keys.toml").write_text(
        """\
[keys.myorg]
filename = "id_myorg"
secret_path = "op://V/myorg/key"
""",
        encoding="utf-8",
    )

    provider_type, keys = load_ssh_key_config(tmp_path)

    assert provider_type == "op"
    assert len(keys) == 1
