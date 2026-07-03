"""Entry point for MyHandWriting application."""

import sys

from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
from PyQt6.QtWidgets import QApplication

from myhandwriting.app import MainWindow


def _message_handler(msg_type: QtMsgType, context, message: str):
    """Filter out noisy Qt/macOS warnings."""
    if "minimum bearings" in message:
        return
    if "overrides the method identifier" in message:
        return
    # Print all other messages normally
    print(message)


def main():
    qInstallMessageHandler(_message_handler)
    app = QApplication(sys.argv)
    app.setApplicationName("MyHandWriting")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
