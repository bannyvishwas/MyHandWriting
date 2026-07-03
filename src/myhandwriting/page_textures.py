"""Page texture management - scans directories for texture images."""

from pathlib import Path
from shutil import copy2

from PyQt6.QtGui import QImage

from myhandwriting.appdata import get_app_data_dir
from myhandwriting.resources import RESOURCES_DIR


# Default textures directory (shipped with app)
DEFAULT_TEXTURES_DIR = RESOURCES_DIR / "textures"

# Valid image extensions for textures
VALID_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def get_custom_textures_dir() -> Path:
    """Get user's custom page textures directory."""
    textures_dir = get_app_data_dir() / "page_textures"
    textures_dir.mkdir(parents=True, exist_ok=True)
    return textures_dir


def _scan_directory(directory: Path) -> list[dict]:
    """Scan a directory for valid texture image files."""
    textures = []
    if not directory.exists():
        return textures
    for f in sorted(directory.iterdir()):
        if f.suffix.lower() in VALID_EXTENSIONS:
            # Use filename (without extension) as display name, title-cased
            name = f.stem.replace("-", " ").replace("_", " ").title()
            textures.append({"name": name, "path": f})
    return textures


def list_default_textures() -> list[dict]:
    """List built-in page textures by scanning the resources/textures directory."""
    return _scan_directory(DEFAULT_TEXTURES_DIR)


def list_custom_textures() -> list[dict]:
    """List user-imported custom page textures."""
    return _scan_directory(get_custom_textures_dir())


def list_all_textures() -> list[dict]:
    """List all textures: virtual options + default + custom."""
    all_textures = [
        {"name": "None", "path": None},
        {"name": "Plain White", "path": "plain_white"},
    ]
    all_textures.extend(list_default_textures())
    all_textures.extend(list_custom_textures())
    return all_textures


def import_custom_texture(source_path: Path) -> tuple[bool, str]:
    """Import a custom page texture image."""
    if not source_path.exists():
        return False, "File does not exist."

    if source_path.suffix.lower() not in VALID_EXTENSIONS:
        return False, "Only PNG and JPG files are supported."

    img = QImage(str(source_path))
    if img.isNull():
        return False, "Could not load image."

    dest = get_custom_textures_dir() / source_path.name
    if dest.exists():
        return False, f"A texture named '{source_path.stem}' already exists."

    copy2(source_path, dest)
    return True, f"Texture '{source_path.stem}' imported successfully."
