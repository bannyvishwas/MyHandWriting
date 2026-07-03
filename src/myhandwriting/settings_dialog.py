"""Settings dialog - configure application preferences."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from myhandwriting.settings import Settings


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 400)
        self.resize(480, 450)

        self._settings = settings
        self._is_dark = QApplication.instance().palette().color(
            QPalette.ColorRole.Window
        ).lightness() < 128

        self._setup_ui()
        self._load_current_values()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer_layout.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Theme-aware colors
        text_color = "#ffffff" if self._is_dark else "#000000"
        section_style = f"font-size: 14px; font-weight: bold; color: {text_color};"

        # Title
        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {text_color};")
        layout.addWidget(title)

        # --- Appearance section ---
        appearance_label = QLabel("Appearance")
        appearance_label.setStyleSheet(section_style)
        layout.addWidget(appearance_label)

        appearance_form = QFormLayout()
        appearance_form.setSpacing(12)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["System Default", "Dark", "Light"])
        self._theme_combo.setFixedWidth(180)
        appearance_form.addRow("Theme:", self._theme_combo)

        layout.addLayout(appearance_form)

        # --- Editor section ---
        editor_label = QLabel("Editor")
        editor_label.setStyleSheet(section_style)
        layout.addWidget(editor_label)

        editor_form = QFormLayout()
        editor_form.setSpacing(12)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 200)
        self._font_size_spin.setFixedWidth(80)
        editor_form.addRow("Default Font Size:", self._font_size_spin)

        self._default_font_combo = QComboBox()
        self._default_font_combo.addItem("System Default")
        # Add user fonts
        from myhandwriting.fonts.manager import FontManager
        manager = FontManager()
        for font_info in manager.list_fonts():
            self._default_font_combo.addItem(font_info["name"])
        self._default_font_combo.setFixedWidth(180)
        editor_form.addRow("Default Font:", self._default_font_combo)

        layout.addLayout(editor_form)

        # --- Canvas section ---
        canvas_label = QLabel("Canvas")
        canvas_label.setStyleSheet(section_style)
        layout.addWidget(canvas_label)

        canvas_form = QFormLayout()
        canvas_form.setSpacing(12)

        self._brush_size_spin = QSpinBox()
        self._brush_size_spin.setRange(5, 100)
        self._brush_size_spin.setFixedWidth(80)
        canvas_form.addRow("Default Brush Size:", self._brush_size_spin)

        self._brush_combo = QComboBox()
        from myhandwriting.fonts.brushes import list_default_brushes
        for brush in list_default_brushes():
            self._brush_combo.addItem(brush["name"])
        self._brush_combo.setFixedWidth(180)
        canvas_form.addRow("Default Brush:", self._brush_combo)

        layout.addLayout(canvas_form)

        # --- Export section ---
        export_label = QLabel("Export")
        export_label.setStyleSheet(section_style)
        layout.addWidget(export_label)

        export_form = QFormLayout()
        export_form.setSpacing(12)

        self._export_format_combo = QComboBox()
        self._export_format_combo.addItems(["PDF"])
        self._export_format_combo.setFixedWidth(180)
        export_form.addRow("Export Format:", self._export_format_combo)

        layout.addLayout(export_form)

        # Stretch
        layout.addStretch()

        # --- Save button ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._save_btn = QPushButton("Save")
        self._save_btn.setFixedSize(120, 40)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2D4EBF; }
            QPushButton:pressed { background-color: #1E3A9F; }
        """)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        scroll.setWidget(content)

    def _load_current_values(self):
        """Load current settings into the UI."""
        # Theme
        theme = self._settings.get("editor", "theme", "system")
        theme_map = {"system": 0, "dark": 1, "light": 2}
        self._theme_combo.setCurrentIndex(theme_map.get(theme, 0))

        # Editor
        self._font_size_spin.setValue(self._settings.get("editor", "default_font_size", 14))
        default_font = self._settings.get("editor", "default_font", "System Default")
        idx = self._default_font_combo.findText(default_font)
        if idx >= 0:
            self._default_font_combo.setCurrentIndex(idx)

        # Canvas
        self._brush_size_spin.setValue(self._settings.get("canvas", "default_brush_size", 40))
        default_brush = self._settings.get("canvas", "default_brush", "black-ball-pen")
        # Match brush by stem name
        for i in range(self._brush_combo.count()):
            if self._brush_combo.itemText(i).lower().replace(" ", "-") == default_brush:
                self._brush_combo.setCurrentIndex(i)
                break

        # Export
        export_format = self._settings.get("export", "format", "pdf").upper()
        idx = self._export_format_combo.findText(export_format)
        if idx >= 0:
            self._export_format_combo.setCurrentIndex(idx)

    def _on_save(self):
        """Save all settings and close."""
        # Theme
        theme_map = {0: "system", 1: "dark", 2: "light"}
        self._settings.set("editor", "theme", theme_map.get(self._theme_combo.currentIndex(), "system"))

        # Editor
        self._settings.set("editor", "default_font_size", self._font_size_spin.value())
        self._settings.set("editor", "default_font", self._default_font_combo.currentText())

        # Canvas
        self._settings.set("canvas", "default_brush_size", self._brush_size_spin.value())
        brush_name = self._brush_combo.currentText().lower().replace(" ", "-")
        self._settings.set("canvas", "default_brush", brush_name)

        # Export
        self._settings.set("export", "format", self._export_format_combo.currentText().lower())

        self.accept()

    def get_theme(self) -> str:
        """Get the selected theme value."""
        theme_map = {0: "system", 1: "dark", 2: "light"}
        return theme_map.get(self._theme_combo.currentIndex(), "system")
