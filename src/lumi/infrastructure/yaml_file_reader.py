"""YAML parsing helpers."""

from __future__ import annotations

from typing import Any

import yaml


def read_yaml_mapping(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Expected YAML mapping at document root")
    return data
