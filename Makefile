# MyHandWriting - Build System
# Usage:
#   make setup      - Create venv and install dependencies
#   make run        - Run the app in development mode
#   make build      - Build macOS .app bundle
#   make clean      - Remove build artifacts
#   make lint       - Run linter
#   make all        - Setup + Build

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
APP_NAME := MyHandWriting
ICON_SRC := src/myhandwriting/resources/icons/icon.png
ICON_ICNS := icon.icns
ENTRY := src/myhandwriting/__main__.py

.PHONY: all setup run build clean lint icon help

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

all: setup build ## Full setup and build

setup: ## Create virtual environment and install dependencies
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Setup complete!"

run: ## Run the app in development mode
	$(PYTHON) -m myhandwriting

icon: ## Generate macOS .icns icon from PNG
	@echo "Generating macOS icon..."
	@mkdir -p /tmp/$(APP_NAME).iconset
	@sips -z 16 16 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_16x16.png 2>/dev/null
	@sips -z 32 32 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_16x16@2x.png 2>/dev/null
	@sips -z 32 32 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_32x32.png 2>/dev/null
	@sips -z 64 64 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_32x32@2x.png 2>/dev/null
	@sips -z 128 128 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_128x128.png 2>/dev/null
	@sips -z 256 256 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_128x128@2x.png 2>/dev/null
	@sips -z 256 256 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_256x256.png 2>/dev/null
	@sips -z 512 512 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_256x256@2x.png 2>/dev/null
	@sips -z 512 512 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_512x512.png 2>/dev/null
	@sips -z 1024 1024 $(ICON_SRC) --out /tmp/$(APP_NAME).iconset/icon_512x512@2x.png 2>/dev/null
	@iconutil -c icns /tmp/$(APP_NAME).iconset -o $(ICON_ICNS)
	@rm -rf /tmp/$(APP_NAME).iconset
	@echo "Icon created: $(ICON_ICNS)"

build: icon ## Build macOS .app bundle using PyInstaller
	@echo "Building $(APP_NAME).app..."
	$(VENV)/bin/pyinstaller \
		--name "$(APP_NAME)" \
		--windowed \
		--icon $(ICON_ICNS) \
		--add-data "src/myhandwriting/resources:myhandwriting/resources" \
		--hidden-import myhandwriting \
		--hidden-import myhandwriting.app \
		--hidden-import myhandwriting.fonts \
		--hidden-import myhandwriting.fonts.brushes \
		--hidden-import myhandwriting.fonts.canvas \
		--hidden-import myhandwriting.fonts.editor \
		--hidden-import myhandwriting.fonts.generator \
		--hidden-import myhandwriting.fonts.manager \
		--hidden-import myhandwriting.page_editor \
		--hidden-import myhandwriting.page_textures \
		--hidden-import myhandwriting.page_style \
		--hidden-import myhandwriting.fileformat \
		--hidden-import myhandwriting.settings \
		--hidden-import myhandwriting.settings_dialog \
		--hidden-import myhandwriting.appdata \
		--hidden-import myhandwriting.exporter \
		--hidden-import myhandwriting.resources \
		$(ENTRY)
	@echo ""
	@echo "Build complete!"
	@echo "App: dist/$(APP_NAME).app"
	@echo "Run: open dist/$(APP_NAME).app"

lint: ## Run ruff linter
	$(VENV)/bin/ruff check src/

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.spec $(ICON_ICNS)
	rm -rf src/myhandwriting.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
