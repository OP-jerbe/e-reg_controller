from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet


class BleedSupplyWindow(QMainWindow):
    start_bleed_supply_sig = Signal(int)  # rate (blips/hour)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.create_gui()
        self.rate_sb.setFocus()
        self.start_clicked: bool = False

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Bleed Gas Supply')
        self.setFixedSize(300, 130)
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit {color: lightgreen;}'
        )

        # Create the widgets
        self.rate_label = QLabel('Blips/Hour')
        self.rate_sb = QSpinBox()
        self.rate_sb.setRange(1, 60)
        self.rate_sb.setValue(2)
        self.start_btn = QPushButton('Start')
        self.start_btn.clicked.connect(self.handle_connect_clicked)
        self.start_btn.setAutoDefault(True)

        # Set the layout
        main_layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        input_layout = QHBoxLayout()
        label_layout.addWidget(self.rate_label, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.rate_sb)
        main_layout.addLayout(label_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.start_btn)
        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def handle_connect_clicked(self) -> None:
        self.start_clicked = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.start_clicked:
            rate = self.rate_sb.value()
            self.start_bleed_supply_sig.emit(rate)
        event.accept()
        super().closeEvent(event)
