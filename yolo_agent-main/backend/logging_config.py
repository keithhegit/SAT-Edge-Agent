from __future__ import annotations

import logging
from logging import FileHandler, Formatter, StreamHandler
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "log"
LOG_FILE = LOG_DIR / "backend.log"
_CONFIGURED = False


def setup_backend_logging() -> Path:
    global _CONFIGURED

    if _CONFIGURED:
        return LOG_FILE

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    has_stream_handler = any(
        isinstance(handler, StreamHandler) and not isinstance(handler, FileHandler)
        for handler in root_logger.handlers
    )
    has_file_handler = any(
        isinstance(handler, FileHandler) and Path(handler.baseFilename) == LOG_FILE
        for handler in root_logger.handlers
    )

    if not has_stream_handler:
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    if not has_file_handler:
        file_handler = FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _CONFIGURED = True
    return LOG_FILE
