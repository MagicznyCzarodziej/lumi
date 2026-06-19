"""SMB connectivity spike — list one directory on the configured share."""

from __future__ import annotations

import logging
import sys
from pathlib import PurePosixPath

from lumi.config.settings import get_settings
from lumi.config.smb_config import SmbConfig
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    settings = get_settings()

    if settings.mode != "smb":
        logger.error("Set mode: smb in config.yaml (or LUMI_MODE=smb) before running the spike")
        return 1

    missing = [
        name
        for name, value in [
            ("smb.hostname", settings.smb_hostname),
            ("smb.share_name", settings.smb_share_name),
            ("smb.username", settings.smb_username),
        ]
        if not value
    ]
    if missing:
        logger.error("Missing config: %s", ", ".join(missing))
        return 1

    root = PurePosixPath(settings.library_root)
    logger.info(
        "Connecting to //%s/%s as %s …",
        settings.smb_hostname,
        settings.smb_share_name,
        settings.smb_username,
    )

    repository = SmbFileRepository(SmbConfig.from_settings(settings))
    try:
        entries = repository.list_files_and_directories(root)
    except Exception:
        logger.exception("SMB spike failed")
        return 1
    finally:
        repository.disconnect()

    logger.info("Listed %d entries under /%s:", len(entries), root.as_posix().strip("/"))
    for entry in sorted(entries, key=lambda item: item.name.lower()):
        kind = "dir" if entry.is_directory else "file"
        logger.info("  [%s] %s", kind, entry.name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
