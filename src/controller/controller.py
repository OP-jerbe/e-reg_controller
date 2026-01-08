from src.model.model import Model
from src.view.main_window import MainWindow


class Controller:
    def __init__(self, model: Model, view: MainWindow) -> None:
        self.model = model
        self.view = view
