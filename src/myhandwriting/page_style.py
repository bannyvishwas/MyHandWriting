"""Page style and customize dialog for the editor."""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from myhandwriting.page_textures import list_all_textures, import_custom_texture
from myhandwriting.settings import Settings
from pathlib import Path


# Page style types
PAGE_STYLES = ["Plain", "Lined", "Ruled", "Grid"]

# Default line spacing in pixels
DEFAULT_LINE_SPACING = 28


class PageCustomizeDialog(QDialog):
    """Dialog for customizing page layout settings."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Page Format")
        self.setMinimumSize(450, 520)
        self.resize(470, 560)

        self._settings = settings
        self._is_dark = QApplication.instance().palette().color(
            QPalette.ColorRole.Window
        ).lightness() < 128

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        from PyQt6.QtWidgets import QScrollArea

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        text_color = "#ffffff" if self._is_dark else "#000000"

        title = QLabel("Page Format")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {text_color};")
        layout.addWidget(title)

        # --- Section 1: Page Settings ---
        page_form = QFormLayout()
        page_form.setSpacing(16)

        # Page Size
        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["A4", "Letter", "A3", "A5"])
        self._page_size_combo.setFixedWidth(160)
        page_form.addRow("Page Size:", self._page_size_combo)

        # Margins
        self._margin_h_spin = QSpinBox()
        self._margin_h_spin.setRange(0, 200)
        self._margin_h_spin.setSuffix(" px")
        self._margin_h_spin.setFixedWidth(100)
        self._margin_h_spin.setToolTip("Left and right margin")
        page_form.addRow("Horizontal Margin:", self._margin_h_spin)

        self._margin_v_spin = QSpinBox()
        self._margin_v_spin.setRange(0, 200)
        self._margin_v_spin.setSuffix(" px")
        self._margin_v_spin.setFixedWidth(100)
        self._margin_v_spin.setToolTip("Top and bottom margin")
        page_form.addRow("Vertical Margin:", self._margin_v_spin)

        # Page Texture
        self._texture_combo = QComboBox()
        self._texture_combo.setIconSize(QSize(24, 24))
        self._texture_list = list_all_textures()
        self._add_texture_items(self._texture_combo, self._texture_list)
        self._texture_combo.setFixedWidth(200)
        page_form.addRow("Page Texture:", self._texture_combo)

        # Import texture button
        import_row = QHBoxLayout()
        self._import_btn = QPushButton("Import Texture...")
        self._import_btn.setFixedHeight(30)
        btn_bg = "#444" if self._is_dark else "#e8e8e8"
        btn_color = "#ffffff" if self._is_dark else "#333333"
        btn_hover = "#555" if self._is_dark else "#d0d0d0"
        self._import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_color};
                border: none;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        self._import_btn.clicked.connect(self._on_import_texture)
        import_row.addWidget(self._import_btn)
        import_row.addStretch()
        page_form.addRow("", import_row)

        layout.addLayout(page_form)

        # --- Divider ---
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {'#555' if self._is_dark else '#ccc'};")
        layout.addWidget(divider)

        # --- Section 2: Page Style ---
        style_form = QFormLayout()
        style_form.setSpacing(16)

        # Page Style
        self._page_style_combo = QComboBox()
        self._page_style_combo.addItems(PAGE_STYLES)
        self._page_style_combo.setFixedWidth(160)
        self._page_style_combo.currentTextChanged.connect(self._on_style_changed)
        style_form.addRow("Page Style:", self._page_style_combo)

        # Line thickness slider
        thickness_row = QHBoxLayout()
        self._thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self._thickness_slider.setMinimum(1)
        self._thickness_slider.setMaximum(10)
        self._thickness_slider.setValue(1)
        self._thickness_slider.setFixedWidth(100)
        self._thickness_slider.valueChanged.connect(self._on_thickness_changed)
        thickness_row.addWidget(self._thickness_slider)

        self._thickness_label = QLabel("1px")
        self._thickness_label.setFixedWidth(35)
        thickness_row.addWidget(self._thickness_label)
        thickness_row.addStretch()
        style_form.addRow("Line Thickness:", thickness_row)

        # Red line position (for Ruled style only)
        self._red_line_spin = QSpinBox()
        self._red_line_spin.setRange(0, 300)
        self._red_line_spin.setSuffix(" px")
        self._red_line_spin.setFixedWidth(100)
        self._red_line_spin.setToolTip("Position of the red margin line (Ruled style only)")
        style_form.addRow("Red Line Position:", self._red_line_spin)

        layout.addLayout(style_form)
        layout.addStretch()

        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._save_btn = QPushButton("Apply")
        self._save_btn.setFixedSize(100, 36)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2D4EBF; }
        """)
        self._save_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        scroll.setWidget(content)

    def _load_values(self):
        """Load current settings into controls."""
        # Page size
        paper = self._settings.get("export", "paper_size", "a4")
        paper_text = paper.upper() if paper != "letter" else "Letter"
        idx = self._page_size_combo.findText(paper_text)
        if idx >= 0:
            self._page_size_combo.setCurrentIndex(idx)

        # Page style
        style = self._settings.get("editor", "page_style", "Plain")
        idx = self._page_style_combo.findText(style)
        if idx >= 0:
            self._page_style_combo.setCurrentIndex(idx)

        # Texture
        saved_texture = self._settings.get("editor", "page_texture", "None")
        for idx, t in enumerate(self._texture_list):
            if t["name"] == saved_texture:
                self._texture_combo.setCurrentIndex(idx)
                break

        # Margins
        self._margin_h_spin.setValue(self._settings.get("editor", "margin_horizontal", 72))
        self._margin_v_spin.setValue(self._settings.get("editor", "margin_vertical", 48))

        # Red line position (default to horizontal margin)
        margin_h = self._settings.get("editor", "margin_horizontal", 40)
        red_line_pos = self._settings.get("editor", "red_line_position", margin_h)
        self._red_line_spin.setValue(red_line_pos)

        # Line thickness
        thickness = self._settings.get("editor", "line_thickness", 1)
        self._thickness_slider.setValue(thickness)
        self._thickness_label.setText(f"{thickness}px")

        # Enable/disable style size based on current style
        self._on_style_changed(self._page_style_combo.currentText())

    def _on_style_changed(self, style: str):
        """Enable/disable controls based on selected style."""
        self._thickness_slider.setEnabled(style != "Plain")
        self._red_line_spin.setEnabled(style == "Ruled")

    def _on_thickness_changed(self, value: int):
        """Update thickness label."""
        self._thickness_label.setText(f"{value}px")

    def _add_texture_items(self, combo: QComboBox, texture_list: list):
        """Add texture items to a combo box with icons where applicable."""
        from pathlib import Path as _Path
        for t in texture_list:
            path = t["path"]
            if path and isinstance(path, _Path) and path.exists():
                icon = QIcon(QPixmap(str(path)).scaled(24, 24))
                combo.addItem(icon, t["name"])
            else:
                combo.addItem(t["name"])

    def _on_import_texture(self):
        """Import a custom texture file."""
        last_dir = self._settings.get("app", "last_file_directory", "")
        if not last_dir:
            last_dir = str(Path.home() / "Documents")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Page Texture", last_dir, "Images (*.png *.jpg *.jpeg)",
        )
        if not file_path:
            return

        self._settings.set("app", "last_file_directory", str(Path(file_path).parent))

        success, message = import_custom_texture(Path(file_path))
        if success:
            QMessageBox.information(self, "Texture Imported", message)
            # Refresh texture list
            self._texture_list = list_all_textures()
            self._texture_combo.clear()
            self._add_texture_items(self._texture_combo, self._texture_list)
            self._texture_combo.setCurrentIndex(self._texture_combo.count() - 1)
        else:
            QMessageBox.warning(self, "Import Failed", message)

    def _on_apply(self):
        """Save settings and close."""
        self._settings.set("export", "paper_size", self._page_size_combo.currentText().lower())
        self._settings.set("editor", "page_style", self._page_style_combo.currentText())
        self._settings.set("editor", "margin_horizontal", self._margin_h_spin.value())
        self._settings.set("editor", "margin_vertical", self._margin_v_spin.value())
        self._settings.set("editor", "red_line_position", self._red_line_spin.value())
        self._settings.set("editor", "line_thickness", self._thickness_slider.value())

        # Save texture name
        idx = self._texture_combo.currentIndex()
        if 0 <= idx < len(self._texture_list):
            self._settings.set("editor", "page_texture", self._texture_list[idx]["name"])

        self.accept()
