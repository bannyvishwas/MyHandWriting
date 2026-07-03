"""Brush management - handles default and custom brush styles."""

from pathlib import Path
from shutil import copy2

from PyQt6.QtGui import QImage, QPixmap

from myhandwriting.appdata import get_app_data_dir
from myhandwriting.resources import RESOURCES_DIR


DEFAULT_BRUSHES_DIR = RESOURCES_DIR / "brushes"
MIN_BRUSH_SIZE = 5
MAX_BRUSH_SIZE = 100


def get_custom_brushes_dir() -> Path:
    """Get user's custom brushes directory in app data."""
    brushes_dir = get_app_data_dir() / "brushes"
    brushes_dir.mkdir(parents=True, exist_ok=True)
    return brushes_dir


def list_default_brushes() -> list[dict]:
    """List all built-in brush styles.

    Returns list of dicts: {name, path}
    """
    brushes = []
    for png in sorted(DEFAULT_BRUSHES_DIR.glob("*.png")):
        brushes.append({
            "name": png.stem.replace("-", " ").title(),
            "path": png,
        })
    return brushes


def list_custom_brushes() -> list[dict]:
    """List all user-imported custom brushes.

    Returns list of dicts: {name, path}
    """
    brushes = []
    custom_dir = get_custom_brushes_dir()
    for png in sorted(custom_dir.glob("*.png")):
        brushes.append({
            "name": png.stem.replace("-", " ").title(),
            "path": png,
        })
    return brushes


def list_all_brushes() -> list[dict]:
    """List all brushes (default + custom)."""
    return list_default_brushes() + list_custom_brushes()


def import_custom_brush(source_path: Path) -> tuple[bool, str]:
    """Import a user brush image into the custom brushes directory.

    Validates:
        - File is PNG
        - Image is square
        - Size between MIN_BRUSH_SIZE and MAX_BRUSH_SIZE

    Returns (success, message)
    """
    if not source_path.exists():
        return False, "File does not exist."

    if source_path.suffix.lower() != ".png":
        return False, "Only PNG files are supported."

    img = QImage(str(source_path))
    if img.isNull():
        return False, "Could not load image."

    if img.width() != img.height():
        return False, f"Brush must be square. Got {img.width()}x{img.height()}."

    if img.width() < MIN_BRUSH_SIZE or img.width() > MAX_BRUSH_SIZE:
        return False, f"Brush size must be between {MIN_BRUSH_SIZE}x{MIN_BRUSH_SIZE} and {MAX_BRUSH_SIZE}x{MAX_BRUSH_SIZE}. Got {img.width()}x{img.height()}."

    dest = get_custom_brushes_dir() / source_path.name
    if dest.exists():
        return False, f"A brush named '{source_path.stem}' already exists."

    copy2(source_path, dest)
    return True, f"Brush '{source_path.stem}' imported successfully."


def load_brush_pixmap(brush_path: Path, size: int) -> QPixmap:
    """Load a brush image and scale it to the given size."""
    pixmap = QPixmap(str(brush_path))
    if pixmap.isNull():
        # Fallback: solid circle
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPainter, QColor
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 0, 0, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
    else:
        pixmap = pixmap.scaled(size, size)
    return pixmap
