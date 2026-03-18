"""Tests for loadout.ui — Rich console helpers."""

from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import pytest

from loadout import ui

if TYPE_CHECKING:
    from rich.console import Console


# ── status_line ──────────────────────────────────────────────────────────────


class TestStatusLine:
    def test_output_contains_all_parts(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        ui.status_line("🔧", "Build", "completed successfully")

        output = buf.getvalue()
        assert "🔧" in output
        assert "Build" in output
        assert "completed successfully" in output

    def test_output_format(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        ui.status_line("→", "Step", "details")

        output = buf.getvalue().strip()
        assert output == "→  Step  details"


# ── section_header ───────────────────────────────────────────────────────────


class TestSectionHeader:
    def test_output_contains_title(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        ui.section_header("Configuration")

        output = buf.getvalue()
        assert "Configuration" in output

    def test_output_contains_rule_characters(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        ui.section_header("Setup")

        output = buf.getvalue()
        # Rich Rule uses '─' characters by default
        assert "─" in output


# ── run_step ─────────────────────────────────────────────────────────────────


class TestRunStep:
    def test_success_returns_value(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, _buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        result = ui.run_step("adding numbers", lambda: 42)

        assert result == 42

    def test_success_shows_checkmark(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        ui.run_step("doing work", lambda: None)

        output = buf.getvalue()
        assert "✓" in output
        assert "doing work" in output

    def test_failure_shows_x_and_reraises(
        self, monkeypatch: pytest.MonkeyPatch, captured_console: tuple[Console, StringIO]
    ) -> None:
        test_console, buf = captured_console
        monkeypatch.setattr(ui, "console", test_console)

        def failing() -> None:
            msg = "boom"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="boom"):
            ui.run_step("risky step", failing)

        output = buf.getvalue()
        assert "✗" in output
        assert "risky step" in output
