"""Subtitle file content hashing for duplicate detection."""

from __future__ import annotations

import hashlib


def normalize_subtitle_bytes(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip().encode("utf-8")


def subtitle_content_hash(data: bytes) -> str:
    return hashlib.sha256(normalize_subtitle_bytes(data)).hexdigest()
