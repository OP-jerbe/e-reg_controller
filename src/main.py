import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from src.controller.controller import Controller
from src.model.ereg_driver import eReg
from src.view.main_window import MainWindow


def run_app() -> NoReturn:
    app = QApplication([])
    ereg = eReg()
    mw = MainWindow(ereg)
    _ = Controller(ereg, mw)
    mw.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
