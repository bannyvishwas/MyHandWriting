"""Font generator - converts QPainterPath glyphs into a .ttf font file."""

from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


# Full character set matching the old app
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.?{}()-_+=*&^%@<>|/'\"\\;:"

# Units per em - standard for TrueType fonts
UNITS_PER_EM = 1000

# Default glyph metrics
ASCENDER = 800
DESCENDER = -200
CAP_HEIGHT = 700
X_HEIGHT = 500

# Canvas dimensions used in the drawing widget
CANVAS_WIDTH = 200
CANVAS_HEIGHT = 300


class FontGenerator:
    """Generates .ttf font files from drawn glyph paths."""

    def __init__(self, font_name: str):
        self.font_name = font_name
        self._glyphs: dict[str, list[tuple]] = {}  # char -> list of path commands

    @property
    def charset(self) -> str:
        return CHARSET

    @property
    def total_chars(self) -> int:
        return len(CHARSET)

    @property
    def drawn_chars(self) -> int:
        return len(self._glyphs)

    def has_glyph(self, char: str) -> bool:
        """Check if a glyph has been drawn for a character."""
        return char in self._glyphs

    def set_glyph_paths(self, char: str, path_data: list[tuple]):
        """Store path data for a character.

        path_data is a list of path commands:
            [("moveTo", (x, y)), ("lineTo", (x, y)), ("close",)]
        """
        self._glyphs[char] = path_data

    def remove_glyph(self, char: str):
        """Remove a drawn glyph."""
        self._glyphs.pop(char, None)

    def generate(self, output_path: Path) -> Path:
        """Generate a .ttf font file from all stored glyphs.

        Characters without glyphs will get a placeholder glyph.
        """
        glyph_names = [".notdef", "space"] + [f"uni{ord(c):04X}" for c in CHARSET]

        fb = FontBuilder(UNITS_PER_EM, isTTF=True)
        fb.setupGlyphOrder(glyph_names)
        fb.setupCharacterMap({
            ord(" "): "space",
            **{ord(c): f"uni{ord(c):04X}" for c in CHARSET},
        })

        # Build glyph objects using TTGlyphPen
        glyph_table = {}

        # .notdef - empty
        pen = TTGlyphPen(None)
        glyph_table[".notdef"] = pen.glyph()

        # space - empty
        pen = TTGlyphPen(None)
        glyph_table["space"] = pen.glyph()

        # Character glyphs
        for char in CHARSET:
            glyph_name = f"uni{ord(char):04X}"
            if char in self._glyphs and self._glyphs[char]:
                glyph_table[glyph_name] = self._build_glyph(self._glyphs[char])
            else:
                glyph_table[glyph_name] = self._build_placeholder()

        fb.setupGlyf(glyph_table)

        # Metrics
        advance_width = 600
        metrics = {name: (advance_width, 0) for name in glyph_names}
        fb.setupHorizontalMetrics(metrics)

        fb.setupHorizontalHeader(ascent=ASCENDER, descent=DESCENDER)
        fb.setupNameTable({
            "familyName": self.font_name,
            "styleName": "Regular",
        })
        fb.setupOS2(
            sTypoAscender=ASCENDER,
            sTypoDescender=DESCENDER,
            sCapHeight=CAP_HEIGHT,
            sxHeight=X_HEIGHT,
        )
        fb.setupPost()

        # Save
        output_path = output_path.with_suffix(".ttf")
        fb.font.save(str(output_path))
        return output_path

    def _build_glyph(self, path_data: list[tuple]):
        """Convert path commands to a TTGlyph via TTGlyphPen."""
        pen = TTGlyphPen(None)
        scale_x = UNITS_PER_EM / CANVAS_WIDTH
        scale_y = UNITS_PER_EM / CANVAS_HEIGHT

        for cmd in path_data:
            if cmd[0] == "moveTo":
                x, y = cmd[1]
                fx = int(x * scale_x)
                fy = int((CANVAS_HEIGHT - y) * scale_y) + DESCENDER
                pen.moveTo((fx, fy))
            elif cmd[0] == "lineTo":
                x, y = cmd[1]
                fx = int(x * scale_x)
                fy = int((CANVAS_HEIGHT - y) * scale_y) + DESCENDER
                pen.lineTo((fx, fy))
            elif cmd[0] == "close":
                pen.closePath()
            elif cmd[0] == "endPath":
                pen.endPath()

        return pen.glyph()

    def _build_placeholder(self):
        """Build a simple square placeholder glyph."""
        pen = TTGlyphPen(None)
        margin = 100
        top = ASCENDER - margin
        bottom = DESCENDER + margin
        left = margin
        right = 500

        pen.moveTo((left, bottom))
        pen.lineTo((right, bottom))
        pen.lineTo((right, top))
        pen.lineTo((left, top))
        pen.closePath()

        return pen.glyph()
