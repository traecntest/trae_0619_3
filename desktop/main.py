# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from desktop.controllers.main_controller import MainController
from desktop.core.config import desktop_config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(desktop_config.app_name)
    app.setApplicationVersion(desktop_config.app_version)

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }
    """)

    controller = MainController()
    controller.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
