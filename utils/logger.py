"""Centralized application logging."""

import logging
from pathlib import Path

_LOG_FILE = Path(__file__).resolve().parent.parent / "app.log"


def get_logger(name="fraud_detection"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    try:
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass
    logger.propagate = False
    return logger
