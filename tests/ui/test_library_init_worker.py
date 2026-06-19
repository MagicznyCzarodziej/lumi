"""LibraryInitWorker tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath
from unittest.mock import MagicMock

from lumi.domain.library.build_progress import LibraryBuildProgress
from lumi.ui.workers.library_init_worker import LibraryInitWorker


def test_library_init_worker_emits_progress(qtbot) -> None:
    repository = MagicMock()

    def initialize(root, ignore_cache=False, progress=None):
        del root, ignore_cache
        if progress is not None:
            progress(LibraryBuildProgress(completed=1, total=2, directory_name="Alpha"))
            progress(LibraryBuildProgress(completed=2, total=2, directory_name="Beta"))

    repository.initialize.side_effect = initialize

    worker = LibraryInitWorker(repository, MOCK_LIBRARY_ROOT)
    progress_updates: list[tuple[int, int, str]] = []
    worker.progress.connect(lambda completed, total, name: progress_updates.append((completed, total, name)))

    with qtbot.waitSignal(worker.finished_ok, timeout=1000):
        worker.start()

    assert progress_updates == [(1, 2, "Alpha"), (2, 2, "Beta")]


def test_library_init_worker_emits_cache_warning(qtbot) -> None:
    repository = MagicMock()
    repository.initialize.return_value = None
    repository.last_cache_warning = "Could not save library cache to disk."

    worker = LibraryInitWorker(repository, MOCK_LIBRARY_ROOT)
    warnings: list[str] = []
    worker.cache_warning.connect(warnings.append)

    with qtbot.waitSignal(worker.finished_ok, timeout=1000):
        worker.start()

    assert warnings == ["Could not save library cache to disk."]
