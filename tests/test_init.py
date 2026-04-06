# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.init — full machine bootstrap flow."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from loadout.config import LoadoutConfig
from loadout.init import (
    _bootstrap_canvas_config,
    _collect_existing_pub_keys,
    _ensure_gh_authenticated,
    _provision_ssh_keys,
    run_init,
)


def _fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Return a successful CompletedProcess for any command."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Full flow
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=True)
@patch("loadout.init.generate_launch_agent_plist", return_value="<plist/>")
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_full_flow(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_plist: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """All steps should execute in order (fallback to keygen, no provider config)."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()

    run_init("testuser", ["orgA", "orgB"], base_dir=tmp_path)

    # 1. Xcode CLI Tools check (via runner.run)
    xcode_calls = [c for c in mock_run.call_args_list if "xcode-select" in c.args[0]]
    assert len(xcode_calls) == 1

    # 3. SSH keygen (fallback — no keys.toml)
    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 1

    # 5. Switch remotes — repo names should NOT have leading dot
    set_url_calls = [c for c in mock_run.call_args_list if "set-url" in c.args[0]]
    assert len(set_url_calls) == 2
    for c in set_url_calls:
        url = c.args[0][-1]
        assert "/." not in url, f"URL should not have leading dot: {url}"

    # 6. Build dotfiles
    mock_build.assert_called_once()

    # 7. Brew bundle
    mock_brew.assert_called_once()

    # 8. Install globals
    mock_globals.assert_called_once()

    # 9. Build Claude config
    mock_claude.assert_called_once()

    # 10. Apply macOS defaults
    mock_macos_defaults.assert_called_once()

    # 12. Save config
    mock_save.assert_called_once()
    saved_config = mock_save.call_args.args[0]
    assert saved_config.user == "testuser"
    assert saved_config.orgs == ["orgA", "orgB"]


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_dry_run(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """Mutating calls should receive dry_run=True; save_config skipped."""
    run_init("testuser", ["org1"], base_dir=tmp_path, dry_run=True)

    # All mutating runner.run calls should have dry_run=True
    # Read-only calls (gh auth status) are exempt
    for c in mock_run.call_args_list:
        cmd = c.args[0] if c.args else []
        if cmd == ["gh", "auth", "status"]:
            continue  # read-only check, always runs
        assert c.kwargs.get("dry_run") is True, f"Expected dry_run=True: {c}"

    # build_dotfiles should get dry_run=True
    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs.get("dry_run") is True

    # install_globals should get dry_run=True
    mock_globals.assert_called_once()
    assert mock_globals.call_args.kwargs.get("dry_run") is True

    # brew_bundle should get dry_run=True
    mock_brew.assert_called_once()
    assert mock_brew.call_args.kwargs.get("dry_run") is True

    # build_claude_config should get dry_run=True
    mock_claude.assert_called_once()
    assert mock_claude.call_args.kwargs.get("dry_run") is True

    # apply_macos_defaults should get dry_run=True
    mock_macos_defaults.assert_called_once()
    assert mock_macos_defaults.call_args.kwargs.get("dry_run") is True

    # save_config should NOT be called in dry-run
    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# Existing dotfiles skip clone
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_existing_dotfiles_skips_clone(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When dotfiles dirs already exist, git clone should not be called."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()

    run_init("testuser", ["org1"], base_dir=tmp_path)

    clone_calls = [c for c in mock_run.call_args_list if "clone" in c.args[0]]
    assert len(clone_calls) == 0


# ---------------------------------------------------------------------------
# Existing SSH key skips keygen
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_existing_ssh_key_skips_keygen(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When SSH key already exists, ssh-keygen should not be called."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("fake key", encoding="utf-8")

    run_init("testuser", ["org1"], base_dir=tmp_path)

    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 0


# ---------------------------------------------------------------------------
# No op CLI skips SSH registration
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_no_op_cli_skips_ssh_registration(
    mock_ssh_config: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """When 1Password CLI is not available, SSH registration is skipped."""

    def selective_which(name: str) -> str | None:
        if name == "op":
            return None
        return "/usr/bin/thing"

    with patch("loadout.init.shutil.which", side_effect=selective_which):
        run_init("testuser", ["org1"], base_dir=tmp_path)

    # No bash pipeline (op read | gh auth login) calls
    bash_auth_calls = [
        c
        for c in mock_run.call_args_list
        if c.args[0][0] == "bash" and "gh auth login" in str(c.args[0])
    ]
    assert len(bash_auth_calls) == 0


# ---------------------------------------------------------------------------
# No brew skips bundle
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_no_brew_skips_bundle(
    mock_ssh_config: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """brew_bundle is called regardless; it handles missing brew internally."""

    def selective_which(name: str) -> str | None:
        if name == "brew":
            return None
        return "/usr/bin/thing"

    with patch("loadout.init.shutil.which", side_effect=selective_which):
        run_init("testuser", ["org1"], base_dir=tmp_path)

    # brew_bundle is still called (it decides internally to skip)
    mock_brew.assert_called_once()


# ---------------------------------------------------------------------------
# Save config
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_saves_config(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """save_config should be called with correct user and orgs."""
    run_init("myuser", ["orgX", "orgY"], base_dir=tmp_path)

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert isinstance(saved, LoadoutConfig)
    assert saved.user == "myuser"
    assert saved.orgs == ["orgX", "orgY"]


# ---------------------------------------------------------------------------
# Non-macOS skips launch agent
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_non_macos_skips_launch_agent(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """On non-macOS, the launch agent plist should not be written."""
    run_init("testuser", ["org1"], base_dir=tmp_path)

    launchctl_calls = [c for c in mock_run.call_args_list if "launchctl" in c.args[0]]
    assert len(launchctl_calls) == 0

    plist_path = tmp_path / "Library" / "LaunchAgents" / "com.oakensoul.loadout.display.plist"
    assert not plist_path.exists()


# ---------------------------------------------------------------------------
# Canvas config bootstrap
# ---------------------------------------------------------------------------


@patch("loadout.init.shutil.which", return_value="/usr/local/bin/canvas")
def test_bootstrap_canvas_config_creates_file(mock_which: MagicMock, tmp_path: Path) -> None:
    """Should create ~/.canvas/config.json with first org."""
    config = LoadoutConfig(user="testuser", orgs=["myorg", "other"], base_dir=tmp_path)
    _bootstrap_canvas_config(config)

    config_path = tmp_path / ".canvas" / "config.json"
    assert config_path.exists()
    import json

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data == {"org": "myorg"}


@patch("loadout.init.shutil.which", return_value="/usr/local/bin/canvas")
def test_bootstrap_canvas_config_skips_if_exists(mock_which: MagicMock, tmp_path: Path) -> None:
    """Should not overwrite existing config."""
    canvas_dir = tmp_path / ".canvas"
    canvas_dir.mkdir()
    config_path = canvas_dir / "config.json"
    config_path.write_text('{"org": "existing"}', encoding="utf-8")

    config = LoadoutConfig(user="testuser", orgs=["neworg"], base_dir=tmp_path)
    _bootstrap_canvas_config(config)

    import json

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data == {"org": "existing"}


@patch("loadout.init.shutil.which", return_value=None)
def test_bootstrap_canvas_config_skips_if_not_installed(
    mock_which: MagicMock, tmp_path: Path
) -> None:
    """Should skip when canvas CLI is not installed."""
    config = LoadoutConfig(user="testuser", orgs=["myorg"], base_dir=tmp_path)
    _bootstrap_canvas_config(config)

    config_path = tmp_path / ".canvas" / "config.json"
    assert not config_path.exists()


@patch("loadout.init.shutil.which", return_value="/usr/local/bin/canvas")
def test_bootstrap_canvas_config_skips_if_no_orgs(mock_which: MagicMock, tmp_path: Path) -> None:
    """Should skip when no orgs are configured."""
    config = LoadoutConfig(user="testuser", orgs=[], base_dir=tmp_path)
    _bootstrap_canvas_config(config)

    config_path = tmp_path / ".canvas" / "config.json"
    assert not config_path.exists()


@patch("loadout.init.shutil.which", return_value="/usr/local/bin/canvas")
def test_bootstrap_canvas_config_dry_run(mock_which: MagicMock, tmp_path: Path) -> None:
    """Dry-run should not create the config file."""
    config = LoadoutConfig(user="testuser", orgs=["myorg"], base_dir=tmp_path)
    _bootstrap_canvas_config(config, dry_run=True)

    config_path = tmp_path / ".canvas" / "config.json"
    assert not config_path.exists()


# ---------------------------------------------------------------------------
# _ensure_gh_authenticated
# ---------------------------------------------------------------------------


@patch("loadout.init.runner.run")
@patch("loadout.init.shutil.which", return_value="/usr/bin/gh")
def test_ensure_gh_already_authenticated(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should return True without browser auth when already logged in."""
    mock_run.return_value = subprocess.CompletedProcess(
        args=["gh", "auth", "status"], returncode=0, stdout="", stderr=""
    )
    assert _ensure_gh_authenticated() is True
    mock_run.assert_called_once_with(["gh", "auth", "status"], capture=True, check=False)


@patch("loadout.init.shutil.which", return_value=None)
def test_ensure_gh_not_installed(mock_which: MagicMock) -> None:
    """Should return False when gh CLI is not found."""
    assert _ensure_gh_authenticated() is False


@patch("loadout.init.runner.run")
@patch("loadout.init.shutil.which", return_value="/usr/bin/gh")
def test_ensure_gh_triggers_browser_auth(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Should open browser auth when not logged in."""
    mock_run.side_effect = [
        # First call: gh auth status — not authenticated
        subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=""),
        # Second call: gh auth login --web -p ssh — success
        subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    ]
    assert _ensure_gh_authenticated() is True
    assert mock_run.call_count == 2
    login_call = mock_run.call_args_list[1]
    assert "auth" in login_call.args[0]
    assert "login" in login_call.args[0]
    assert "--web" in login_call.args[0]


@patch("loadout.init.runner.run")
@patch("loadout.init.shutil.which", return_value="/usr/bin/gh")
def test_ensure_gh_dry_run(mock_which: MagicMock, mock_run: MagicMock) -> None:
    """Dry run should skip browser auth."""
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    assert _ensure_gh_authenticated(dry_run=True) is True
    # Should only call auth status, not auth login
    assert mock_run.call_count == 1


# ---------------------------------------------------------------------------
# _provision_ssh_keys — fallback to keygen
# ---------------------------------------------------------------------------


@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
@patch("loadout.init.runner.run", side_effect=_fake_run)
def test_provision_ssh_keys_fallback_keygen(
    mock_run: MagicMock,
    mock_ssh_config: MagicMock,
    tmp_path: Path,
) -> None:
    """When no keys.toml exists, should fall back to ssh-keygen."""
    config = LoadoutConfig(user="testuser", orgs=["org1"], base_dir=tmp_path)

    _provision_ssh_keys(config)

    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 1
    # Should target id_ed25519
    assert str(tmp_path / ".ssh" / "id_ed25519") in keygen_calls[0].args[0]


# ---------------------------------------------------------------------------
# _provision_ssh_keys — from provider
# ---------------------------------------------------------------------------


@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.runner.run")
@patch("loadout.init.get_provider")
@patch("loadout.init.load_ssh_key_config")
def test_provision_ssh_keys_from_provider(
    mock_ssh_config: MagicMock,
    mock_get_provider: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    tmp_path: Path,
) -> None:
    """When keys.toml has entries, should pull keys from provider."""
    from loadout.secrets import SshKeyConfig

    mock_ssh_config.return_value = (
        "op",
        [SshKeyConfig(org="acme", filename="id_acme", secret_path="op://V/acme/key")],
    )
    mock_provider = MagicMock()
    mock_provider.read.return_value = "PRIVATE_KEY_DATA"
    mock_get_provider.return_value = mock_provider

    # ssh-keygen -y -f returns the public key
    mock_run.return_value = subprocess.CompletedProcess(
        args=["ssh-keygen"], returncode=0, stdout="ssh-ed25519 AAAA acme\n", stderr=""
    )

    config = LoadoutConfig(user="testuser", orgs=["acme"], base_dir=tmp_path)
    pub_keys = _provision_ssh_keys(config)

    # Provider should be called
    mock_provider.read.assert_called_once_with("op://V/acme/key")

    # Private key should be written
    key_path = tmp_path / ".ssh" / "id_acme"
    assert key_path.exists()
    assert key_path.read_text() == "PRIVATE_KEY_DATA"
    assert oct(key_path.stat().st_mode & 0o777) == "0o600"

    # Public key should be derived
    pub_path = tmp_path / ".ssh" / "id_acme.pub"
    assert pub_path.exists()
    assert pub_path.read_text().strip() == "ssh-ed25519 AAAA acme"

    assert pub_keys == [pub_path]


# ---------------------------------------------------------------------------
# _provision_ssh_keys — existing key skips
# ---------------------------------------------------------------------------


@patch("loadout.init.load_ssh_key_config")
def test_provision_ssh_keys_existing_key_skips(
    mock_ssh_config: MagicMock,
    tmp_path: Path,
) -> None:
    """When a key file already exists, it should be skipped."""
    from loadout.secrets import SshKeyConfig

    mock_ssh_config.return_value = (
        "op",
        [SshKeyConfig(org="acme", filename="id_acme", secret_path="op://V/acme/key")],
    )

    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir(parents=True)
    (ssh_dir / "id_acme").write_text("existing key", encoding="utf-8")
    (ssh_dir / "id_acme.pub").write_text("existing pub", encoding="utf-8")

    config = LoadoutConfig(user="testuser", orgs=["acme"], base_dir=tmp_path)
    pub_keys = _provision_ssh_keys(config)

    # Should return the existing pub key
    assert pub_keys == [ssh_dir / "id_acme.pub"]


# ---------------------------------------------------------------------------
# _provision_ssh_keys — keychain integration (macOS)
# ---------------------------------------------------------------------------


@patch("loadout.init.is_macos", return_value=True)
@patch("loadout.init.runner.run")
@patch("loadout.init.get_provider")
@patch("loadout.init.load_ssh_key_config")
def test_provision_ssh_keys_adds_to_keychain_on_macos(
    mock_ssh_config: MagicMock,
    mock_get_provider: MagicMock,
    mock_run: MagicMock,
    mock_is_macos: MagicMock,
    tmp_path: Path,
) -> None:
    """On macOS, provisioned keys should be added to the keychain."""
    from loadout.secrets import SshKeyConfig

    mock_ssh_config.return_value = (
        "op",
        [SshKeyConfig(org="acme", filename="id_acme", secret_path="op://V/acme/key")],
    )
    mock_provider = MagicMock()
    mock_provider.read.return_value = "PRIVATE_KEY_DATA"
    mock_get_provider.return_value = mock_provider

    mock_run.return_value = subprocess.CompletedProcess(
        args=["ssh-keygen"], returncode=0, stdout="ssh-ed25519 AAAA acme\n", stderr=""
    )

    config = LoadoutConfig(user="testuser", orgs=["acme"], base_dir=tmp_path)
    _provision_ssh_keys(config)

    # Should call ssh-add --apple-use-keychain
    keychain_calls = [c for c in mock_run.call_args_list if "ssh-add" in c.args[0]]
    assert len(keychain_calls) == 1
    assert "--apple-use-keychain" in keychain_calls[0].args[0]


# ---------------------------------------------------------------------------
# _provision_ssh_keys — dry run with provider config
# ---------------------------------------------------------------------------


@patch("loadout.init.load_ssh_key_config")
def test_provision_ssh_keys_dry_run_with_provider(
    mock_ssh_config: MagicMock,
    tmp_path: Path,
) -> None:
    """Dry-run with provider config should not write files."""
    from loadout.secrets import SshKeyConfig

    mock_ssh_config.return_value = (
        "op",
        [SshKeyConfig(org="acme", filename="id_acme", secret_path="op://V/acme/key")],
    )

    config = LoadoutConfig(user="testuser", orgs=["acme"], base_dir=tmp_path)
    pub_keys = _provision_ssh_keys(config, dry_run=True)

    # Should return pub path but not write the key
    assert len(pub_keys) == 1
    key_path = tmp_path / ".ssh" / "id_acme"
    assert not key_path.exists()


# ---------------------------------------------------------------------------
# _collect_existing_pub_keys
# ---------------------------------------------------------------------------


@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_collect_existing_pub_keys_fallback(mock_ssh_config: MagicMock, tmp_path: Path) -> None:
    """Without key config, should find default id_ed25519.pub if it exists."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    pub = ssh_dir / "id_ed25519.pub"
    pub.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")

    config = LoadoutConfig(user="testuser", orgs=["org1"], base_dir=tmp_path)
    result = _collect_existing_pub_keys(config)
    assert result == [pub]


@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_collect_existing_pub_keys_no_keys(mock_ssh_config: MagicMock, tmp_path: Path) -> None:
    """When no keys exist on disk, should return empty list."""
    config = LoadoutConfig(user="testuser", orgs=["org1"], base_dir=tmp_path)
    result = _collect_existing_pub_keys(config)
    assert result == []


@patch("loadout.init.load_ssh_key_config")
def test_collect_existing_pub_keys_from_config(mock_ssh_config: MagicMock, tmp_path: Path) -> None:
    """Should find pub keys matching key config entries."""
    from loadout.secrets import SshKeyConfig

    mock_ssh_config.return_value = (
        "op",
        [
            SshKeyConfig(org="acme", filename="id_acme", secret_path="op://V/acme/key"),
            SshKeyConfig(org="beta", filename="id_beta", secret_path="op://V/beta/key"),
        ],
    )
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_acme.pub").write_text("ssh-ed25519 AAAA acme\n", encoding="utf-8")
    # id_beta.pub does not exist

    config = LoadoutConfig(user="testuser", orgs=["acme", "beta"], base_dir=tmp_path)
    result = _collect_existing_pub_keys(config)
    assert result == [ssh_dir / "id_acme.pub"]


# ---------------------------------------------------------------------------
# Headless mode
# ---------------------------------------------------------------------------


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_headless_skips_interactive(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """Headless mode should skip interactive steps but still run build, claude, save."""
    (tmp_path / ".dotfiles").mkdir()
    (tmp_path / ".dotfiles-private").mkdir()

    run_init("testuser", ["org1"], base_dir=tmp_path, headless=True)

    # Interactive steps should NOT be called
    mock_brew.assert_not_called()
    mock_globals.assert_not_called()
    mock_macos_defaults.assert_not_called()

    # SSH keygen should NOT be called (headless skips provisioning)
    keygen_calls = [c for c in mock_run.call_args_list if "ssh-keygen" in c.args[0]]
    assert len(keygen_calls) == 0

    # Xcode should NOT be called
    xcode_calls = [c for c in mock_run.call_args_list if "xcode-select" in c.args[0]]
    assert len(xcode_calls) == 0

    # GitHub auth should NOT be called
    gh_auth_calls = [c for c in mock_run.call_args_list if "gh" in c.args[0]]
    assert len(gh_auth_calls) == 0

    # Non-interactive steps SHOULD still run
    mock_build.assert_called_once()
    mock_claude.assert_called_once()
    mock_save.assert_called_once()


@patch("loadout.init.save_config")
@patch("loadout.init.apply_macos_defaults")
@patch("loadout.init.build_claude_config")
@patch("loadout.init.install_globals")
@patch("loadout.init.build_dotfiles")
@patch("loadout.init.is_macos", return_value=False)
@patch("loadout.init.brew_bundle")
@patch("loadout.init.runner.run", side_effect=_fake_run)
@patch("loadout.init.shutil.which", return_value="/usr/bin/thing")
@patch("loadout.init.load_ssh_key_config", return_value=("op", []))
def test_run_init_headless_still_clones_repos(
    mock_ssh_config: MagicMock,
    mock_which: MagicMock,
    mock_run: MagicMock,
    mock_brew: MagicMock,
    mock_is_macos: MagicMock,
    mock_build: MagicMock,
    mock_globals: MagicMock,
    mock_claude: MagicMock,
    mock_macos_defaults: MagicMock,
    mock_save: MagicMock,
    tmp_path: Path,
) -> None:
    """Headless mode should still clone dotfiles repos."""
    run_init("testuser", ["org1"], base_dir=tmp_path, headless=True)

    clone_calls = [c for c in mock_run.call_args_list if "clone" in c.args[0]]
    assert len(clone_calls) == 2  # dotfiles + dotfiles-private
