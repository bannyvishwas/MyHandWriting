"""Main application window - text editor style UI."""

from PyQt6.QtCore import Qt, QEvent, QUrl
from PyQt6.QtGui import QFont, QFontDatabase, QIcon, QImage, QPalette, QTextCharFormat, QTextCursor, QTextImageFormat
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QToolBar,
    QToolButton,
    QWidget,
)

from pathlib import Path
from typing import Optional

from myhandwriting.resources import get_icon
from myhandwriting.fileformat import StyledSpan, StyledLine, PageData, PageFormat, Document, serialize_document, parse_document
from myhandwriting.fonts.editor import FontEditorDialog
from myhandwriting.fonts.manager import FontManager
from myhandwriting.page_editor import PageManager
from myhandwriting.page_textures import list_all_textures, import_custom_texture
from myhandwriting.page_style import PageCustomizeDialog
from myhandwriting.exporter import export_to_pdf
from myhandwriting.settings import Settings
from myhandwriting.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window with toolbar, text editor, and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyHandWriting")
        self.setWindowIcon(QIcon(str(get_icon("icon.png"))))

        # Load settings
        self._settings = Settings()

        # Apply window size from settings
        win_w = self._settings.get("app", "window_width", 900)
        win_h = self._settings.get("app", "window_height", 600)
        self.setMinimumSize(900, 600)
        self.resize(win_w, win_h)

        # Theme state from settings
        self._theme_mode = self._settings.get("editor", "theme", "system")
        self._is_dark = self._resolve_dark_mode()
        self._apply_global_palette()

        self._setup_menubar()
        self._setup_toolbar()
        self._populate_page_textures()
        self._setup_editor()
        self._setup_statusbar()

        # Active user font for image-based rendering (None = system font)
        self._active_user_font = None
        self._current_file: Optional[Path] = None

        # Load user fonts into the dropdown
        self._refresh_font_list()

        # Apply default font size from settings
        default_size = self._settings.get("editor", "default_font_size", 14)
        self.size_combo.setCurrentText(str(default_size))

        # Apply default font from settings
        default_font = self._settings.get("editor", "default_font", "System Default")
        idx = self.font_combo.findText(default_font)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)

    def _detect_system_dark(self) -> bool:
        """Detect if the OS is using a dark theme."""
        palette = QApplication.instance().palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128

    def _resolve_dark_mode(self) -> bool:
        """Resolve whether dark mode should be active based on theme setting."""
        if self._theme_mode == "dark":
            return True
        elif self._theme_mode == "light":
            return False
        else:
            return self._detect_system_dark()

    def _setup_menubar(self):
        """Hide the menu bar - settings moved to toolbar."""
        self.menuBar().setVisible(False)

    def _switch_theme(self, mode: str):
        """Switch the application theme and re-apply all styles."""
        self._theme_mode = mode
        self._is_dark = self._resolve_dark_mode()
        self._settings.set("editor", "theme", mode)
        self._apply_global_palette()
        self._apply_theme()

    def _apply_global_palette(self):
        """Apply a global palette to the entire application so all windows inherit the theme."""
        from PyQt6.QtGui import QColor
        app = QApplication.instance()
        palette = QPalette()

        if self._is_dark:
            palette.setColor(QPalette.ColorRole.Window, QColor("#2d2d2d"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#3a3a3a"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#3a3a3a"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#3E61DB"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3a3a3a"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#888888"))
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#f8f8f8"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#e8e8e8"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#3E61DB"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#888888"))

        app.setPalette(palette)

    def _apply_theme(self):
        """Re-apply all theme-dependent styles."""
        # Toolbar
        toolbar_bg = "#2d2d2d" if self._is_dark else "#f8f8f8"
        toolbar_border = "#555" if self._is_dark else "#d0d0d0"
        self._toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {toolbar_bg};
                border-bottom: 1px solid {toolbar_border};
                padding: 4px 8px;
                spacing: 6px;
            }}
        """)

        # Tool buttons (blue icons, no border/background)
        self._style_tool_button(self.save_btn)
        self._style_tool_button(self.open_btn)
        self._style_tool_button(self.align_left_btn)
        self._style_tool_button(self.align_center_btn)
        self._style_tool_button(self.align_right_btn)

        # Help button icon
        self.help_btn.setIcon(QIcon(str(get_icon("help-blue.svg"))))

        # Font combo and size combo text color
        combo_text = "#ffffff" if self._is_dark else "#000000"
        combo_bg = "#3a3a3a" if self._is_dark else "#ffffff"
        combo_border = "#555" if self._is_dark else "#ccc"
        arrow_icon = str(get_icon("chevron-down-dark.svg")) if self._is_dark else str(get_icon("chevron-down-light.svg"))
        combo_style = f"""
            QComboBox {{
                color: {combo_text};
                background-color: {combo_bg};
                border: 1px solid {combo_border};
                border-radius: 4px;
                padding: 2px 24px 2px 6px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_icon});
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                color: {combo_text};
                background-color: {combo_bg};
                selection-background-color: #3E61DB;
                selection-color: white;
            }}
        """
        self.font_combo.setStyleSheet(combo_style)
        self.size_combo.setStyleSheet(combo_style)

        # Editor - apply page texture (handles border color too)
        self._apply_page_texture()

        # Desk background
        desk_bg = "#3a3a3a" if self._is_dark else "#c0c0c0"
        self._desk.setStyleSheet(f"background-color: {desk_bg};")
        # Scroll area background
        scroll = self.centralWidget()
        if scroll:
            scroll.setStyleSheet(f"QScrollArea {{ background-color: {desk_bg}; border: none; }}")

        # Status bar - dark theme: black text, light theme: black text
        status_bg = "#2d2d2d" if self._is_dark else "#f0f0f0"
        status_border = "#555" if self._is_dark else "#d0d0d0"
        status_color = "#ffffff" if self._is_dark else "#000000"

        self.statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {status_bg};
                border-top: 1px solid {status_border};
                font-size: 12px;
                padding: 2px 8px;
            }}
            QLabel {{
                padding: 0 12px;
                color: {status_color};
            }}
        """)

    def _style_tool_button(self, btn: QToolButton):
        """Apply blue icon and transparent style (no border/background box)."""
        # All icons are blue in both themes
        icon_name = btn.toolTip().lower()
        if "save" in icon_name:
            btn.setIcon(QIcon(str(get_icon("save-blue.svg"))))
        elif "open" in icon_name:
            btn.setIcon(QIcon(str(get_icon("open-blue.svg"))))
        elif "left" in icon_name:
            btn.setIcon(QIcon(str(get_icon("align-left-blue.svg"))))
        elif "center" in icon_name:
            btn.setIcon(QIcon(str(get_icon("align-center-blue.svg"))))
        elif "right" in icon_name:
            btn.setIcon(QIcon(str(get_icon("align-right-blue.svg"))))

        btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                padding: 4px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 0.15);
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 0.3);
            }
        """)

    def _make_tool_button(self, icon_name: str, tooltip: str) -> QToolButton:
        """Create a tool button with blue icon and no border."""
        btn = QToolButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setIconSize(btn.size().scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio))
        # Set initial blue icon
        blue_icon = icon_name.replace(".svg", "-blue.svg")
        icon_path = get_icon(blue_icon)
        if icon_path.exists():
            btn.setIcon(QIcon(str(icon_path)))
        else:
            btn.setIcon(QIcon(str(get_icon(icon_name))))

        btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                padding: 4px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 0.15);
            }
            QToolButton:pressed {
                background: rgba(128, 128, 128, 0.3);
            }
        """)
        return btn

    def _setup_toolbar(self):
        """Create the toolbar: Save, Open, Font, Size, Color, Alignment, Export, Help."""
        self._toolbar = QToolBar("Main Toolbar")
        self._toolbar.setMovable(False)

        toolbar_bg = "#2d2d2d" if self._is_dark else "#f8f8f8"
        toolbar_border = "#555" if self._is_dark else "#d0d0d0"

        self._toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {toolbar_bg};
                border-bottom: 1px solid {toolbar_border};
                padding: 4px 8px;
                spacing: 6px;
            }}
        """)
        self.addToolBar(self._toolbar)

        # Save button
        self.save_btn = self._make_tool_button("save.svg", "Save (Ctrl+S)")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setShortcut("Ctrl+S")
        self._toolbar.addWidget(self.save_btn)

        # Open button
        self.open_btn = self._make_tool_button("open.svg", "Open (Ctrl+O)")
        self.open_btn.clicked.connect(self._on_open)
        self.open_btn.setShortcut("Ctrl+O")
        self._toolbar.addWidget(self.open_btn)

        self._toolbar.addSeparator()

        # Font picker
        self.font_combo = QComboBox()
        self.font_combo.addItem("System Default")
        self.font_combo.setFixedWidth(160)
        self.font_combo.setToolTip("Font / Letter Set")
        self.font_combo.currentIndexChanged.connect(self._on_font_changed)
        self._loaded_font_families = {}
        self._toolbar.addWidget(self.font_combo)

        # Font size picker
        self.size_combo = QComboBox()
        sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"]
        self.size_combo.addItems(sizes)
        self.size_combo.setCurrentText("14")
        self.size_combo.setEditable(True)
        self.size_combo.setFixedWidth(100)
        self.size_combo.setToolTip("Font Size")
        self.size_combo.currentTextChanged.connect(self._on_size_changed)
        self._toolbar.addWidget(self.size_combo)

        # Apply initial combo styles
        combo_text = "#ffffff" if self._is_dark else "#000000"
        combo_bg = "#3a3a3a" if self._is_dark else "#ffffff"
        combo_border = "#555" if self._is_dark else "#ccc"
        arrow_icon = str(get_icon("chevron-down-dark.svg")) if self._is_dark else str(get_icon("chevron-down-light.svg"))
        combo_style = f"""
            QComboBox {{
                color: {combo_text};
                background-color: {combo_bg};
                border: 1px solid {combo_border};
                border-radius: 4px;
                padding: 2px 24px 2px 6px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_icon});
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                color: {combo_text};
                background-color: {combo_bg};
                selection-background-color: #3E61DB;
                selection-color: white;
            }}
        """
        self.font_combo.setStyleSheet(combo_style)
        self.size_combo.setStyleSheet(combo_style)

        self._toolbar.addSeparator()

        # Alignment buttons
        self.align_left_btn = self._make_tool_button("align-left.svg", "Align Left")
        self.align_left_btn.clicked.connect(lambda: self._on_align(Qt.AlignmentFlag.AlignLeft))
        self._toolbar.addWidget(self.align_left_btn)

        self.align_center_btn = self._make_tool_button("align-center.svg", "Align Center")
        self.align_center_btn.clicked.connect(lambda: self._on_align(Qt.AlignmentFlag.AlignCenter))
        self._toolbar.addWidget(self.align_center_btn)

        self.align_right_btn = self._make_tool_button("align-right.svg", "Align Right")
        self.align_right_btn.clicked.connect(lambda: self._on_align(Qt.AlignmentFlag.AlignRight))
        self._toolbar.addWidget(self.align_right_btn)

        self._toolbar.addSeparator()

        # Page Format button (opens page customization dialog)
        self.page_format_btn = QPushButton("Page Format")
        self.page_format_btn.setFixedHeight(32)
        self.page_format_btn.setToolTip("Page Size, Style & Texture")
        self.page_format_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2D4EBF;
            }
            QPushButton:pressed {
                background-color: #1E3A9F;
            }
        """)
        self.page_format_btn.clicked.connect(self._on_customize_page)
        self._toolbar.addWidget(self.page_format_btn)

        # Remove Page button
        self.remove_page_btn = QPushButton("Remove Page")
        self.remove_page_btn.setFixedHeight(32)
        self.remove_page_btn.setToolTip("Delete the current page and its content")
        self.remove_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:pressed {
                background-color: #ac2925;
            }
        """)
        self.remove_page_btn.clicked.connect(self._on_remove_page)
        self._toolbar.addWidget(self.remove_page_btn)

        # Spacer to push Export and Help to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._toolbar.addWidget(spacer)

        # My Fonts button
        self.my_fonts_btn = QPushButton("My Fonts")
        self.my_fonts_btn.setFixedHeight(32)
        self.my_fonts_btn.setToolTip("Manage Letter Sets")
        self.my_fonts_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2D4EBF;
            }
            QPushButton:pressed {
                background-color: #1E3A9F;
            }
        """)
        self.my_fonts_btn.clicked.connect(self._on_my_fonts)
        self._toolbar.addWidget(self.my_fonts_btn)

        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setToolTip("Export as Handwriting")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #3E61DB;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #2D4EBF;
            }
            QPushButton:pressed {
                background-color: #1E3A9F;
            }
        """)
        self.export_btn.clicked.connect(self._on_export)
        self._toolbar.addWidget(self.export_btn)

        # Settings button
        self.settings_btn = self._make_tool_button("settings.svg", "Settings")
        self.settings_btn.clicked.connect(self._on_settings)
        self._toolbar.addWidget(self.settings_btn)

        # Help button
        self.help_btn = QToolButton()
        self.help_btn.setIcon(QIcon(str(get_icon("help-blue.svg"))))
        self.help_btn.setToolTip("Help & About")
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setIconSize(self.help_btn.size().scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio))
        self.help_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                border-radius: 16px;
            }
            QToolButton:hover {
                background: rgba(128, 128, 128, 0.2);
            }
        """)
        self._toolbar.addWidget(self.help_btn)

    # Page dimensions at 96 DPI
    PAGE_SIZES = {
        "A4": (794, 1123),
        "Letter": (816, 1056),
        "A3": (1123, 1587),
        "A5": (559, 794),
    }

    def _setup_editor(self):
        """Create a page-style editor with gray desk background and white page."""
        from PyQt6.QtCore import QSizeF
        from PyQt6.QtWidgets import QScrollArea, QFrame, QVBoxLayout

        # Gray desk background
        self._desk = QWidget()
        desk_bg = "#3a3a3a" if self._is_dark else "#c0c0c0"
        self._desk.setStyleSheet(f"background-color: {desk_bg};")

        desk_layout = QVBoxLayout(self._desk)
        desk_layout.setContentsMargins(40, 30, 40, 30)
        desk_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # Page Manager (handles multi-page layout)
        self._page_manager = PageManager(self._settings)
        self.editor = self._page_manager  # Compatibility alias

        # Apply page size
        page_name = self._settings.get("export", "paper_size", "a4").upper()
        if page_name == "LETTER":
            page_name = "Letter"
        page_w, page_h = self.PAGE_SIZES.get(page_name, self.PAGE_SIZES["A4"])
        self._page_manager.set_page_size(page_w, page_h)

        desk_layout.addWidget(self._page_manager)

        # Wrap desk in a scroll area
        from PyQt6.QtWidgets import QScrollArea, QFrame
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._desk)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_bg = "#3a3a3a" if self._is_dark else "#c0c0c0"
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {scroll_bg}; border: none; }}")

        self.setCentralWidget(scroll)

        # Install event filter for image-based font rendering
        self._page_manager.installEventFilter(self)

        # Connect signals for status bar updates
        self._page_manager.cursor_moved.connect(self._update_cursor_position)
        self._page_manager.text_changed.connect(self._update_char_count)
        self._page_manager.selection_changed.connect(self._update_char_count)

        # Apply saved page texture now that editor exists
        self._apply_page_texture()

    def _setup_statusbar(self):
        """Create status bar with page, language, char count, and cursor position."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        status_bg = "#2d2d2d" if self._is_dark else "#f0f0f0"
        status_border = "#555" if self._is_dark else "#d0d0d0"
        status_color = "#ffffff" if self._is_dark else "#000000"

        self.statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {status_bg};
                border-top: 1px solid {status_border};
                font-size: 12px;
                padding: 2px 8px;
            }}
            QLabel {{
                padding: 0 12px;
                color: {status_color};
            }}
        """)

        # Page indicator
        self.page_label = QLabel("Page 1/1")
        self.statusbar.addWidget(self.page_label)

        # Spacer
        spacer = QWidget()
        spacer.setFixedWidth(1)
        self.statusbar.addWidget(spacer, 1)

        # Language
        self.lang_label = QLabel("English")
        self.statusbar.addPermanentWidget(self.lang_label)

        # Character count
        self.char_label = QLabel("0 characters")
        self.statusbar.addPermanentWidget(self.char_label)

        # Cursor position
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.statusbar.addPermanentWidget(self.cursor_label)

    # --- Toolbar callbacks ---

    def eventFilter(self, obj, event):
        """Intercept key presses to insert glyph images when user font is active."""
        # Check if the event comes from any page in the page manager
        is_page = obj in self._page_manager._pages
        if is_page and event.type() == QEvent.Type.KeyPress:
            if self._active_user_font and event.text():
                char = event.text()
                if char and char.isprintable():
                    self._insert_glyph_image(char)
                    return True  # Consume the event
        return super().eventFilter(obj, event)

    def _insert_glyph_image(self, char: str):
        """Insert a character's bitmap image into the editor, scaled to font size."""
        manager = FontManager()
        img_path = manager.get_glyph_image_path(self._active_user_font, char)

        # Get current font size for scaling
        try:
            size = int(self.size_combo.currentText())
        except ValueError:
            size = 14

        # Scale image height to match font size in points (pixels ~ points on screen)
        # Use a multiplier that makes the glyph visually match the point size
        img_height = int(size * 1.8)

        cursor = self.editor.textCursor()

        if img_path:
            # Use a unique resource name per char + size to allow re-scaling
            resource_name = f"glyph://{self._active_user_font}/{ord(char)}/{size}"
            img = QImage(str(img_path))
            if not img.isNull():
                # Scale proportionally based on target height
                scale_factor = img_height / img.height()
                img_width = int(img.width() * scale_factor)

                self.editor.document().addResource(
                    2,  # QTextDocument.ResourceType.ImageResource
                    QUrl(resource_name),
                    img.scaled(img_width, img_height),
                )

                img_fmt = QTextImageFormat()
                img_fmt.setName(resource_name)
                img_fmt.setWidth(img_width)
                img_fmt.setHeight(img_height)
                cursor.insertImage(img_fmt)
            else:
                cursor.insertText(char)
        else:
            cursor.insertText("□")

    def _on_my_fonts(self):
        """Open the font creation dialog."""
        dialog = FontEditorDialog(self)
        if dialog.exec():
            # Refresh font list in dropdown
            self._refresh_font_list()

    def _on_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec():
            # Apply theme change if it changed
            new_theme = self._settings.get("editor", "theme", "system")
            if new_theme != self._theme_mode:
                self._switch_theme(new_theme)

            # Apply font size if changed
            new_size = self._settings.get("editor", "default_font_size", 14)
            self.size_combo.setCurrentText(str(new_size))

            # Apply default font if changed
            new_font = self._settings.get("editor", "default_font", "System Default")
            idx = self.font_combo.findText(new_font)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)

    def _get_default_dir(self) -> str:
        """Get the last used directory or default to Documents."""
        last_dir = self._settings.get("app", "last_file_directory", "")
        if last_dir and Path(last_dir).is_dir():
            return last_dir
        return str(Path.home() / "Documents")

    def _on_save(self):
        """Save the document as .mhw file."""
        if self._current_file:
            self._save_to_file(self._current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        """Save As - prompt for file path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Document",
            self._get_default_dir() + "/untitled.mhw",
            "MyHandWriting Files (*.mhw);;All Files (*)",
        )
        if file_path:
            path = Path(file_path)
            if not path.suffix:
                path = path.with_suffix(".mhw")
            self._save_to_file(path)

    def _on_export(self):
        """Export the document as PDF."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export as PDF",
            self._get_default_dir() + "/untitled.pdf",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if not path.suffix:
            path = path.with_suffix(".pdf")

        # Extract all pages data
        pages_data = self._extract_all_pages()

        try:
            success = export_to_pdf(pages_data, self._settings, path)
            if success:
                QMessageBox.information(
                    self, "Export Complete",
                    f"PDF exported successfully!\n\nSaved to: {path}",
                )
                self._settings.set("app", "last_file_directory", str(path.parent))
            else:
                QMessageBox.warning(self, "Export Failed", "Could not export PDF.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    def _save_to_file(self, file_path: Path):
        """Serialize the editor content with page format and save to file."""
        # Build page format from current settings
        page_format = PageFormat(
            paper_size=self._settings.get("export", "paper_size", "a4"),
            margin_horizontal=self._settings.get("editor", "margin_horizontal", 40),
            margin_vertical=self._settings.get("editor", "margin_vertical", 30),
            page_texture=self._settings.get("editor", "page_texture", "Texture"),
            page_style=self._settings.get("editor", "page_style", "Plain"),
            line_thickness=self._settings.get("editor", "line_thickness", 1),
            red_line_position=self._settings.get("editor", "red_line_position", 100),
        )

        # Extract pages data
        pages = self._extract_all_pages()
        content = serialize_document(pages, page_format)

        try:
            file_path.write_text(content, encoding="utf-8")
            self._current_file = file_path
            self._settings.set("app", "last_file_directory", str(file_path.parent))
            self._settings.set("app", "last_opened_file", str(file_path))
            self.setWindowTitle(f"MyHandWriting - {file_path.name}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")

    def _on_open(self):
        """Open a .mhw file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Document",
            self._get_default_dir(),
            "MyHandWriting Files (*.mhw);;All Files (*)",
        )
        if file_path:
            self._open_file(Path(file_path))

    def _open_file(self, file_path: Path):
        """Load a .mhw file into the editor."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open file:\n{e}")
            return

        document = parse_document(content)

        # Apply page format from the file
        pf = document.page_format
        self._settings.set("export", "paper_size", pf.paper_size)
        self._settings.set("editor", "margin_horizontal", pf.margin_horizontal)
        self._settings.set("editor", "margin_vertical", pf.margin_vertical)
        self._settings.set("editor", "page_texture", pf.page_texture)
        self._settings.set("editor", "page_style", pf.page_style)
        self._settings.set("editor", "line_thickness", pf.line_thickness)
        self._settings.set("editor", "red_line_position", pf.red_line_position)

        # Apply page size
        paper_text = pf.paper_size.upper() if pf.paper_size != "letter" else "Letter"
        page_w, page_h = self.PAGE_SIZES.get(paper_text, self.PAGE_SIZES["A4"])
        self._page_manager.set_page_size(page_w, page_h)

        # Apply texture
        self._texture_list = list_all_textures()
        self._apply_page_texture()

        # Load pages content
        self._load_document_pages(document.pages)

        self._current_file = file_path
        self._settings.set("app", "last_file_directory", str(file_path.parent))
        self._settings.set("app", "last_opened_file", str(file_path))
        self.setWindowTitle(f"MyHandWriting - {file_path.name}")

    def _extract_all_pages(self) -> list[PageData]:
        """Extract content from all pages as PageData list."""
        pages = []
        for page in self._page_manager._pages:
            lines = self._extract_lines_from_page(page)
            pages.append(PageData(lines=lines))
        return pages

    def _extract_lines_from_page(self, page) -> list[StyledLine]:
        """Extract styled lines from a single page widget."""
        lines = []
        doc = page.document()
        block = doc.begin()

        while block.isValid():
            alignment = "left"
            block_fmt = block.blockFormat()
            if block_fmt.alignment() & Qt.AlignmentFlag.AlignCenter:
                alignment = "center"
            elif block_fmt.alignment() & Qt.AlignmentFlag.AlignRight:
                alignment = "right"

            line = StyledLine(alignment=alignment, spans=[])
            it = block.begin()
            current_span_text = ""
            current_style = "system_default"
            current_size = 14

            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    char_fmt = fragment.charFormat()

                    if char_fmt.isImageFormat():
                        img_fmt = char_fmt.toImageFormat()
                        res_name = img_fmt.name()
                        parts = res_name.split("/")
                        frag_char = "□"
                        frag_style = "system_default"
                        frag_size = 14
                        if len(parts) >= 5:
                            try:
                                frag_char = chr(int(parts[3]))
                                frag_style = parts[2]
                                frag_size = int(parts[4])
                            except (ValueError, IndexError):
                                pass
                        elif len(parts) >= 4:
                            try:
                                frag_char = chr(int(parts[3]))
                                frag_style = parts[2]
                            except (ValueError, IndexError):
                                pass

                        if frag_style != current_style or frag_size != current_size:
                            if current_span_text:
                                line.spans.append(StyledSpan(
                                    text=current_span_text,
                                    font_style=current_style,
                                    font_size=current_size,
                                ))
                            current_span_text = frag_char
                            current_style = frag_style
                            current_size = frag_size
                        else:
                            current_span_text += frag_char
                    else:
                        frag_text = fragment.text()
                        frag_style = "system_default"
                        frag_size = 14

                        families = char_fmt.fontFamilies()
                        if families:
                            family = families[0] if isinstance(families, list) else str(families)
                            if family not in ("Courier New", "monospace"):
                                frag_style = family

                        ps = char_fmt.fontPointSize()
                        if ps > 0:
                            frag_size = int(ps)

                        if frag_style != current_style or frag_size != current_size:
                            if current_span_text:
                                line.spans.append(StyledSpan(
                                    text=current_span_text,
                                    font_style=current_style,
                                    font_size=current_size,
                                ))
                            current_span_text = frag_text
                            current_style = frag_style
                            current_size = frag_size
                        else:
                            current_span_text += frag_text

                it += 1

            if current_span_text:
                line.spans.append(StyledSpan(
                    text=current_span_text,
                    font_style=current_style,
                    font_size=current_size,
                ))

            if not line.spans:
                line.spans.append(StyledSpan(text=""))

            lines.append(line)
            block = block.next()

        return lines

    def _load_document_pages(self, pages: list[PageData]):
        """Load multiple pages of content into the page manager."""
        from PyQt6.QtGui import QTextImageFormat

        self._page_manager.clear()
        manager = FontManager()

        for page_idx, page_data in enumerate(pages):
            if page_idx > 0:
                # Add a new page for subsequent pages
                self._page_manager._add_new_page()
                self._page_manager._active_page_index = page_idx

            page_widget = self._page_manager._pages[page_idx]
            cursor = page_widget.textCursor()

            for line_idx, line in enumerate(page_data.lines):
                if line_idx > 0:
                    cursor.insertBlock()

                # Set alignment
                block_fmt = cursor.blockFormat()
                if line.alignment == "center":
                    block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
                elif line.alignment == "right":
                    block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
                cursor.setBlockFormat(block_fmt)

                for span in line.spans:
                    is_user_font = span.font_style != "system_default"
                    img_height = int(span.font_size * 1.8)

                    for char in span.text:
                        if is_user_font:
                            img_path = manager.get_glyph_image_path(span.font_style, char)
                            if img_path:
                                from PyQt6.QtCore import QUrl
                                resource_name = f"glyph://{span.font_style}/{ord(char)}/{span.font_size}"
                                img = QImage(str(img_path))
                                if not img.isNull():
                                    scale_factor = img_height / img.height()
                                    img_width = int(img.width() * scale_factor)
                                    page_widget.document().addResource(
                                        2, QUrl(resource_name),
                                        img.scaled(img_width, img_height),
                                    )
                                    img_fmt = QTextImageFormat()
                                    img_fmt.setName(resource_name)
                                    img_fmt.setWidth(img_width)
                                    img_fmt.setHeight(img_height)
                                    cursor.insertImage(img_fmt)
                                    continue
                            cursor.insertText("□")
                        else:
                            from PyQt6.QtGui import QTextCharFormat
                            fmt = QTextCharFormat()
                            fmt.setFontFamilies(["Courier New", "monospace"])
                            fmt.setFontPointSize(span.font_size)
                            cursor.insertText(char, fmt)

        # Set active font from last span
        if pages and pages[-1].lines and pages[-1].lines[-1].spans:
            last_style = pages[-1].lines[-1].spans[-1].font_style
            if last_style != "system_default":
                self._active_user_font = last_style
                idx = self.font_combo.findText(last_style)
                if idx >= 0:
                    self.font_combo.blockSignals(True)
                    self.font_combo.setCurrentIndex(idx)
                    self.font_combo.blockSignals(False)

        # Focus first page
        self._page_manager._active_page_index = 0
        if self._page_manager._pages:
            self._page_manager._pages[0].setFocus()

    def _extract_blocks_from_editor(self) -> list[StyledLine]:
        """Extract styled lines from the active page (legacy compatibility)."""
        return self._extract_lines_from_page(self._page_manager.active_page)
        while block.isValid():
            # Get alignment
            alignment = "left"
            block_fmt = block.blockFormat()
            if block_fmt.alignment() & Qt.AlignmentFlag.AlignCenter:
                alignment = "center"
            elif block_fmt.alignment() & Qt.AlignmentFlag.AlignRight:
                alignment = "right"

            line = StyledLine(alignment=alignment, spans=[])

            # Iterate through text fragments in the block
            it = block.begin()
            current_span_text = ""
            current_style = "system_default"
            current_size = 14

            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    char_fmt = fragment.charFormat()

                    if char_fmt.isImageFormat():
                        # Extract char and style from image resource name
                        img_fmt = char_fmt.toImageFormat()
                        res_name = img_fmt.name()
                        parts = res_name.split("/")
                        frag_char = "□"
                        frag_style = "system_default"
                        frag_size = 14
                        if len(parts) >= 5:
                            try:
                                frag_char = chr(int(parts[3]))
                                frag_style = parts[2]
                                frag_size = int(parts[4])
                            except (ValueError, IndexError):
                                pass
                        elif len(parts) >= 4:
                            try:
                                frag_char = chr(int(parts[3]))
                                frag_style = parts[2]
                            except (ValueError, IndexError):
                                pass

                        # Check if style/size changed — start new span
                        if frag_style != current_style or frag_size != current_size:
                            if current_span_text:
                                line.spans.append(StyledSpan(
                                    text=current_span_text,
                                    font_style=current_style,
                                    font_size=current_size,
                                ))
                            current_span_text = frag_char
                            current_style = frag_style
                            current_size = frag_size
                        else:
                            current_span_text += frag_char
                    else:
                        # Text fragment
                        frag_text = fragment.text()
                        frag_style = "system_default"
                        frag_size = 14

                        families = char_fmt.fontFamilies()
                        if families:
                            family = families[0] if isinstance(families, list) else str(families)
                            if family not in ("Courier New", "monospace"):
                                frag_style = family

                        ps = char_fmt.fontPointSize()
                        if ps > 0:
                            frag_size = int(ps)

                        # Check if style/size changed
                        if frag_style != current_style or frag_size != current_size:
                            if current_span_text:
                                line.spans.append(StyledSpan(
                                    text=current_span_text,
                                    font_style=current_style,
                                    font_size=current_size,
                                ))
                            current_span_text = frag_text
                            current_style = frag_style
                            current_size = frag_size
                        else:
                            current_span_text += frag_text

                it += 1

            # Flush remaining span
            if current_span_text:
                line.spans.append(StyledSpan(
                    text=current_span_text,
                    font_style=current_style,
                    font_size=current_size,
                ))

            # If no spans, add empty one
            if not line.spans:
                line.spans.append(StyledSpan(text=""))

            lines.append(line)
            block = block.next()

        return lines

    def _load_blocks_into_editor(self, lines: list[StyledLine]):
        """Load styled lines into the editor, rendering each span with its font/size."""
        self.editor.clear()
        cursor = self.editor.textCursor()
        manager = FontManager()

        for i, line in enumerate(lines):
            if i > 0:
                cursor.insertBlock()

            # Set alignment
            block_fmt = cursor.blockFormat()
            if line.alignment == "center":
                block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif line.alignment == "right":
                block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
            else:
                block_fmt.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cursor.setBlockFormat(block_fmt)

            for span in line.spans:
                is_user_font = span.font_style != "system_default"
                img_height = int(span.font_size * 1.8)

                for char in span.text:
                    if is_user_font:
                        img_path = manager.get_glyph_image_path(span.font_style, char)
                        if img_path:
                            resource_name = f"glyph://{span.font_style}/{ord(char)}/{span.font_size}"
                            img = QImage(str(img_path))
                            if not img.isNull():
                                scale_factor = img_height / img.height()
                                img_width = int(img.width() * scale_factor)

                                self.editor.document().addResource(
                                    2, QUrl(resource_name),
                                    img.scaled(img_width, img_height),
                                )

                                img_fmt = QTextImageFormat()
                                img_fmt.setName(resource_name)
                                img_fmt.setWidth(img_width)
                                img_fmt.setHeight(img_height)
                                cursor.insertImage(img_fmt)
                                continue

                        cursor.insertText("□")
                    else:
                        fmt = QTextCharFormat()
                        fmt.setFontFamilies(["Courier New", "monospace"])
                        fmt.setFontPointSize(span.font_size)
                        cursor.insertText(char, fmt)

        # Set the active font from the last span's style
        if lines and lines[-1].spans:
            last_style = lines[-1].spans[-1].font_style
            if last_style != "system_default":
                self._active_user_font = last_style
                idx = self.font_combo.findText(last_style)
                if idx >= 0:
                    self.font_combo.blockSignals(True)
                    self.font_combo.setCurrentIndex(idx)
                    self.font_combo.blockSignals(False)

    def _refresh_font_list(self):
        """Reload available user fonts into the font combo."""
        manager = FontManager()
        self.font_combo.blockSignals(True)
        self.font_combo.clear()
        self.font_combo.addItem("System Default")

        self._loaded_font_families = {}  # combo index -> font family name
        self._loaded_font_names = {}  # combo index -> font name (for image lookup)

        for font_info in manager.list_fonts():
            # Register .ttf with Qt if available (for fallback)
            ttf_path = manager.fonts_dir / f"{font_info['name']}.ttf"
            if ttf_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(ttf_path))
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self._loaded_font_families[self.font_combo.count()] = families[0]
            self._loaded_font_names[self.font_combo.count()] = font_info["name"]
            self.font_combo.addItem(font_info["name"])

        self.font_combo.blockSignals(False)

    def _on_font_changed(self, index: int):
        """Switch between system font and user handwriting font."""
        if index == 0:
            # System Default - use normal text rendering
            self._active_user_font = None
            self._settings.set("editor", "default_font", "System Default")
            families = ["Courier New", "monospace"]
            fmt = QTextCharFormat()
            fmt.setFontFamilies(families)
            self._apply_format(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
            doc_font = self.editor.document().defaultFont()
            doc_font.setFamilies(families)
            self.editor.document().setDefaultFont(doc_font)
        else:
            # User font - use image-based rendering
            if index in self._loaded_font_names:
                self._active_user_font = self._loaded_font_names[index]
                self._settings.set("editor", "default_font", self._active_user_font)
                # If there's a selection, replace it with glyph images
                self._replace_selection_with_glyphs()

    def _on_size_changed(self, size_text: str):
        """Apply selected font size to current selection and set as default for new text."""
        try:
            size = int(size_text)
        except ValueError:
            return
        if size < 1 or size > 200:
            return

        self._settings.set("editor", "default_font_size", size)

        if self._active_user_font:
            # For user fonts, resize glyph images in selection
            self._replace_selection_with_glyphs()
        else:
            # For system fonts, apply text formatting
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            self._apply_format(fmt)
            self.editor.mergeCurrentCharFormat(fmt)
            doc_font = self.editor.document().defaultFont()
            doc_font.setPointSize(size)
            self.editor.document().setDefaultFont(doc_font)

    def _replace_selection_with_glyphs(self):
        """Replace selected content with glyph images at current size."""
        if not self._active_user_font:
            return

        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return

        # Get font size
        try:
            size = int(self.size_combo.currentText())
        except ValueError:
            size = 14

        img_height = int(size * 1.8)
        manager = FontManager()

        # Walk through the selection to collect characters
        # (including those represented as images via their resource names)
        sel_start = cursor.selectionStart()
        sel_end = cursor.selectionEnd()
        chars_to_insert = []

        walk_cursor = QTextCursor(self.editor.document())
        walk_cursor.setPosition(sel_start)

        while walk_cursor.position() < sel_end:
            walk_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
            fragment = walk_cursor.selection()
            fmt = walk_cursor.charFormat()

            if fmt.isImageFormat():
                # Extract the original character from the resource name
                img_fmt = fmt.toImageFormat()
                res_name = img_fmt.name()
                # Format: "glyph://FontName/ordinal/size"
                parts = res_name.split("/")
                if len(parts) >= 4:
                    try:
                        char_ord = int(parts[3])
                        chars_to_insert.append(chr(char_ord))
                    except (ValueError, IndexError):
                        chars_to_insert.append("□")
                else:
                    chars_to_insert.append("□")
            else:
                text = fragment.toPlainText()
                if text:
                    chars_to_insert.append(text[-1])

            # Reset anchor for next iteration
            walk_cursor.clearSelection()

        if not chars_to_insert:
            return

        # Now remove selection and re-insert with new size
        cursor.removeSelectedText()

        for char in chars_to_insert:
            if char == '\n' or char == '\u2029':
                cursor.insertText('\n')
                continue
            if char == ' ':
                cursor.insertText(' ')
                continue

            img_path = manager.get_glyph_image_path(self._active_user_font, char)
            if img_path:
                resource_name = f"glyph://{self._active_user_font}/{ord(char)}/{size}"
                img = QImage(str(img_path))
                if not img.isNull():
                    scale_factor = img_height / img.height()
                    img_width = int(img.width() * scale_factor)

                    self.editor.document().addResource(
                        2, QUrl(resource_name),
                        img.scaled(img_width, img_height),
                    )

                    img_format = QTextImageFormat()
                    img_format.setName(resource_name)
                    img_format.setWidth(img_width)
                    img_format.setHeight(img_height)
                    cursor.insertImage(img_format)
                else:
                    cursor.insertText(char)
            else:
                cursor.insertText("□" if char.isprintable() and char != ' ' else char)

    def _on_align(self, alignment: Qt.AlignmentFlag):
        """Apply text alignment to the current paragraph."""
        self.editor.setAlignment(alignment)

    def _on_page_style_changed(self, style: str):
        """Update page style and re-render."""
        self._settings.set("editor", "page_style", style)
        self._apply_page_texture()

    def _on_remove_page(self):
        """Remove the current page (not allowed for page 1)."""
        current = self._page_manager.get_current_page()
        total = self._page_manager.get_total_pages()

        if current == 1:
            QMessageBox.information(self, "Cannot Remove", "The first page cannot be removed.")
            return

        if total <= 1:
            return

        reply = QMessageBox.question(
            self, "Remove Page",
            f"Delete page {current} and all its content?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._page_manager.remove_page(current - 1)  # 0-based index

    def _on_customize_page(self):
        """Open the page customization dialog."""
        dialog = PageCustomizeDialog(self._settings, self)
        if dialog.exec():
            # Apply page size change
            paper = self._settings.get("export", "paper_size", "a4")
            paper_text = paper.upper() if paper != "letter" else "Letter"
            page_w, page_h = self.PAGE_SIZES.get(paper_text, self.PAGE_SIZES["A4"])
            self._page_manager.set_page_size(page_w, page_h)

            # Refresh texture list and apply
            self._texture_list = list_all_textures()
            self._apply_page_texture()

    def _populate_page_textures(self):
        """Load the texture list from available textures."""
        self._texture_list = list_all_textures()

    def _on_page_texture_changed(self, index: int):
        """Apply selected page texture (called from customize dialog)."""
        self._apply_page_texture()

    def _apply_page_texture(self):
        """Apply the current page texture and style to all pages."""
        border_color = "#555555" if self._is_dark else "#999999"

        # Find the texture by name from settings
        saved_texture = self._settings.get("editor", "page_texture", "Plain White")
        texture_path = None
        for t in self._texture_list:
            if t["name"] == saved_texture:
                texture_path = t["path"]
                break

        # Set texture via PageManager (applies to all pages)
        if texture_path is None:
            self._page_manager.set_page_texture(None)
        elif texture_path == "plain_white":
            self._page_manager.set_page_texture("plain_white")
        else:
            self._page_manager.set_page_texture(str(texture_path))

    def _apply_format(self, fmt: QTextCharFormat):
        """Merge a character format into the current selection or cursor."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    # --- Status bar callbacks ---

    def _update_cursor_position(self):
        """Update cursor position and page number in status bar."""
        cursor = self._page_manager.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.cursor_label.setText(f"Ln {line}, Col {col}")

        # Update page number
        current_page = self._page_manager.get_current_page()
        total_pages = self._page_manager.get_total_pages()
        self.page_label.setText(f"Page {current_page}/{total_pages}")

    def _update_char_count(self):
        """Update character count in status bar (selected/total)."""
        total = len(self._page_manager.toPlainText())
        cursor = self._page_manager.textCursor()
        selected = len(cursor.selectedText())

        if selected > 0:
            self.char_label.setText(f"{selected}/{total} characters")
        else:
            self.char_label.setText(f"{total} characters")

    # --- Window events ---

    def closeEvent(self, event):
        """Save window size on close."""
        self._settings.set("app", "window_width", self.width())
        self._settings.set("app", "window_height", self.height())
        event.accept()
