from __future__ import annotations

import logging
from typing import Any


def configure_logging(level_name: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("evosmash")
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        rendered = str(value).replace('"', "'")
        if any(char.isspace() for char in rendered):
            rendered = f'"{rendered}"'
        parts.append(f"{key}={rendered}")
    logger.info(" ".join(parts))
