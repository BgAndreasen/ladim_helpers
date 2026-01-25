from __future__ import annotations

import logging
import shutil
from pathlib import Path


def publish_file(
    src: Path,
    publish_dir: Path,
    logger: logging.Logger | None = None,
    keep_temp: bool = False,
) -> Path:
    """
    Copy src into publish_dir unless it's already there.
    If copied and keep_temp=False, delete src.
    Returns the published path.

    Safe when output_dir == publish_dir (no-op).
    """
    src = Path(src).resolve()
    publish_dir = Path(publish_dir).resolve()
    publish_dir.mkdir(parents=True, exist_ok=True)

    dst = (publish_dir / src.name).resolve()

    def log(msg: str):
        if logger:
            logger.info(msg)

    if src == dst:
        log(f"Publish skipped (same path): {src}")
        return src

    shutil.copy2(src, dst)
    log(f"Published {src} -> {dst}")

    if not keep_temp:
        try:
            src.unlink()
            log(f"Deleted temp file: {src}")
        except Exception as e:
            if logger:
                logger.exception("Could not delete temp file %s: %s", src, e)

    return dst
