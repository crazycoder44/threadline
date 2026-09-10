"""Logging configuration shared by the project's execution phases."""
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_ROOT = Path(os.environ.get("LOG_ROOT", "logs"))
PHASE_ROOT = LOG_ROOT / "metacrawler"
JOBS_ROOT = PHASE_ROOT / "jobs"
MAIN_LOG = PHASE_ROOT / "metacrawler.log"
FUTURE_PHASES = ("processor", "api")
MAX_LOG_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5
JOB_BACKUP_COUNT = 3

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("metacrawler")
    if logger.handlers:
        return logger

    PHASE_ROOT.mkdir(parents=True, exist_ok=True)
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    for phase in FUTURE_PHASES:
        (LOG_ROOT / phase).mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)
    file_handler = RotatingFileHandler(
        MAIN_LOG,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def get_logger() -> logging.Logger:
    return configure_logging()


def get_job_logger(source_type: str, target_id: str) -> logging.Logger:
    configure_logging()
    safe_source = _safe_filename(source_type)
    safe_target = _safe_filename(target_id)
    logger = logging.getLogger(f"metacrawler.job.{safe_source}.{safe_target}")
    logger.setLevel(logging.INFO)
    logger.propagate = True

    if not logger.handlers:
        formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)
        handler = RotatingFileHandler(
            JOBS_ROOT / f"{safe_source}_{safe_target}.log",
            maxBytes=MAX_LOG_BYTES,
            backupCount=JOB_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _safe_filename(value: str) -> str:
    safe_value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    return safe_value[:120] or "unknown"