"""Resource path utilities."""

from pathlib import Path

RESOURCES_DIR = Path(__file__).parent
ICONS_DIR = RESOURCES_DIR / "icons"


def get_resource(filename: str) -> Path:
    """Get the full path to a resource file."""
    return RESOURCES_DIR / filename


def get_icon(filename: str) -> Path:
    """Get the full path to an icon file."""
    return ICONS_DIR / filename
