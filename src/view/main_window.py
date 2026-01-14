from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

import src.helpers.helpers as h
from src.model.ereg_driver import eReg


class MainWindow(QMainWindow):
    ereg_connected_sig = Signal()
    closing_sig = Signal()

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self.create_gui()

    def create_gui(self) -> None:
        ver = h.get_app_version()
        self.setWindowTitle(f'e-Reg Controller v{ver}')
        icon = h.get_icon()
        self.setWindowIcon(icon)
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )
        self.resize(600, 600)

        pressure_setting_label = QLabel('Pressure Setting')
        self.pressure_reading_label = QLabel()
        self.pressure_setting_le = QLineEdit()

        # --- Create the layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.container_frame = QFrame()
        self.container_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.container_frame.setLineWidth(2)

        frame_layout = QVBoxLayout(self.container_frame)
        frame_layout.addWidget(pressure_setting_label)
        frame_layout.addWidget(self.pressure_reading_label)
        frame_layout.addWidget(self.pressure_setting_le)

        main_layout.addWidget(self.container_frame)

    def update_pressure_reading(self, pressure: float) -> None:
        """
        Updates the pressure reading on the UI.

        Args:
            pressure (float): The pressure reading from the e-reg in PSI.
        """
        pressure_mbar = h.convert_psi_to_mbar(pressure)
        text = f'{pressure_mbar:.0f} mBar'
        self.pressure_reading_label.setText(text)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing_sig.emit()
        event.accept()
        super().closeEvent(event)
