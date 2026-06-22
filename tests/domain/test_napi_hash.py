from __future__ import annotations

import hashlib

from lumi.domain.subtitles.napi_hash import NAPI_HASH_BYTES, calc_napi_hash


def test_calc_napi_hash_uses_first_10mb() -> None:
    data = b"a" * (NAPI_HASH_BYTES + 100)
    assert calc_napi_hash(data) == hashlib.md5(data[:NAPI_HASH_BYTES]).hexdigest()
