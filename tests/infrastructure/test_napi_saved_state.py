from __future__ import annotations

from pathlib import PurePosixPath

from lumi.infrastructure.subtitles.napi_saved_state import JsonNapiSavedStateStore


def test_napi_saved_state_tracks_saved_videos(tmp_path) -> None:
    store = JsonNapiSavedStateStore(tmp_path / "napi_saved_state.json")
    video = PurePosixPath("/Movies/Foo/Foo.mkv")

    assert not store.is_saved_to_nas(video)
    store.mark_saved_to_nas(video)
    assert store.is_saved_to_nas(video)

    reloaded = JsonNapiSavedStateStore(tmp_path / "napi_saved_state.json")
    assert reloaded.is_saved_to_nas(video)

    store.clear(video)
    assert not store.is_saved_to_nas(video)
