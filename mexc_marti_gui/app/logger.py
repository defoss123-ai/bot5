import logging
from pathlib import Path
from typing import Optional

_LOGGER: Optional[logging.Logger] = None


def get_logger(name: str = "bot") -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "bot.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    _LOGGER = logger
    return logger
