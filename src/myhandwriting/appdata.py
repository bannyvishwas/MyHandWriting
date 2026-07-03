"""Application data directory management - OS-aware."""

import platform
import sys
from pathlib import Path

APP_NAME = "MyHandWriting"


def get_app_data_dir() -> Path:
    """Get the application data directory based on the OS.

    Returns:
        macOS:   ~/Library/Application Support/MyHandWriting/
        Linux:   ~/.local/share/MyHandWriting/
        Windows: %LOCALAPPDATA%/MyHandWriting/
    """
    system = platform.system()

    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Linux":
        xdg = Path(environ.get("XDG_DATA_HOME", "")) if "XDG_DATA_HOME" in environ else None
        base = xdg if xdg else Path.home() / ".local" / "share"
    elif system == "Windows":
        local_app_data = Path(environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        base = local_app_data
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_fonts_dir() -> Path:
    """Get the directory where user-created fonts are stored."""
    fonts_dir = get_app_data_dir() / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    return fonts_dir


def get_config_dir() -> Path:
    """Get the directory for app configuration files."""
    config_dir = get_app_data_dir() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# Need os.environ for Linux XDG
from os import environ
