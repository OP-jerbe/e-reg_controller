from src.model.model import eReg
from src.view.main_window import MainWindow


class Controller:
    def __init__(self, model: eReg, view: MainWindow) -> None:
        self.model = model
        self.view = view
