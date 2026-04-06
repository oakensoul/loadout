# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Robert Gunnar Johnson Jr.
"""Shared deep-merge utility for combining nested data structures."""

from __future__ import annotations


def deep_merge(base: object, overlay: object) -> object:
    """Recursively merge *overlay* into *base*; overlay values win on conflict."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return overlay
