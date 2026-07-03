"""Application settings management - JSON-based configuration."""

import json
from pathlib import Path
from typing import Any

from myhandwriting.appdata import get_config_dir


SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "editor": {
        "default_font_size": 14,
        "default_font": "System Default",
        "theme": "system",
        "page_texture": "Texture",
        "page_style": "Plain",
        "page_style_size": 30,
        "margin_horizontal": 40,
        "margin_vertical": 30,
        "red_line_position": 100,
        "line_thickness": 1,
    },
    "canvas": {
        "default_brush": "black-ball-pen",
        "default_brush_size": 40,
    },
    "export": {
        "format": "pdf",
        "paper_size": "a4",
        "margin": 50,
    },
    "app": {
        "window_width": 900,
        "window_height": 600,
        "last_opened_file": None,
        "recent_files": [],
    },
}


class Settings:
    """Manages application settings stored as JSON."""

    def __init__(self):
        self._config_dir = get_config_dir()
        self._file_path = self._config_dir / SETTINGS_FILE
        self._data: dict = {}
        self._load()

    @property
    def file_path(self) -> Path:
        return self._file_path

    def _load(self):
        """Load settings from file, or create default if not exists."""
        if self._file_path.exists():
            try:
                self._data = json.loads(self._file_path.read_text())
                # Merge with defaults to pick up any new keys added in updates
                self._data = self._merge_defaults(DEFAULT_SETTINGS, self._data)
            except (json.JSONDecodeError, ValueError):
                # Corrupted file — reset to defaults
                self._data = DEFAULT_SETTINGS.copy()
                self._save()
        else:
            self._data = DEFAULT_SETTINGS.copy()
            self._save()

    def _merge_defaults(self, defaults: dict, current: dict) -> dict:
        """Recursively merge defaults with current settings.

        Adds any missing keys from defaults without overwriting existing user values.
        """
        merged = defaults.copy()
        for key, value in current.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_defaults(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _save(self):
        """Save current settings to file."""
        self._file_path.write_text(json.dumps(self._data, indent=2))

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a setting value by section and key.

        Example: settings.get("editor", "theme")
        """
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any):
        """Set a setting value and persist to disk.

        Example: settings.set("editor", "theme", "dark")
        """
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value
        self._save()

    def get_section(self, section: str) -> dict:
        """Get an entire settings section as a dict."""
        return self._data.get(section, {})

    def set_section(self, section: str, data: dict):
        """Set an entire settings section and persist."""
        self._data[section] = data
        self._save()

    def reset(self):
        """Reset all settings to defaults."""
        self._data = DEFAULT_SETTINGS.copy()
        self._save()

    @property
    def all(self) -> dict:
        """Get all settings as a dict (read-only copy)."""
        return self._data.copy()
