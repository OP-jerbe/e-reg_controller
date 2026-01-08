import sys
from typing import NoReturn

from PySide6.QtWidgets import QApplication

from src.controller.controller import Controller
from src.model.model import Model
from src.view.main_window import MainWindow


def run_app() -> NoReturn:
    app = QApplication([])
    model = Model()
    view = MainWindow(model)
    _ = Controller(model, view)
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
