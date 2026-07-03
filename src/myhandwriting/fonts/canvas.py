"""Drawing canvas widget for creating font glyphs."""

from pathlib import Path

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

from myhandwriting.fonts.brushes import load_brush_pixmap, list_default_brushes


class GlyphCanvas(QWidget):
    """A drawing canvas that captures strokes as QPainterPath data.

    Completed strokes are baked into a buffer image so brush size/style
    changes don't affect previously drawn content.

    The canvas is 400x500 pixels with guide lines for baseline,
    x-height, and cap-height.
    """

    drawing_changed = pyqtSignal()

    CANVAS_WIDTH = 200
    CANVAS_HEIGHT = 300

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)

        # Path data stored for font generation
        self._paths: list[QPainterPath] = []
        self._current_path: QPainterPath | None = None
        self._is_drawing = False

        # Baked buffer for completed strokes (won't change with brush settings)
        self._buffer = QImage(self.CANVAS_WIDTH, self.CANVAS_HEIGHT, QImage.Format.Format_ARGB32)
        self._buffer.fill(QColor(0, 0, 0, 0))

        # Brush settings
        self._brush_size = 40
        self._brush_pixmap: QPixmap | None = None
        self._brush_path: Path | None = None

        # Load default brush
        defaults = list_default_brushes()
        if defaults:
            self.set_brush(defaults[0]["path"])

        self.setMouseTracking(True)

    @property
    def brush_size(self) -> int:
        return self._brush_size

    @brush_size.setter
    def brush_size(self, size: int):
        self._brush_size = max(5, min(100, size))
        if self._brush_path:
            self._brush_pixmap = load_brush_pixmap(self._brush_path, self._brush_size)

    def set_brush(self, brush_path: Path):
        """Set the active brush from a PNG file path."""
        self._brush_path = brush_path
        self._brush_pixmap = load_brush_pixmap(brush_path, self._brush_size)

    def get_buffer_image(self) -> QImage:
        """Get the current baked buffer image (for saving character bitmaps)."""
        return self._buffer.copy()

    def clear(self):
        """Clear all drawn paths and the buffer."""
        self._paths.clear()
        self._current_path = None
        self._buffer.fill(QColor(0, 0, 0, 0))
        self.update()
        self.drawing_changed.emit()

    def load_paths(self, path_data: list[tuple]):
        """Load previously saved path data back onto the canvas.

        Re-renders them into the buffer with the current brush.
        """
        self._paths.clear()
        self._current_path = None
        self._buffer.fill(QColor(0, 0, 0, 0))

        current_path = None
        for cmd in path_data:
            if cmd[0] == "moveTo":
                current_path = QPainterPath()
                current_path.moveTo(QPointF(cmd[1][0], cmd[1][1]))
            elif cmd[0] == "lineTo" and current_path is not None:
                current_path.lineTo(QPointF(cmd[1][0], cmd[1][1]))
            elif cmd[0] == "close":
                if current_path is not None:
                    self._paths.append(current_path)
                    self._bake_path(current_path)
                    current_path = None

        if current_path is not None:
            self._paths.append(current_path)
            self._bake_path(current_path)

        self.update()

    def load_from_image(self, image_path: str):
        """Load a previously saved glyph image directly into the buffer.

        This preserves the original brush texture/size without re-rendering.
        """
        self._paths.clear()
        self._current_path = None
        self._buffer.fill(QColor(0, 0, 0, 0))

        img = QImage(image_path)
        if not img.isNull():
            # Scale to canvas size if needed
            if img.size() != self._buffer.size():
                img = img.scaled(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
            painter = QPainter(self._buffer)
            painter.drawImage(0, 0, img)
            painter.end()

        self.update()

    def is_empty(self) -> bool:
        """Check if the canvas has any drawn content."""
        return len(self._paths) == 0

    def get_path_data(self) -> list[tuple]:
        """Export all paths as a list of drawing commands for font generation."""
        commands = []
        for path in self._paths:
            for i in range(path.elementCount()):
                el = path.elementAt(i)
                if el.type == QPainterPath.ElementType.MoveToElement:
                    commands.append(("moveTo", (el.x, el.y)))
                elif el.type == QPainterPath.ElementType.LineToElement:
                    commands.append(("lineTo", (el.x, el.y)))
                elif el.type == QPainterPath.ElementType.CurveToElement:
                    commands.append(("lineTo", (el.x, el.y)))
            commands.append(("close",))
        return commands

    def _bake_path(self, path: QPainterPath):
        """Stamp a completed path into the buffer image."""
        painter = QPainter(self._buffer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._brush_pixmap and not self._brush_pixmap.isNull():
            half = self._brush_size // 2
            self._stamp_along_path(painter, path, half)
        else:
            pen = QPen(QColor("#000000"), self._brush_size,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)

        painter.end()

    def paintEvent(self, event):
        """Draw the canvas background, guides, baked buffer, and active stroke."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#ffffff"))

        # Guide lines
        guide_pen = QPen(QColor("#e0e0e0"), 1, Qt.PenStyle.DashLine)
        painter.setPen(guide_pen)

        cap_height_y = int(self.CANVAS_HEIGHT * 0.02)
        painter.drawLine(0, cap_height_y, self.CANVAS_WIDTH, cap_height_y)

        x_height_y = int(self.CANVAS_HEIGHT * 0.34)
        painter.drawLine(0, x_height_y, self.CANVAS_WIDTH, x_height_y)

        baseline_y = int(self.CANVAS_HEIGHT * 0.66)
        painter.drawLine(0, baseline_y, self.CANVAS_WIDTH, baseline_y)

        descender_y = int(self.CANVAS_HEIGHT * 0.98)
        painter.drawLine(0, descender_y, self.CANVAS_WIDTH, descender_y)

        # Guide labels
        label_pen = QPen(QColor("#bbbbbb"))
        painter.setPen(label_pen)
        painter.drawText(5, cap_height_y + 12, "Cap")
        painter.drawText(5, x_height_y - 5, "x-height")
        painter.drawText(5, baseline_y - 5, "Baseline")
        painter.drawText(5, descender_y - 5, "Descender")

        # Draw baked buffer (completed strokes)
        painter.drawImage(0, 0, self._buffer)

        # Draw current active stroke (live, with current brush settings)
        if self._current_path and self._brush_pixmap and not self._brush_pixmap.isNull():
            half = self._brush_size // 2
            self._stamp_along_path(painter, self._current_path, half)
        elif self._current_path:
            pen = QPen(QColor("#000000"), self._brush_size,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(self._current_path)

        painter.end()

    def _stamp_along_path(self, painter: QPainter, path: QPainterPath, half: int):
        """Stamp the brush pixmap along a path at regular intervals."""
        length = path.length()
        if length < 1:
            # Just stamp at the start point
            if path.elementCount() > 0:
                el = path.elementAt(0)
                painter.drawPixmap(int(el.x) - half, int(el.y) - half, self._brush_pixmap)
            return

        step = max(1.0, self._brush_size / 3.0)
        distance = 0.0
        while distance <= length:
            percent = distance / length
            point = path.pointAtPercent(min(percent, 1.0))
            painter.drawPixmap(
                int(point.x()) - half,
                int(point.y()) - half,
                self._brush_pixmap,
            )
            distance += step

    def mousePressEvent(self, event):
        """Start a new stroke."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_drawing = True
            self._current_path = QPainterPath()
            pos = event.position()
            self._current_path.moveTo(pos)
            self.update()

    def mouseMoveEvent(self, event):
        """Continue the current stroke."""
        if self._is_drawing and self._current_path:
            pos = event.position()
            self._current_path.lineTo(pos)
            self.update()

    def mouseReleaseEvent(self, event):
        """Finish the current stroke."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_drawing:
            self._is_drawing = False
            if self._current_path:
                self._paths.append(self._current_path)
                # Bake the completed stroke into the buffer
                self._bake_path(self._current_path)
                self._current_path = None
                self.drawing_changed.emit()
            self.update()
