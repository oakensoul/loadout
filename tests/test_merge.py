# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Tests for loadout.merge module."""

from __future__ import annotations

from loadout.merge import deep_merge


class TestDeepMerge:
    """Tests for the deep_merge utility."""

    def test_deep_merge_dicts(self) -> None:
        """Merging two flat dicts combines all keys."""
        base = {"a": 1, "b": 2}
        overlay = {"c": 3}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_deep_merge_overlay_wins(self) -> None:
        """Overlay values win on key conflict."""
        base = {"a": 1, "b": 2}
        overlay = {"b": 99}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 99}

    def test_deep_merge_nested(self) -> None:
        """Nested dicts are merged recursively."""
        base = {"nested": {"x": 10, "y": 20}, "top": True}
        overlay = {"nested": {"y": 99, "z": 30}}
        result = deep_merge(base, overlay)
        assert result == {"nested": {"x": 10, "y": 99, "z": 30}, "top": True}

    def test_deep_merge_non_dict_overlay(self) -> None:
        """When overlay is not a dict, it replaces base entirely."""
        assert deep_merge({"a": 1}, "string") == "string"
        assert deep_merge({"a": 1}, 42) == 42
        assert deep_merge({"a": 1}, [1, 2]) == [1, 2]
        assert deep_merge("old", "new") == "new"
