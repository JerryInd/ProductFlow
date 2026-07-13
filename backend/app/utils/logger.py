import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.config import LOGS_DIR, LOG_LEVEL

class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            record.msg = record.msg.encode("utf-8", errors="replace").decode("utf-8")
            super().emit(record)
        except Exception:
            self.handleError(record)

def setup_logger(name: str = "productflow") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stdout = UTF8StreamHandler(sys.stdout)
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
