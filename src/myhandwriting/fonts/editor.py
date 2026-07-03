"""Font editor dialog - guides user through drawing each character."""

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from myhandwriting.fonts.brushes import (
    import_custom_brush,
    list_default_brushes,
)
from myhandwriting.fonts.canvas import GlyphCanvas
from myhandwriting.fonts.generator import CHARSET, FontGenerator
from myhandwriting.fonts.manager import FontManager


CANVAS_WIDTH = GlyphCanvas.CANVAS_WIDTH
UI_PANEL_WIDTH = 400  # Width for controls, buttons, indicator (independent of canvas)


class FontEditorDialog(QDialog):
    """Dialog for creating/editing handwriting fonts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Fonts")
        self.setMinimumSize(500, 700)
        self.resize(520, 800)

        self._manager = FontManager()
        self._generator: FontGenerator | None = None
        self._current_index = 0
        self._edit_mode = False  # True when editing an existing font

        # Per-character brush metadata: {char: {"brush_size": int, "brush_style": str}}
        self._char_metadata: dict[str, dict] = {}

        # Detect theme
        palette = QApplication.instance().palette()
        self._is_dark = palette.color(QPalette.ColorRole.Window).lightness() < 128

        self._setup_ui()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(16)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # --- Section 1: Font name input ---
        name_section = QVBoxLayout()
        name_section.setSpacing(6)

        name_label = QLabel("Font Name")
        name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {self._fg_muted};")
        name_section.addWidget(name_label)

        name_row = QHBoxLayout()
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter your font name...")
        self._name_input.setFixedHeight(36)
        self._name_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 14px;
                padding: 4px 12px;
                border: 1px solid {self._border_color};
                border-radius: 4px;
                background: {self._input_bg};
                color: {self._fg_color};
            }}
            QLineEdit:focus {{
                border-color: #3E61DB;
            }}
        """)
        name_row.addWidget(self._name_input)

        self._start_btn = QPushButton("Start Drawing")
        self._start_btn.setFixedHeight(36)
        self._start_btn.setStyleSheet(self._blue_btn_style())
        self._start_btn.clicked.connect(self._on_start)
        name_row.addWidget(self._start_btn)

        self._info_btn = QPushButton("?")
        self._info_btn.setFixedSize(36, 36)
        self._info_btn.setToolTip("How to draw characters")
        self._info_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._input_bg};
                color: #3E61DB;
                border: 1px solid {self._border_color};
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {"#444" if self._is_dark else "#e8e8e8"};
            }}
        """)
        self._info_btn.clicked.connect(self._on_info)
        name_row.addWidget(self._info_btn)

        name_section.addLayout(name_row)
        self._layout.addLayout(name_section)

        # --- Section 2: Existing fonts list ---
        self._font_list_section = QWidget()
        font_list_layout = QVBoxLayout(self._font_list_section)
        font_list_layout.setContentsMargins(0, 0, 0, 0)
        font_list_layout.setSpacing(8)

        list_header = QLabel("Your Fonts")
        list_header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {self._fg_muted};")
        font_list_layout.addWidget(list_header)

        self._font_list_container = QVBoxLayout()
        self._font_list_container.setSpacing(4)
        font_list_layout.addLayout(self._font_list_container)

        self._layout.addWidget(self._font_list_section)
        self._populate_font_list()

        # --- Section 3: Brush controls ---
        self._brush_section = QWidget()
        self._brush_section.setFixedWidth(UI_PANEL_WIDTH)
        self._brush_section.setVisible(False)
        brush_layout = QHBoxLayout(self._brush_section)
        brush_layout.setContentsMargins(0, 0, 0, 0)
        brush_layout.setSpacing(10)

        brush_style_label = QLabel("Brush:")
        brush_style_label.setStyleSheet(f"font-size: 12px; color: {self._fg_muted};")
        brush_layout.addWidget(brush_style_label)

        self._brush_combo = QComboBox()
        self._brush_combo.setFixedWidth(52)
        self._brush_combo.setFixedHeight(32)
        self._brush_combo.setIconSize(QSize(24, 24))
        self._brush_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 2px 4px;
                border: 1px solid {self._border_color};
                border-radius: 4px;
                background-color: {self._input_bg};
                color: {self._fg_color};
            }}
            QComboBox::drop-down {{
                width: 16px;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                min-width: 180px;
                background-color: {self._input_bg};
                color: {self._fg_color};
                selection-background-color: #3E61DB;
                selection-color: white;
            }}
        """)
        self._populate_brushes()
        self._brush_combo.currentIndexChanged.connect(self._on_brush_changed)
        brush_layout.addWidget(self._brush_combo)

        self._browse_btn = QPushButton("+")
        self._browse_btn.setFixedSize(28, 28)
        self._browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._input_bg};
                color: {self._fg_color};
                border: 1px solid {self._border_color};
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {"#444" if self._is_dark else "#e0e0e0"};
            }}
        """)
        self._browse_btn.setToolTip("Import custom brush (PNG, square, 5-50px)")
        self._browse_btn.clicked.connect(self._on_browse_brush)
        brush_layout.addWidget(self._browse_btn)

        brush_layout.addSpacing(10)

        size_label = QLabel("Size:")
        size_label.setStyleSheet(f"font-size: 12px; color: {self._fg_muted};")
        brush_layout.addWidget(size_label)

        self._size_slider = QSlider(Qt.Orientation.Horizontal)
        self._size_slider.setMinimum(5)
        self._size_slider.setMaximum(100)
        self._size_slider.setValue(40)
        self._size_slider.setFixedWidth(80)
        self._size_slider.valueChanged.connect(self._on_brush_size_changed)
        brush_layout.addWidget(self._size_slider)

        self._size_value_label = QLabel("40px")
        self._size_value_label.setFixedWidth(35)
        self._size_value_label.setStyleSheet(f"font-size: 12px; color: {self._fg_color};")
        brush_layout.addWidget(self._size_value_label)

        brush_layout.addStretch()
        self._layout.addWidget(self._brush_section, alignment=Qt.AlignmentFlag.AlignHCenter)

        # --- Section 4: Character indicator ---
        self._indicator_section = QWidget()
        self._indicator_section.setFixedWidth(UI_PANEL_WIDTH)
        self._indicator_section.setVisible(False)
        indicator_layout = QHBoxLayout(self._indicator_section)
        indicator_layout.setContentsMargins(0, 0, 0, 0)
        indicator_layout.setSpacing(12)

        self._char_label = QLabel("A")
        self._char_label.setStyleSheet("font-size: 52px; font-weight: bold; color: #3E61DB;")
        self._char_label.setFixedWidth(64)
        self._char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        indicator_layout.addWidget(self._char_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        self._info_label = QLabel("Draw the character shown on the left")
        self._info_label.setStyleSheet(f"font-size: 13px; color: {self._fg_color};")
        info_col.addWidget(self._info_label)

        self._progress_label = QLabel("Character 1 of 87")
        self._progress_label.setStyleSheet(f"font-size: 12px; color: {self._fg_muted};")
        info_col.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(len(CHARSET))
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(16)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self._border_color};
                border-radius: 8px;
                background: {self._input_bg};
            }}
            QProgressBar::chunk {{
                background-color: #3E61DB;
                border-radius: 7px;
            }}
        """)
        info_col.addWidget(self._progress_bar)

        indicator_layout.addLayout(info_col)
        self._layout.addWidget(self._indicator_section, alignment=Qt.AlignmentFlag.AlignHCenter)

        # --- Section 5: Canvas ---
        self._canvas_section = QWidget()
        self._canvas_section.setVisible(False)
        canvas_layout = QVBoxLayout(self._canvas_section)
        canvas_layout.setContentsMargins(0, 0, 0, 0)

        self._canvas = GlyphCanvas()
        self._canvas.setStyleSheet(f"border: 2px solid {self._border_color}; border-radius: 6px;")
        canvas_layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._layout.addWidget(self._canvas_section, alignment=Qt.AlignmentFlag.AlignHCenter)

        # --- Section 6: Navigation buttons ---
        self._btn_section = QWidget()
        self._btn_section.setFixedWidth(UI_PANEL_WIDTH)
        self._btn_section.setVisible(False)
        btn_layout = QHBoxLayout(self._btn_section)
        btn_layout.setContentsMargins(0, 8, 0, 0)
        btn_layout.setSpacing(8)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedHeight(36)
        self._clear_btn.setStyleSheet(self._gray_btn_style())
        self._clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self._clear_btn)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setFixedHeight(36)
        self._skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #ec971f; }
        """)
        self._skip_btn.clicked.connect(self._on_skip)
        btn_layout.addWidget(self._skip_btn)

        self._prev_btn = QPushButton("← Previous")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.setEnabled(False)
        self._prev_btn.setStyleSheet(self._gray_btn_style())
        self._prev_btn.clicked.connect(self._on_prev)
        btn_layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next →")
        self._next_btn.setFixedHeight(36)
        self._next_btn.setStyleSheet(self._blue_btn_style())
        self._next_btn.clicked.connect(self._on_next)
        btn_layout.addWidget(self._next_btn)

        self._layout.addWidget(self._btn_section, alignment=Qt.AlignmentFlag.AlignHCenter)

        # --- Section 7: Generate/Save button ---
        self._generate_section = QWidget()
        self._generate_section.setFixedWidth(UI_PANEL_WIDTH)
        self._generate_section.setVisible(False)
        gen_layout = QHBoxLayout(self._generate_section)
        gen_layout.setContentsMargins(0, 12, 0, 0)
        gen_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._generate_btn = QPushButton("Generate Font")
        self._generate_btn.setFixedHeight(40)
        self._generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 32px;
            }
            QPushButton:hover { background-color: #4cae4c; }
            QPushButton:pressed { background-color: #398439; }
        """)
        self._generate_btn.clicked.connect(self._on_generate)
        gen_layout.addWidget(self._generate_btn)

        self._layout.addWidget(self._generate_section, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Bottom stretch
        self._layout.addStretch()

        scroll.setWidget(content)

    # --- Font list ---

    def _populate_font_list(self):
        """Populate the existing fonts list with edit/delete buttons."""
        # Clear existing items
        while self._font_list_container.count():
            item = self._font_list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fonts = self._manager.list_fonts()

        if not fonts:
            empty_label = QLabel("No fonts created yet.")
            empty_label.setStyleSheet(f"font-size: 12px; color: {self._fg_muted}; font-style: italic; padding: 8px 0;")
            self._font_list_container.addWidget(empty_label)
            return

        for font_info in fonts:
            row = QWidget()
            row.setFixedHeight(40)
            row.setStyleSheet(f"""
                QWidget {{
                    background-color: {self._input_bg};
                    border: 1px solid {self._border_color};
                    border-radius: 4px;
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 4, 8, 4)
            row_layout.setSpacing(8)

            # Font name
            name_lbl = QLabel(font_info["name"])
            name_lbl.setStyleSheet(f"font-size: 13px; color: {self._fg_color}; border: none; background: transparent;")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            # Edit button
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(60, 28)
            edit_btn.setStyleSheet(self._blue_btn_style())
            edit_btn.clicked.connect(lambda checked, name=font_info["name"]: self._on_edit_font(name))
            row_layout.addWidget(edit_btn)

            # Delete button
            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(55, 28)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #c9302c; }
            """)
            del_btn.clicked.connect(lambda checked, name=font_info["name"]: self._on_delete_font(name))
            row_layout.addWidget(del_btn)

            self._font_list_container.addWidget(row)

    def _on_edit_font(self, font_name: str):
        """Load an existing font for editing, restoring saved glyph paths."""
        self._edit_mode = True
        self._name_input.setText(font_name)
        self._name_input.setEnabled(False)
        self._start_btn.setEnabled(False)

        self._generator = FontGenerator(font_name)
        self._current_index = 0

        # Restore saved glyph data if available
        glyph_data = self._manager.load_glyph_data(font_name)
        if glyph_data:
            for char, paths in glyph_data.items():
                restored = []
                for cmd in paths:
                    if len(cmd) == 2:
                        restored.append((cmd[0], tuple(cmd[1])))
                    else:
                        restored.append((cmd[0],))
                self._generator.set_glyph_paths(char, restored)

        # Restore metadata (brush settings per char)
        metadata = self._manager.load_metadata(font_name)
        if metadata and "chars" in metadata:
            self._char_metadata = metadata["chars"]
        else:
            self._char_metadata = {}

        # Hide font list, show drawing sections
        self._font_list_section.setVisible(False)
        self._brush_section.setVisible(True)
        self._indicator_section.setVisible(True)
        self._canvas_section.setVisible(True)
        self._btn_section.setVisible(True)
        self._generate_section.setVisible(True)

        # Change button text to "Save"
        self._generate_btn.setText("Save")

        self._update_char_display()
        self._restore_canvas()

    def _on_delete_font(self, font_name: str):
        """Delete a font after confirmation."""
        reply = QMessageBox.question(
            self, "Delete Font",
            f'Are you sure you want to delete "{font_name}"?\nThis cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._manager.delete_font(font_name):
                QMessageBox.information(self, "Deleted", f'Font "{font_name}" has been deleted.')
                self._populate_font_list()
            else:
                QMessageBox.warning(self, "Error", f'Could not delete "{font_name}".')

    # --- Theme properties ---

    @property
    def _fg_color(self) -> str:
        return "#ffffff" if self._is_dark else "#000000"

    @property
    def _fg_muted(self) -> str:
        return "#aaa" if self._is_dark else "#666"

    @property
    def _input_bg(self) -> str:
        return "#3a3a3a" if self._is_dark else "#ffffff"

    @property
    def _border_color(self) -> str:
        return "#555" if self._is_dark else "#ccc"

    # --- Style helpers ---

    def _blue_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton:hover { background-color: #2D4EBF; }
            QPushButton:pressed { background-color: #1E3A9F; }
        """

    def _gray_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                padding: 4px 16px;
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:disabled { background-color: #f5f5f5; color: #aaa; }
        """

    # --- Brush controls ---

    def _populate_brushes(self):
        """Populate the brush dropdown with icons and names."""
        from PyQt6.QtGui import QIcon, QPixmap
        from myhandwriting.fonts.brushes import list_default_brushes, list_custom_brushes

        self._brush_combo.clear()
        self._brush_list = []

        defaults = list_default_brushes()
        for brush in defaults:
            icon = QIcon(QPixmap(str(brush["path"])).scaled(24, 24))
            self._brush_combo.addItem(icon, brush["name"])
            self._brush_list.append(brush)

        customs = list_custom_brushes()
        for i, brush in enumerate(customs, start=1):
            icon = QIcon(QPixmap(str(brush["path"])).scaled(24, 24))
            self._brush_combo.addItem(icon, f"User Brush {i}")
            self._brush_list.append(brush)

        for idx, brush in enumerate(self._brush_list):
            if "black-ball-pen" in str(brush["path"]):
                self._brush_combo.setCurrentIndex(idx)
                break

    def _on_brush_changed(self, index: int):
        if 0 <= index < len(self._brush_list):
            self._canvas.set_brush(self._brush_list[index]["path"])

    def _on_brush_size_changed(self, value: int):
        self._canvas.brush_size = value
        self._size_value_label.setText(f"{value}px")

    def _on_browse_brush(self):
        from myhandwriting.settings import Settings
        settings = Settings()
        last_dir = settings.get("app", "last_file_directory", "")
        if not last_dir:
            last_dir = str(Path.home() / "Documents")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Custom Brush", last_dir, "PNG Images (*.png)",
        )
        if not file_path:
            return

        settings.set("app", "last_file_directory", str(Path(file_path).parent))

        success, message = import_custom_brush(Path(file_path))
        if success:
            QMessageBox.information(self, "Brush Imported", message)
            self._populate_brushes()
            self._brush_combo.setCurrentIndex(self._brush_combo.count() - 1)
        else:
            QMessageBox.warning(self, "Import Failed", message)

    # --- Drawing actions ---

    def _on_info(self):
        """Show instruction window with example character placements."""
        from PyQt6.QtGui import QPixmap
        from myhandwriting.resources import get_icon

        dialog = QDialog(self)
        dialog.setWindowTitle("How to Draw Characters")
        dialog.setMinimumSize(500, 420)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        # Header
        header = QLabel("Draw characters between the guide lines:")
        header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self._fg_color};")
        layout.addWidget(header)

        # Instructions
        instructions = QLabel(
            "• Uppercase letters & digits: draw between Cap and Baseline\n"
            "• Lowercase letters: draw between x-height and Baseline\n"
            "• Descenders (g, y, p, q): extend below Baseline to Descender\n"
            "• Symbols: draw between x-height and Baseline"
        )
        instructions.setStyleSheet(f"font-size: 12px; color: {self._fg_muted}; padding: 4px 0;")
        layout.addWidget(instructions)

        # Examples grid
        grid_widget = QWidget()
        grid_layout = QHBoxLayout(grid_widget)
        grid_layout.setSpacing(12)

        examples = [
            ("Uppercase", "example-A.png"),
            ("Lowercase", "example-b.png"),
            ("Descender", "example-y.png"),
            ("Digit", "example-1.png"),
            ("Symbol", "example-colon.png"),
        ]

        for label_text, img_file in examples:
            col = QVBoxLayout()
            col.setSpacing(4)

            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {self._fg_muted};")
            col.addWidget(lbl)

            img_label = QLabel()
            pixmap = QPixmap(str(get_icon(img_file)))
            if not pixmap.isNull():
                img_label.setPixmap(pixmap.scaled(80, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet(f"border: 1px solid {self._border_color}; border-radius: 4px;")
            col.addWidget(img_label)

            grid_layout.addLayout(col)

        layout.addWidget(grid_widget)

        # Close button
        close_btn = QPushButton("Got it!")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(self._blue_btn_style())
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def _on_start(self):
        """Validate font name and start drawing mode."""
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Font Name Required", "Please enter a name for your font.")
            return

        if self._manager.font_exists(name):
            reply = QMessageBox.question(
                self, "Font Exists",
                f'A font named "{name}" already exists. Overwrite it?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self._edit_mode = False
        self._generator = FontGenerator(name)
        self._current_index = 0
        self._name_input.setEnabled(False)
        self._start_btn.setEnabled(False)

        # Hide font list, show drawing sections
        self._font_list_section.setVisible(False)
        self._brush_section.setVisible(True)
        self._indicator_section.setVisible(True)
        self._canvas_section.setVisible(True)
        self._btn_section.setVisible(True)
        self._generate_section.setVisible(True)

        self._generate_btn.setText("Generate Font")
        self._update_char_display()

    def _update_char_display(self):
        char = CHARSET[self._current_index]
        self._char_label.setText(char)
        self._progress_label.setText(f"Character {self._current_index + 1} of {len(CHARSET)}")

        drawn = self._generator.drawn_chars
        if 0 < drawn < 4:
            self._progress_bar.setValue(4)
        else:
            self._progress_bar.setValue(drawn)

        self._prev_btn.setEnabled(self._current_index > 0)

        if self._generator.has_glyph(char):
            self._info_label.setText("✓ Already drawn — redraw or press Next")
        else:
            self._info_label.setText("Draw the character shown on the left")

    def _save_current_glyph(self):
        if not self._canvas.is_empty():
            char = CHARSET[self._current_index]
            path_data = self._canvas.get_path_data()
            self._generator.set_glyph_paths(char, path_data)
            # Save the canvas bitmap for this character
            self._save_glyph_image(char)
            # Record brush settings for this character
            current_brush_idx = self._brush_combo.currentIndex()
            brush_name = ""
            if 0 <= current_brush_idx < len(self._brush_list):
                brush_name = str(self._brush_list[current_brush_idx]["path"].stem)
            self._char_metadata[char] = {
                "brush_size": self._size_slider.value(),
                "brush_style": brush_name,
                "image": f"{ord(char)}.png",
            }

    def _on_clear(self):
        self._canvas.clear()

    def _on_skip(self):
        if self._current_index < len(CHARSET) - 1:
            self._current_index += 1
            self._canvas.clear()
            self._update_char_display()

    def _on_prev(self):
        if self._current_index > 0:
            self._save_current_glyph()
            self._current_index -= 1
            self._canvas.clear()
            self._restore_canvas()
            self._update_char_display()

    def _on_next(self):
        self._save_current_glyph()
        if self._current_index < len(CHARSET) - 1:
            self._current_index += 1
            self._canvas.clear()
            self._restore_canvas()
            self._update_char_display()
        else:
            self._update_char_display()

    def _restore_canvas(self):
        """Restore previously drawn content for the current character.

        Loads the saved PNG image directly to preserve original brush appearance.
        Also restores brush size and style from metadata.
        """
        char = CHARSET[self._current_index]
        if not self._generator:
            return

        # Restore brush settings from metadata for this character
        if char in self._char_metadata:
            meta = self._char_metadata[char]
            # Restore brush size
            saved_size = meta.get("brush_size", 12)
            self._size_slider.blockSignals(True)
            self._size_slider.setValue(saved_size)
            self._size_slider.blockSignals(False)
            self._size_value_label.setText(f"{saved_size}px")
            self._canvas.brush_size = saved_size

            # Restore brush style
            saved_style = meta.get("brush_style", "")
            if saved_style:
                for idx, brush in enumerate(self._brush_list):
                    if brush["path"].stem == saved_style:
                        self._brush_combo.blockSignals(True)
                        self._brush_combo.setCurrentIndex(idx)
                        self._brush_combo.blockSignals(False)
                        self._canvas.set_brush(brush["path"])
                        break

        # Try loading the saved bitmap first (preserves original brush size/texture)
        img_path = self._manager.get_glyph_image_path(self._generator.font_name, char)
        if img_path:
            self._canvas.load_from_image(str(img_path))
            # Also restore paths for data export
            if self._generator.has_glyph(char):
                path_data = self._generator._glyphs[char]
                from PyQt6.QtCore import QPointF
                from PyQt6.QtGui import QPainterPath
                current_path = None
                for cmd in path_data:
                    if cmd[0] == "moveTo":
                        current_path = QPainterPath()
                        current_path.moveTo(QPointF(cmd[1][0], cmd[1][1]))
                    elif cmd[0] == "lineTo" and current_path is not None:
                        current_path.lineTo(QPointF(cmd[1][0], cmd[1][1]))
                    elif cmd[0] == "close":
                        if current_path is not None:
                            self._canvas._paths.append(current_path)
                            current_path = None
                if current_path is not None:
                    self._canvas._paths.append(current_path)
        elif self._generator.has_glyph(char):
            # Fallback: re-render from path data
            path_data = self._generator._glyphs[char]
            self._canvas.load_paths(path_data)

    def _save_glyph_image(self, char: str):
        """Save the current canvas buffer as a processed PNG (smoothed + cropped)."""
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import Qt

        img_dir = self._manager.get_glyphs_image_dir(self._generator.font_name)
        img_path = img_dir / f"{ord(char)}.png"
        buffer = self._canvas.get_buffer_image()

        # Skip processing for space
        if char == ' ':
            buffer.save(str(img_path), "PNG")
            return

        # Step 1: Crop left/right empty space
        cropped = self._crop_horizontal(buffer)

        # Step 2: Smooth (scale up 2x then back down with smooth transformation)
        w, h = cropped.width(), cropped.height()
        if w > 0 and h > 0:
            scaled_up = cropped.scaled(w * 2, h * 2,
                                       Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            smoothed = scaled_up.scaled(w, h,
                                        Qt.AspectRatioMode.IgnoreAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            smoothed.save(str(img_path), "PNG")
        else:
            buffer.save(str(img_path), "PNG")

    def _crop_horizontal(self, image) -> 'QImage':
        """Crop empty columns from left and right of the image."""
        w, h = image.width(), image.height()
        left = w
        right = 0

        for x in range(w):
            for y in range(h):
                if image.pixelColor(x, y).alpha() > 0:
                    left = min(left, x)
                    right = max(right, x)
                    break

        if left > right:
            # Completely empty — return as-is
            return image

        # Add small padding
        padding = 3
        left = max(0, left - padding)
        right = min(w - 1, right + padding)

        return image.copy(left, 0, right - left + 1, h)

    def _create_space_image(self):
        """Create a blank (transparent) PNG for the space character."""
        from PyQt6.QtGui import QImage, QColor
        img_dir = self._manager.get_glyphs_image_dir(self._generator.font_name)
        img_path = img_dir / f"{ord(' ')}.png"
        # Create a transparent image at canvas size
        img = QImage(GlyphCanvas.CANVAS_WIDTH, GlyphCanvas.CANVAS_HEIGHT, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        img.save(str(img_path), "PNG")

    def _on_generate(self):
        """Generate or save the font."""
        if not self._generator:
            return

        self._save_current_glyph()

        if self._generator.drawn_chars == 0:
            QMessageBox.warning(
                self, "No Characters",
                "You haven't drawn any characters yet. Draw at least one before saving.",
            )
            return

        try:
            # .ttf generation disabled - using bitmap images instead
            # output_path = self._manager.fonts_dir / f"{self._generator.font_name}.ttf"
            # result_path = self._generator.generate(output_path)

            # Save glyph path data for future editing
            self._manager.save_glyph_data(
                self._generator.font_name,
                self._generator._glyphs,
            )

            # Save metadata (brush settings per char, image mappings)
            metadata = {
                "font_name": self._generator.font_name,
                "chars": self._char_metadata,
            }
            self._manager.save_metadata(self._generator.font_name, metadata)

            # Create a blank (transparent) space image
            self._create_space_image()

            if self._edit_mode:
                QMessageBox.information(
                    self, "Font Saved",
                    f"Font '{self._generator.font_name}' updated successfully!\n\n"
                    f"Characters drawn: {self._generator.drawn_chars}/{self._generator.total_chars}\n"
                    f"Missing characters will show as □",
                )
            else:
                QMessageBox.information(
                    self, "Font Generated",
                    f"Font '{self._generator.font_name}' created successfully!\n\n"
                    f"Characters drawn: {self._generator.drawn_chars}/{self._generator.total_chars}\n"
                    f"Missing characters will show as □",
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save font:\n{e}")
