# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from io import StringIO

import pytest
from rich.console import Console


@pytest.fixture()
def captured_console() -> tuple[Console, StringIO]:
    """Return a Console that writes to a StringIO buffer and the buffer itself."""
    buf = StringIO()
    return Console(file=buf, width=80), buf


@pytest.fixture(autouse=True)
def _reset_verbose() -> Iterator[None]:
    """Reset the global verbose flag after every test."""
    from loadout.ui import set_verbose

    yield
    set_verbose(False)
