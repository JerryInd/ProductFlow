import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import LOGS_DIR, LOG_LEVEL

os.environ["PYTHONIOENCODING"] = "utf-8"

def setup_logger(name: str = "productflow") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(fmt)
    logger.addHandler(stdout)

    log_path = Path(LOGS_DIR)
    log_path.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(
        log_path / "productflow.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

logger = setup_logger()
