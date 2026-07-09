"""Logging utilities for the public tool API server."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


MAX_LOG_LENGTH = 500
MAX_FILE_LOG_LENGTH = 2000


class TruncatingFormatter(logging.Formatter):
    """Formatter that truncates long log records."""

    def __init__(self, fmt=None, datefmt=None, max_length=500):
        super().__init__(fmt, datefmt)
        self.max_length = max_length

    def format(self, record):
        """Format a record and truncate overly long output."""
        formatted = super().format(record)

        if len(formatted) > self.max_length:
            truncated = formatted[:self.max_length]
            if truncated.rfind('\n') > self.max_length - 100:
                truncated = truncated[:truncated.rfind('\n')]
            formatted = truncated + f"... [truncated, original length: {len(formatted)}]"

        return formatted


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Create a logger with console and optional rotating-file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()

    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = TruncatingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            max_length=MAX_LOG_LENGTH,
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    if file_output:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        if log_file is None:
            log_file = log_dir / f"{name}.log"
        else:
            log_file = Path(log_file)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_format = TruncatingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            max_length=MAX_FILE_LOG_LENGTH,
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return an existing logger or initialize a default one."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


def truncate_text(text: str, max_length: int = MAX_LOG_LENGTH) -> str:
    """Truncate text to a maximum character length."""
    if len(text) <= max_length:
        return text

    truncated = text[:max_length]
    if "\n" in truncated[-100:]:
        last_newline = truncated.rfind("\n")
        if last_newline > max_length - 200:
            truncated = truncated[:last_newline]

    return truncated + f"... [truncated, original length: {len(text)}]"


def log_data(logger: logging.Logger, level: int, message: str, data: any, max_length: int = MAX_LOG_LENGTH):
    """Log structured data after applying the configured length limit."""
    data_str = str(data)
    truncated_data = truncate_text(data_str, max_length)
    full_message = f"{message}: {truncated_data}"
    logger.log(level, full_message)


server_logger = None
tool_logger = None


def init_loggers():
    """Initialize shared server and tool-execution loggers."""
    global server_logger, tool_logger

    server_logger = setup_logger(
        name="tool_server",
        log_file=Path("logs") / "server.log",
        level=logging.INFO,
    )

    tool_logger = setup_logger(
        name="tool_execution",
        log_file=Path("logs") / "tool_execution.log",
        level=logging.INFO,
    )

    server_logger.info("Loggers initialized")


init_loggers()
