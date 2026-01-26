from socket import SocketType

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QCloseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet


class ReconnectWindow(QMainWindow):
    try_to_connect_sig = Signal(str, str)  # ip address, port

    def __init__(
        self, parent: QWidget, ip: str, port: int, sock: SocketType | None
    ) -> None:
        super().__init__(parent)
        self.ip = ip
        self.port = str(port)
        self.sock = sock
        self.create_gui()
        self.connect_btn.setFocus()
        self.connect_clicked: bool = False

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Connect to e-Reg')
        self.setFixedSize(300, 130)
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit {color: lightgreen;}'
        )

        # Create validator for ip and port inputs
        ip_regex = QRegularExpression(r'[0-9.]*')
        ip_validator = QRegularExpressionValidator(ip_regex)
        port_regex = QRegularExpression(r'[0-9]*')
        port_validator = QRegularExpressionValidator(port_regex)

        # Create the widgets
        self.ip_label = QLabel('IP ADDRESS')
        self.ip_entry = QLineEdit(self.ip)
        self.ip_entry.setValidator(ip_validator)
        self.port_label = QLabel('PORT')
        self.port_entry = QLineEdit(self.port)
        self.port_entry.setValidator(port_validator)
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.handle_connect_clicked)
        self.connect_btn.setAutoDefault(True)

        # Disable the buttons and entry boxes if there is already a socket connection.
        if self.sock:
            self.ip_entry.setEnabled(False)
            self.port_entry.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText('Connected')

        # Set the layout
        main_layout = QVBoxLayout()
        label_layout = QHBoxLayout()
        input_layout = QHBoxLayout()
        label_layout.addWidget(self.ip_label, alignment=Qt.AlignmentFlag.AlignCenter)
        label_layout.addWidget(self.port_label, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.ip_entry)
        input_layout.addWidget(self.port_entry)
        main_layout.addLayout(label_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.connect_btn)
        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def handle_connect_clicked(self) -> None:
        self.connect_clicked = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.connect_clicked:
            ip = self.ip_entry.text()
            port = self.port_entry.text()
            self.try_to_connect_sig.emit(ip, port)
        event.accept()
        super().closeEvent(event)
