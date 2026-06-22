"""NapiProjekt movie hash (MD5 of first 10 MB)."""

from __future__ import annotations

import hashlib

NAPI_HASH_BYTES = 10_485_760


def calc_napi_hash(first_bytes: bytes) -> str:
    return hashlib.md5(first_bytes[:NAPI_HASH_BYTES]).hexdigest()
