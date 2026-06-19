"""Pytest configuration."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def lumi_cache_in_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_root = tmp_path / "lumi-cache"

    def _default_cache_dir() -> Path:
        return cache_root

    monkeypatch.setattr("lumi.infrastructure.paths.default_cache_dir", _default_cache_dir)
