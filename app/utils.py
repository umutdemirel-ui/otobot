"""Utility helpers for paths, logging, and formatting."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_path(relative_path: str) -> Path:
    """Resolve bundled asset paths for both source runs and PyInstaller builds."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative_path


def get_runtime_dir() -> Path:
    """Return writable directory for settings and logs.

    When packaged as a Windows EXE, prefers the executable's directory if writable,
    falling back to %APPDATA%/SonOyuncuAutoMessageBot.
    """
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        if _is_dir_writable(exe_dir):
            return exe_dir
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home()
        target = base / "SonOyuncuAutoMessageBot"
        target.mkdir(parents=True, exist_ok=True)
        return target

    project_root = Path(__file__).resolve().parent.parent
    return project_root


def _is_dir_writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write_test.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def get_settings_path() -> Path:
    """Return the path to the persistent JSON settings file."""
    data_dir = get_runtime_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "settings.json"


def get_log_path() -> Path:
    """Return the path to the rotating application log file."""
    log_dir = get_runtime_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "otobot.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with file rotation and safe stream output."""
    logger = logging.getLogger("otobot")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        file_handler = RotatingFileHandler(
            get_log_path(),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def format_countdown(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS for UI countdown display."""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
