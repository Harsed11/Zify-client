import logging
import os
from logging.handlers import RotatingFileHandler

from vpn_configurator.core.paths import data_dir

LOG_DIR = data_dir("logs")
LOG_PATH = os.path.join(LOG_DIR, "app.log")
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3

_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

_logger = None


def _get_logger():
    global _logger
    if _logger is not None:
        return _logger
    _logger = logging.getLogger("zifyvpn")
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass
    try:
        handler = RotatingFileHandler(
            LOG_PATH, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        _logger.addHandler(handler)
    except Exception:
        pass
    return _logger


def log(message, level="INFO"):
    lvl = _LEVEL_MAP.get(level, logging.INFO)
    try:
        _get_logger().log(lvl, message)
    except Exception:
        pass
