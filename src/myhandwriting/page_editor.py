"""Multi-page editor with computed rows/columns and page break management."""

import math
from pathlib import Path

from PyQt6.QtCore import Qt, QRectF, QSizeF, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPaintEvent, QKeyEvent, QTextFrameFormat
from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QScrollArea, QFrame

from myhandwriting.settings import Settings


# Visual gap between pages
PAGE_GAP = 20


class SinglePage(QTextEdit):
    """A single page widget with texture background and line/grid overlay."""

    # Emitted when this page is full and content should flow to next page
    page_overflow = pyqtSignal()
    # Emitted when backspace at start should merge with previous page
    merge_previous = pyqtSignal()

    def __init__(self, settings: Settings, page_width: int, page_height: int, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._page_width = page_width
        self._page_height = page_height
        self._texture_pixmap: QPixmap | None = None
        self._plain_white = True

        self.setFixedSize(page_width, page_height)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Apply margins
        self.document().setDocumentMargin(0)
        margin_h = settings.get("editor", "margin_horizontal", 40)
        margin_v = settings.get("editor", "margin_vertical", 30)
        root_frame = self.document().rootFrame()
        frame_fmt = root_frame.frameFormat()
        frame_fmt.setLeftMargin(margin_h)
        frame_fmt.setRightMargin(margin_h)
        frame_fmt.setTopMargin(margin_v)
        frame_fmt.setBottomMargin(margin_v)
        root_frame.setFrameFormat(frame_fmt)

    def set_page_texture(self, texture_path: str | None):
        """Set the page background texture."""
        if texture_path == "plain_white":
            self._texture_pixmap = None
            self._plain_white = True
        elif texture_path:
            img = QImage(str(texture_path))
            if not img.isNull():
                self._texture_pixmap = QPixmap.fromImage(img)
            else:
                self._texture_pixmap = None
            self._plain_white = False
        else:
            self._texture_pixmap = None
            self._plain_white = False
        self.viewport().update()

    def get_max_rows(self) -> int:
        """Calculate maximum rows this page can hold."""
        margin_v = self._settings.get("editor", "margin_vertical", 30)
        font_size = self._settings.get("editor", "default_font_size", 14)
        row_height = font_size * 1.8
        content_height = self._page_height - (margin_v * 2)
        return max(1, int(content_height / row_height))

    def is_full(self) -> bool:
        """Check if the page content has exceeded its capacity."""
        doc_height = self.document().size().height()
        return doc_height > self._page_height

    def paintEvent(self, event: QPaintEvent):
        """Draw texture background, then text, then line overlay."""
        painter = QPainter(self.viewport())
        vp_rect = self.viewport().rect()
        vp_w = vp_rect.width()
        vp_h = vp_rect.height()

        # Background
        if self._texture_pixmap and not self._texture_pixmap.isNull():
            scaled = self._texture_pixmap.scaled(
                vp_w, vp_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        elif self._plain_white:
            painter.fillRect(vp_rect, QColor("#ffffff"))

        painter.end()

        # Text
        super().paintEvent(event)

        # Line/Grid overlay
        self._draw_style_overlay()

    def _draw_style_overlay(self):
        """Draw lines or grid on this page."""
        style = self._settings.get("editor", "page_style", "Plain")
        if style == "Plain":
            return

        font_size = self._settings.get("editor", "default_font_size", 14)
        glyph_height = font_size * 1.8
        spacing = int(glyph_height)
        baseline_offset = int(glyph_height * 0.66)
        if spacing < 5:
            spacing = 25
            baseline_offset = 16

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        vp_rect = self.viewport().rect()
        width = vp_rect.width()
        height = vp_rect.height()

        line_color = QColor(180, 210, 240, 140)
        margin_color = QColor(240, 120, 120, 120)
        line_thickness = self._settings.get("editor", "line_thickness", 1)
        margin_v = self._settings.get("editor", "margin_vertical", 30)

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
                red_pos = self._settings.get("editor", "red_line_position",
                                             self._settings.get("editor", "margin_horizontal", 40))
                painter.drawLine(red_pos, 0, red_pos, height)

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

        painter.end()


class PageManager(QWidget):
    """Manages multiple page widgets stacked vertically with page breaks."""

    # Emitted when cursor moves (for status bar updates)
    cursor_moved = pyqtSignal()
    text_changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._pages: list[SinglePage] = []
        self._active_page_index = 0
        self._event_filter = None

        # Page dimensions
        self._page_width = 794
        self._page_height = 1123
        self._texture_path: str | None = "plain_white"

        # Layout
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(PAGE_GAP)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Create first page
        self._add_new_page()

    @property
    def active_page(self) -> SinglePage:
        """Get the currently active page."""
        if 0 <= self._active_page_index < len(self._pages):
            return self._pages[self._active_page_index]
        return self._pages[0]

    @property
    def editor(self) -> SinglePage:
        """Alias for active page (compatibility with app.py)."""
        return self.active_page

    def set_page_size(self, width: int, height: int):
        """Set page dimensions for all pages."""
        self._page_width = width
        self._page_height = height
        for page in self._pages:
            page.setFixedSize(width, height)
            # Re-apply margins
            margin_h = self._settings.get("editor", "margin_horizontal", 40)
            margin_v = self._settings.get("editor", "margin_vertical", 30)
            page.document().setDocumentMargin(0)
            root_frame = page.document().rootFrame()
            frame_fmt = root_frame.frameFormat()
            frame_fmt.setLeftMargin(margin_h)
            frame_fmt.setRightMargin(margin_h)
            frame_fmt.setTopMargin(margin_v)
            frame_fmt.setBottomMargin(margin_v)
            root_frame.setFrameFormat(frame_fmt)

    def set_page_texture(self, texture_path: str | None):
        """Set texture for all pages."""
        self._texture_path = texture_path
        for page in self._pages:
            page.set_page_texture(texture_path)

    def get_current_page(self) -> int:
        """Get the current page number (1-based)."""
        return self._active_page_index + 1

    def get_total_pages(self) -> int:
        """Get total number of pages."""
        return len(self._pages)

    def clear(self):
        """Clear all content and reset to single page."""
        while len(self._pages) > 1:
            page = self._pages.pop()
            self._layout.removeWidget(page)
            page.deleteLater()
        self._pages[0].clear()
        self._active_page_index = 0

    def remove_page(self, page_index: int):
        """Remove a page by index (0-based). Cannot remove page 0."""
        if page_index <= 0 or page_index >= len(self._pages):
            return

        page = self._pages.pop(page_index)
        self._layout.removeWidget(page)
        page.deleteLater()

        # Adjust active page index
        if self._active_page_index >= len(self._pages):
            self._active_page_index = len(self._pages) - 1

        # Focus the previous page
        if self._pages:
            self._pages[self._active_page_index].setFocus()

    def installEventFilter(self, filter_obj):
        """Install event filter on all pages."""
        self._event_filter = filter_obj
        super().installEventFilter(filter_obj)
        for page in self._pages:
            page.installEventFilter(filter_obj)

    def _add_new_page(self) -> SinglePage:
        """Create and add a new page widget."""
        page = SinglePage(self._settings, self._page_width, self._page_height)
        page.set_page_texture(self._texture_path)

        # Style the page
        border_color = "#999999"
        page.setStyleSheet(f"""
            QTextEdit {{
                font-family: 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid {border_color};
                background: transparent;
                color: #000000;
            }}
        """)

        # Connect signals
        page.textChanged.connect(self._on_text_changed)
        page.cursorPositionChanged.connect(self._on_cursor_moved)
        page.selectionChanged.connect(self.selection_changed.emit)

        # Track focus to update active page
        page.focusInEvent = lambda e, p=page: self._on_page_focused(p, e)

        self._pages.append(page)
        self._layout.addWidget(page, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Install event filter on new page if one was set
        if self._event_filter:
            page.installEventFilter(self._event_filter)

        return page

    def _on_page_focused(self, page: SinglePage, event):
        """Track which page is active."""
        self._active_page_index = self._pages.index(page)
        QTextEdit.focusInEvent(page, event)

    def _on_text_changed(self):
        """Check if the active page overflowed and create new page if needed."""
        self.text_changed.emit()

        # Check if current page is full
        active = self.active_page
        if active.is_full():
            # Get overflow text from the end
            doc = active.document()
            cursor = active.textCursor()

            # Move cursor to end to check if content overflows
            # Create next page if it doesn't exist
            if self._active_page_index == len(self._pages) - 1:
                new_page = self._add_new_page()

                # Apply current font settings from the previous page to new page
                prev_page = self._pages[self._active_page_index]
                current_fmt = prev_page.currentCharFormat()
                new_page.setCurrentCharFormat(current_fmt)

                # Also set the document default font to match
                doc_font = prev_page.document().defaultFont()
                new_page.document().setDefaultFont(doc_font)

                # Focus moves to new page
                new_page.setFocus()
                self._active_page_index = len(self._pages) - 1

    def _on_cursor_moved(self):
        """Emit cursor_moved signal."""
        self.cursor_moved.emit()

    # --- Compatibility methods (used by app.py) ---

    def textCursor(self):
        return self.active_page.textCursor()

    def setTextCursor(self, cursor):
        self.active_page.setTextCursor(cursor)

    def toPlainText(self) -> str:
        """Get all text from all pages."""
        texts = []
        for page in self._pages:
            texts.append(page.toPlainText())
        return "\n".join(texts)

    def document(self):
        return self.active_page.document()

    def setAlignment(self, alignment):
        self.active_page.setAlignment(alignment)

    def mergeCurrentCharFormat(self, fmt):
        self.active_page.mergeCurrentCharFormat(fmt)

    def cursorRect(self, cursor=None):
        if cursor:
            return self.active_page.cursorRect(cursor)
        return self.active_page.cursorRect()

    def verticalScrollBar(self):
        return self.active_page.verticalScrollBar()

    def viewport(self):
        return self.active_page.viewport()

    def setStyleSheet(self, style):
        """Apply stylesheet to all pages."""
        for page in self._pages:
            page.setStyleSheet(style)

    def setFixedWidth(self, width):
        """Set width for all pages."""
        for page in self._pages:
            page.setFixedWidth(width)
