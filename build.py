#!/usr/bin/env python3
"""Cross-platform build script for MyHandWriting.

Usage:
    python build.py setup     - Create venv and install dependencies
    python build.py run       - Run the app in development mode
    python build.py build     - Build platform-specific executable
    python build.py clean     - Remove build artifacts
    python build.py all       - Setup + Build
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "MyHandWriting"
ROOT = Path(__file__).parent
VENV_DIR = ROOT / ".venv"
ENTRY = ROOT / "src" / "myhandwriting" / "__main__.py"
ICON_SRC = ROOT / "src" / "myhandwriting" / "resources" / "icons" / "icon.png"
RESOURCES = ROOT / "src" / "myhandwriting" / "resources"

SYSTEM = platform.system()  # Darwin, Linux, Windows


def get_python():
    """Get the venv python path."""
    if SYSTEM == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_pip():
    """Get the venv pip path."""
    if SYSTEM == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def get_pyinstaller():
    """Get the venv pyinstaller path."""
    if SYSTEM == "Windows":
        return VENV_DIR / "Scripts" / "pyinstaller.exe"
    return VENV_DIR / "bin" / "pyinstaller"


def run_cmd(cmd, **kwargs):
    """Run a command and exit on failure."""
    print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  ✗ Command failed with exit code {result.returncode}")
        sys.exit(1)


def cmd_setup():
    """Create virtual environment and install dependencies."""
    print(f"\n{'='*50}")
    print(f"Setting up {APP_NAME} ({SYSTEM})")
    print(f"{'='*50}\n")

    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        run_cmd([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print("Virtual environment already exists.")

    print("\nInstalling dependencies...")
    run_cmd([str(get_pip()), "install", "--upgrade", "pip"])
    run_cmd([str(get_pip()), "install", "-e", ".[dev]"], cwd=str(ROOT))

    print("\n✓ Setup complete!")
    print(f"  Run with: python build.py run")


def cmd_run():
    """Run the app in development mode."""
    python = get_python()
    if not python.exists():
        print("Error: Virtual environment not found. Run 'python build.py setup' first.")
        sys.exit(1)
    run_cmd([str(python), "-m", "myhandwriting"], cwd=str(ROOT))


def cmd_build():
    """Build the platform-specific executable."""
    pyinstaller = get_pyinstaller()
    if not pyinstaller.exists():
        print("Error: PyInstaller not found. Run 'python build.py setup' first.")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"Building {APP_NAME} for {SYSTEM}")
    print(f"{'='*50}\n")

    # Platform-specific icon
    icon_arg = _prepare_icon()

    # Data separator differs per platform
    sep = ";" if SYSTEM == "Windows" else ":"

    cmd = [
        str(pyinstaller),
        "--name", APP_NAME,
        "--windowed",
        "--add-data", f"{RESOURCES}{sep}myhandwriting/resources",
        "--hidden-import", "myhandwriting",
        "--hidden-import", "myhandwriting.app",
        "--hidden-import", "myhandwriting.fonts",
        "--hidden-import", "myhandwriting.fonts.brushes",
        "--hidden-import", "myhandwriting.fonts.canvas",
        "--hidden-import", "myhandwriting.fonts.editor",
        "--hidden-import", "myhandwriting.fonts.generator",
        "--hidden-import", "myhandwriting.fonts.manager",
        "--hidden-import", "myhandwriting.page_editor",
        "--hidden-import", "myhandwriting.page_textures",
        "--hidden-import", "myhandwriting.page_style",
        "--hidden-import", "myhandwriting.fileformat",
        "--hidden-import", "myhandwriting.settings",
        "--hidden-import", "myhandwriting.settings_dialog",
        "--hidden-import", "myhandwriting.appdata",
        "--hidden-import", "myhandwriting.exporter",
        "--hidden-import", "myhandwriting.resources",
        str(ENTRY),
    ]

    if icon_arg:
        cmd.insert(4, "--icon")
        cmd.insert(5, icon_arg)

    run_cmd(cmd, cwd=str(ROOT))

    print(f"\n✓ Build complete!")
    if SYSTEM == "Darwin":
        print(f"  App: dist/{APP_NAME}.app")
        print(f"  Run: open dist/{APP_NAME}.app")
    elif SYSTEM == "Windows":
        print(f"  Exe: dist\\{APP_NAME}\\{APP_NAME}.exe")
    else:
        print(f"  Binary: dist/{APP_NAME}/{APP_NAME}")


def _prepare_icon() -> str:
    """Prepare platform-specific icon and return the path."""
    if SYSTEM == "Darwin":
        icns_path = ROOT / "icon.icns"
        if not icns_path.exists():
            print("Generating macOS icon...")
            iconset = Path("/tmp") / f"{APP_NAME}.iconset"
            iconset.mkdir(exist_ok=True)

            sizes = [
                (16, "icon_16x16.png"),
                (32, "icon_16x16@2x.png"),
                (32, "icon_32x32.png"),
                (64, "icon_32x32@2x.png"),
                (128, "icon_128x128.png"),
                (256, "icon_128x128@2x.png"),
                (256, "icon_256x256.png"),
                (512, "icon_256x256@2x.png"),
                (512, "icon_512x512.png"),
                (1024, "icon_512x512@2x.png"),
            ]

            for size, name in sizes:
                run_cmd([
                    "sips", "-z", str(size), str(size),
                    str(ICON_SRC), "--out", str(iconset / name)
                ])

            run_cmd(["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)])
            shutil.rmtree(iconset)

        return str(icns_path)

    elif SYSTEM == "Windows":
        # Windows needs .ico — use the PNG directly (PyInstaller handles conversion)
        return str(ICON_SRC)

    else:
        # Linux — use PNG directly
        return str(ICON_SRC)


def cmd_clean():
    """Remove build artifacts."""
    print("Cleaning build artifacts...")
    dirs_to_remove = ["build", "dist", "src/myhandwriting.egg-info"]
    files_to_remove = ["icon.icns", f"{APP_NAME}.spec"]

    for d in dirs_to_remove:
        path = ROOT / d
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed {d}/")

    for f in files_to_remove:
        path = ROOT / f
        if path.exists():
            path.unlink()
            print(f"  Removed {f}")

    # Remove __pycache__
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache)

    print("✓ Cleaned!")


def cmd_all():
    """Full setup and build."""
    cmd_setup()
    cmd_build()


def main():
    commands = {
        "setup": cmd_setup,
        "run": cmd_run,
        "build": cmd_build,
        "clean": cmd_clean,
        "all": cmd_all,
    }

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        print("Available commands:")
        for name, func in commands.items():
            print(f"  {name:10s} - {func.__doc__}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands.keys())}")
        sys.exit(1)

    commands[cmd]()


if __name__ == "__main__":
    main()
