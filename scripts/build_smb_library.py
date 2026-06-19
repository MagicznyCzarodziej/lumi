"""Build library from SMB share and optionally write JSON cache."""

from __future__ import annotations

import logging
import sys
from pathlib import PurePosixPath

from lumi.config.settings import get_settings
from lumi.container import build_container

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    settings = get_settings()
    if settings.mode != "smb":
        logger.error("Set mode: smb in config.yaml before building from SMB")
        return 1

    container = build_container(settings)
    root = PurePosixPath(settings.library_root)

    try:
        logger.info("Initializing library from %s", root)
        container.library_repository.initialize(root)
        entries = container.library_repository.get_top_level_entries()
        logger.info("Built library with %d top-level entries", len(entries))
        for entry in entries[:10]:
            logger.info("  - %s", entry.name.name)
        if len(entries) > 10:
            logger.info("  … and %d more", len(entries) - 10)
    except Exception:
        logger.exception("SMB library build failed")
        return 1
    finally:
        container.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
