from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow
from qt_material import apply_stylesheet

import src.helpers.helpers as h
from src.model.ereg_driver import eReg


class MainWindow(QMainWindow):
    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.model = model
        self.create_gui()

    def create_gui(self) -> None:
        ver = h.get_app_version()
        root_dir: Path = h.get_root_dir()
        icon_path: str = str(root_dir / 'assets' / 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(f'e-Reg Controller v{ver}')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )
        self.resize(600, 600)
