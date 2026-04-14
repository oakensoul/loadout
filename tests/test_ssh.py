# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.ssh — SSH config generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from loadout.secrets import SshKeyConfig
from loadout.ssh import generate_ssh_config, install_ssh_config


class TestGenerateSshConfig:
    def test_single_key_gets_github_host(self, tmp_path: Path) -> None:
        """A single key without explicit host gets 'github.com'."""
        keys = [SshKeyConfig(org="personal", filename="id_ed25519", secret_path="")]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "Host github.com" in config
        assert f"IdentityFile {tmp_path / '.ssh' / 'id_ed25519'}" in config

    def test_explicit_host(self, tmp_path: Path) -> None:
        """Keys with explicit host use that value."""
        keys = [
            SshKeyConfig(
                org="work",
                filename="id_ed25519_work",
                secret_path="",
                host="github.com-work",
                host_name="github.com",
            )
        ]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "Host github.com-work" in config
        assert "HostName github.com" in config

    def test_multiple_keys_auto_alias(self, tmp_path: Path) -> None:
        """Second key without explicit host gets auto-aliased."""
        keys = [
            SshKeyConfig(org="personal", filename="id_key1", secret_path=""),
            SshKeyConfig(org="work", filename="id_key2", secret_path=""),
        ]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "Host github.com\n" in config
        assert "Host github.com-work" in config
        assert "HostName github.com" in config

    def test_includes_global_defaults(self, tmp_path: Path) -> None:
        """Config includes AddKeysToAgent and does not disable the agent."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "Host *" in config
        assert "AddKeysToAgent yes" in config
        assert "IdentityAgent none" not in config

    def test_includes_config_local(self, tmp_path: Path) -> None:
        """Config includes config.local before Host * so local entries take precedence."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "Include config.local" in config
        assert config.index("Include config.local") < config.index("Host *")

    @patch("loadout.ssh.is_macos", return_value=True)
    def test_macos_includes_usekeychain(self, _mock: object, tmp_path: Path) -> None:
        """On macOS, config includes UseKeychain yes."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "UseKeychain yes" in config

    @patch("loadout.ssh.is_macos", return_value=False)
    def test_linux_omits_usekeychain(self, _mock: object, tmp_path: Path) -> None:
        """On Linux, config omits UseKeychain."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        config = generate_ssh_config(keys, tmp_path / ".ssh")
        assert "UseKeychain" not in config

    def test_empty_keys_no_host_entries(self, tmp_path: Path) -> None:
        """Empty key list produces only global defaults."""
        config = generate_ssh_config([], tmp_path / ".ssh")
        assert "Host *" in config
        # No per-key Host entries
        lines = config.split("\n")
        host_lines = [line for line in lines if line.startswith("Host ") and line != "Host *"]
        assert len(host_lines) == 0


class TestInstallSshConfig:
    def test_writes_config_file(self, tmp_path: Path) -> None:
        """Should write SSH config to ~/.ssh/config."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        install_ssh_config(keys, tmp_path)

        config_path = tmp_path / ".ssh" / "config"
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "Host" in content

    def test_config_file_permissions(self, tmp_path: Path) -> None:
        """SSH config should be chmod 600."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        install_ssh_config(keys, tmp_path)

        config_path = tmp_path / ".ssh" / "config"
        assert oct(config_path.stat().st_mode & 0o777) == "0o600"

    def test_backs_up_existing_config(self, tmp_path: Path) -> None:
        """Should rename existing config to config.bak."""
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        existing = ssh_dir / "config"
        existing.write_text("old config\n", encoding="utf-8")

        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        install_ssh_config(keys, tmp_path)

        backup = ssh_dir / "config.bak"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "old config\n"
        assert existing.exists()
        assert "old config" not in existing.read_text(encoding="utf-8")

    def test_no_keys_skips(self, tmp_path: Path) -> None:
        """Should skip when no keys are configured."""
        install_ssh_config([], tmp_path)
        assert not (tmp_path / ".ssh" / "config").exists()

    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Dry run should not create config file."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        install_ssh_config(keys, tmp_path, dry_run=True)
        assert not (tmp_path / ".ssh" / "config").exists()

    def test_creates_ssh_dir(self, tmp_path: Path) -> None:
        """Should create ~/.ssh if it doesn't exist."""
        keys = [SshKeyConfig(org="test", filename="id_test", secret_path="")]
        install_ssh_config(keys, tmp_path)
        assert (tmp_path / ".ssh").is_dir()
