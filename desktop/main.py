# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from desktop.controllers.main_controller import MainController
from desktop.core.config import desktop_config


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(desktop_config.app_name)
    app.setApplicationVersion(desktop_config.app_version)
    app.setOrganizationName("InvoiceSystem")

    font = QFont("Microsoft YaHei", 10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    app.setStyleSheet("""
        QWidget {
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            color: #333;
        }
        QToolTip {
            background-color: #fff;
            color: #333;
            border: 1px solid #ddd;
            padding: 4px 8px;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background: #f0f0f0;
            width: 10px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #bdbdbd;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #9e9e9e;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            background: #f0f0f0;
            height: 10px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: #bdbdbd;
            min-width: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #9e9e9e;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
    """)

    try:
        controller = MainController()
        controller.show()
    except Exception as e:
        QMessageBox.critical(
            None,
            "启动失败",
            f"桌面客户端启动失败：\n\n{str(e)}\n\n"
            f"请确保：\n"
            f"1. 已安装所有依赖: pip install -r requirements.txt\n"
            f"2. PySide6 已正确安装\n"
            f"3. 系统支持图形界面显示"
        )
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
