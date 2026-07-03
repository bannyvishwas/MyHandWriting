"""PDF export - renders all pages to a PDF file using the page format settings."""

from pathlib import Path

from PyQt6.QtCore import Qt, QMarginsF, QRectF, QSizeF
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPageLayout, QPageSize, QPixmap
from PyQt6.QtWidgets import QApplication

from myhandwriting.fonts.manager import FontManager
from myhandwriting.settings import Settings
from myhandwriting.page_textures import list_all_textures


# Page sizes in points (72 DPI for PDF)
PAGE_SIZES_PT = {
    "a4": QPageSize.PageSizeId.A4,
    "letter": QPageSize.PageSizeId.Letter,
    "a3": QPageSize.PageSizeId.A3,
    "a5": QPageSize.PageSizeId.A5,
}

# Page sizes in pixels at 96 DPI (matching editor)
PAGE_SIZES_PX = {
    "a4": (794, 1123),
    "letter": (816, 1056),
    "a3": (1123, 1587),
    "a5": (559, 794),
}


def export_to_pdf(pages_data: list, settings: Settings, output_path: Path) -> bool:
    """Export all pages to a PDF file.

    Args:
        pages_data: List of PageData objects from the file format
        settings: Application settings for page format
        output_path: Where to save the PDF

    Returns:
        True if export succeeded
    """
    from PyQt6.QtGui import QPdfWriter

    paper_size = settings.get("export", "paper_size", "a4")
    margin_h = settings.get("editor", "margin_horizontal", 40)
    margin_v = settings.get("editor", "margin_vertical", 30)
    page_style = settings.get("editor", "page_style", "Plain")
    line_thickness = settings.get("editor", "line_thickness", 1)
    red_line_pos = settings.get("editor", "red_line_position", 100)
    font_size = settings.get("editor", "default_font_size", 14)
    page_texture_name = settings.get("editor", "page_texture", "Texture")

    # Get page size
    page_size_id = PAGE_SIZES_PT.get(paper_size, QPageSize.PageSizeId.A4)
    page_w_px, page_h_px = PAGE_SIZES_PX.get(paper_size, PAGE_SIZES_PX["a4"])

    # Set up PDF writer
    writer = QPdfWriter(str(output_path))
    writer.setPageSize(QPageSize(page_size_id))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))  # We handle margins ourselves
    writer.setResolution(96)  # Match our pixel-based layout

    painter = QPainter(writer)
    pdf_w = writer.width()
    pdf_h = writer.height()

    # Load texture
    texture_pixmap = _load_texture(page_texture_name)

    # Font manager for glyph images
    manager = FontManager()

    # Line spacing from font size
    glyph_height = font_size * 1.8
    spacing = int(glyph_height)
    baseline_offset = int(glyph_height * 0.66)

    for page_idx, page_data in enumerate(pages_data):
        if page_idx > 0:
            writer.newPage()

        # 1. Draw page texture background
        if texture_pixmap and not texture_pixmap.isNull():
            scaled = texture_pixmap.scaled(pdf_w, pdf_h,
                                           Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)
        else:
            painter.fillRect(0, 0, pdf_w, pdf_h, QColor("#ffffff"))

        # 2. Draw page style (lines/grid)
        _draw_page_style(painter, pdf_w, pdf_h, page_style, spacing,
                         baseline_offset, margin_v, line_thickness, red_line_pos)

        # 3. Draw text content (glyph images positioned on the page)
        _draw_page_content(painter, page_data, manager, margin_h, margin_v,
                           pdf_w, glyph_height)

    painter.end()
    return True


def _load_texture(texture_name: str):
    """Load the page texture pixmap by name."""
    if texture_name in ("None", "Plain White"):
        return None

    textures = list_all_textures()
    for t in textures:
        if t["name"] == texture_name and t["path"] and t["path"] != "plain_white":
            return QPixmap(str(t["path"]))
    return None


def _draw_page_style(painter: QPainter, width: int, height: int, style: str,
                     spacing: int, baseline_offset: int, margin_v: int,
                     line_thickness: int, red_line_pos: int):
    """Draw lines/grid on a PDF page."""
    if style == "Plain":
        return

    line_color = QColor(180, 210, 240, 140)
    margin_color = QColor(240, 120, 120, 120)

    if style in ("Lined", "Ruled"):
        pen = QPen(line_color, line_thickness)
        painter.setPen(pen)
        y = margin_v + baseline_offset
        while y < height:
            painter.drawLine(0, y, width, y)
            y += spacing

        if style == "Ruled":
            pen = QPen(margin_color, line_thickness)
            painter.setPen(pen)
            painter.drawLine(red_line_pos, 0, red_line_pos, height)

    elif style == "Grid":
        pen = QPen(line_color, line_thickness)
        painter.setPen(pen)
        y = margin_v + baseline_offset
        while y < height:
            painter.drawLine(0, y, width, y)
            y += spacing
        x = spacing
        while x < width:
            painter.drawLine(x, 0, x, height)
            x += spacing


def _draw_page_content(painter: QPainter, page_data, manager: FontManager,
                       margin_h: int, margin_v: int, page_width: int,
                       glyph_height: float):
    """Draw the text content (glyph images) on a PDF page."""
    x = margin_h
    y = margin_v
    content_width = page_width - (margin_h * 2)

    for line in page_data.lines:
        for span in line.spans:
            is_user_font = span.font_style != "system_default"
            img_height = int(span.font_size * 1.8)

            for char in span.text:
                if char == ' ':
                    # Space: advance by half glyph width
                    space_width = int(img_height * 0.4)
                    x += space_width
                    if x > margin_h + content_width:
                        x = margin_h
                        y += int(glyph_height)
                    continue

                if is_user_font:
                    img_path = manager.get_glyph_image_path(span.font_style, char)
                    if img_path:
                        img = QImage(str(img_path))
                        if not img.isNull():
                            scale_factor = img_height / img.height()
                            img_width = int(img.width() * scale_factor)

                            # Word wrap: if char doesn't fit, go to next line
                            if x + img_width > margin_h + content_width:
                                x = margin_h
                                y += int(glyph_height)

                            painter.drawImage(QRectF(x, y, img_width, img_height), img,
                                              QRectF(0, 0, img.width(), img.height()))
                            x += img_width
                            continue

                # Fallback: draw as text character
                painter.setPen(QColor("#000000"))
                from PyQt6.QtGui import QFont
                painter.setFont(QFont("Courier New", span.font_size))
                char_width = int(span.font_size * 0.7)
                if x + char_width > margin_h + content_width:
                    x = margin_h
                    y += int(glyph_height)
                painter.drawText(int(x), int(y + img_height * 0.7), char)
                x += char_width

        # End of line — move to next line
        x = margin_h
        y += int(glyph_height)
