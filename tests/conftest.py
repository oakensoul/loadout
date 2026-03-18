"""Shared test fixtures."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console


@pytest.fixture()
def captured_console() -> tuple[Console, StringIO]:
    """Return a Console that writes to a StringIO buffer and the buffer itself."""
    buf = StringIO()
    return Console(file=buf, width=80), buf
