"""Load mock library via container — Phase 2 smoke script."""

from __future__ import annotations

import logging
import sys
from pathlib import PurePosixPath

from lumi.config.settings import get_settings
from lumi.container import build_container


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    settings = get_settings().model_copy(update={"mode": "mock"})
    if get_settings().mode != "mock":
        logger.info("Forcing mock mode for fixture load (config.yaml has mode=%s)", get_settings().mode)

    container = build_container(settings)
    container.library_repository.initialize(PurePosixPath(container.settings.library_root))
    count = len(container.library_repository.get_top_level_entries())
    logger.info("Loaded %d library entries (mode=%s)", count, container.settings.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
