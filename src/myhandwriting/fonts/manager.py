"""Font manager - handles listing, loading, and deleting user fonts."""

from pathlib import Path
from typing import Optional

from myhandwriting.appdata import get_fonts_dir


class FontManager:
    """Manages user-created handwriting fonts."""

    def __init__(self):
        self._fonts_dir = get_fonts_dir()

    @property
    def fonts_dir(self) -> Path:
        return self._fonts_dir

    def list_fonts(self) -> list[dict]:
        """List all available user fonts.

        Returns a list of dicts with keys: name, path, filename
        Looks for .json glyph data files (primary) or .ttf files.
        """
        fonts = []
        seen_names = set()

        # Check for glyph data files (bitmap-based fonts)
        for json_file in sorted(self._fonts_dir.glob("*.json")):
            # Skip metadata files
            if json_file.name.endswith(".meta.json"):
                continue
            name = json_file.stem
            seen_names.add(name)
            fonts.append({
                "name": name,
                "path": json_file,
                "filename": json_file.name,
            })

        # Also check for .ttf files not covered by json
        for ttf_file in sorted(self._fonts_dir.glob("*.ttf")):
            if ttf_file.stem not in seen_names:
                fonts.append({
                    "name": ttf_file.stem,
                    "path": ttf_file,
                    "filename": ttf_file.name,
                })

        return fonts

    def get_font_path(self, name: str) -> Optional[Path]:
        """Get the full path to a font by name."""
        path = self._fonts_dir / f"{name}.ttf"
        if path.exists():
            return path
        return None

    def delete_font(self, name: str) -> bool:
        """Delete a user font by name. Returns True if deleted."""
        import shutil
        deleted = False
        # Delete .ttf
        path = self._fonts_dir / f"{name}.ttf"
        if path.exists():
            path.unlink()
            deleted = True
        # Delete glyph data
        data_path = self._fonts_dir / f"{name}.json"
        if data_path.exists():
            data_path.unlink()
            deleted = True
        # Delete metadata
        meta_path = self._fonts_dir / f"{name}.meta.json"
        if meta_path.exists():
            meta_path.unlink()
        # Delete glyph images
        img_dir = self._fonts_dir / f"{name}_glyphs"
        if img_dir.exists():
            shutil.rmtree(img_dir)
        return deleted

    def font_exists(self, name: str) -> bool:
        """Check if a font with the given name exists."""
        return (self._fonts_dir / f"{name}.json").exists() or (self._fonts_dir / f"{name}.ttf").exists()

    def save_glyph_data(self, name: str, glyphs: dict):
        """Save glyph path data as JSON for future editing."""
        import json
        data_path = self._fonts_dir / f"{name}.json"
        data_path.write_text(json.dumps(glyphs, indent=2))

    def load_glyph_data(self, name: str) -> Optional[dict]:
        """Load previously saved glyph path data."""
        import json
        data_path = self._fonts_dir / f"{name}.json"
        if data_path.exists():
            return json.loads(data_path.read_text())
        return None

    def save_metadata(self, name: str, metadata: dict):
        """Save font metadata (brush settings per char, image mappings).

        Metadata structure:
        {
            "font_name": "MyFont",
            "chars": {
                "A": {
                    "brush_size": 12,
                    "brush_style": "blue-ball-pen",
                    "image": "65.png"
                },
                ...
            }
        }
        """
        import json
        meta_path = self._fonts_dir / f"{name}.meta.json"
        meta_path.write_text(json.dumps(metadata, indent=2))

    def load_metadata(self, name: str) -> Optional[dict]:
        """Load font metadata."""
        import json
        meta_path = self._fonts_dir / f"{name}.meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())
        return None

    def get_glyphs_image_dir(self, name: str) -> Path:
        """Get/create the directory for a font's character bitmap images."""
        img_dir = self._fonts_dir / f"{name}_glyphs"
        img_dir.mkdir(parents=True, exist_ok=True)
        return img_dir

    def get_glyph_image_path(self, font_name: str, char: str) -> Optional[Path]:
        """Get the path to a character's bitmap image if it exists."""
        img_dir = self._fonts_dir / f"{font_name}_glyphs"
        # Use ordinal as filename to avoid filesystem issues with special chars
        img_path = img_dir / f"{ord(char)}.png"
        if img_path.exists():
            return img_path
        return None
