from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QCloseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class PressureSweepWindow(QMainWindow):
    start_sweep_sig = Signal(str, str, str)  # span, rate, direction
    span_error_sig = Signal(int, str)  # span, direction

    def __init__(self, parent: QWidget, current_pressure: int) -> None:
        super().__init__(parent)
        self.mw = parent
        self.current_pressure = current_pressure
        self.create_gui()
        self.start_btn.setFocus()
        self.start_clicked: bool = False

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Pressure Sweep')
        self.resize(250, 100)

        # Create validator for ip and port inputs
        entry_regex = QRegularExpression(r'[0-9.]*')
        entry_validator = QRegularExpressionValidator(entry_regex)

        # Create the widgets
        self.span_label = QLabel('Span (mBar)')
        self.span_entry = QLineEdit('400')
        self.span_entry.setValidator(entry_validator)

        self.rate_label = QLabel('Rate (mBar/sec)')
        self.rate_entry = QLineEdit('2')
        self.rate_entry.setValidator(entry_validator)

        self.h2l_rb = QRadioButton('High-to-Low')
        self.h2l_rb.setChecked(True)
        self.l2h_rb = QRadioButton('Low-to-High')

        self.rb_group = QButtonGroup()
        self.rb_group.addButton(self.h2l_rb, 101)
        self.rb_group.addButton(self.l2h_rb, 102)

        self.start_btn = QPushButton('Start')
        self.start_btn.clicked.connect(self.handle_start_clicked)
        self.start_btn.setAutoDefault(True)

        rb_group_box = QGroupBox('Sweep Direction')

        # Set the layout
        label_layout = QHBoxLayout()
        label_layout.addWidget(self.span_label, alignment=Qt.AlignmentFlag.AlignCenter)
        label_layout.addWidget(self.rate_label, alignment=Qt.AlignmentFlag.AlignCenter)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.span_entry)
        input_layout.addWidget(self.rate_entry)

        h2l_layout = QHBoxLayout()
        h2l_layout.addWidget(self.h2l_rb)
        h2l_layout.addStretch()

        l2h_layout = QHBoxLayout()
        l2h_layout.addWidget(self.l2h_rb)
        l2h_layout.addStretch()

        rb_group_layout = QVBoxLayout()
        rb_group_layout.addLayout(h2l_layout)
        rb_group_layout.addLayout(l2h_layout)

        rb_group_box.setLayout(rb_group_layout)

        main_layout = QVBoxLayout()
        main_layout.addLayout(label_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(rb_group_box)
        main_layout.addWidget(self.start_btn)

        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def handle_start_clicked(self) -> None:
        self.start_clicked = True
        span_ok: bool = self.check_span()
        if not span_ok:
            self.start_clicked = False
            return
        self.close()

    def check_span(self) -> bool:
        span = int(self.span_entry.text())
        match self.rb_group.checkedId():
            case 101:
                if self.current_pressure - span < 1000:
                    self.span_error_sig.emit(span, 'H2L')
                    return False
            case 102:
                if self.current_pressure + span > 3033:
                    self.span_error_sig.emit(span, 'L2H')
                    return False
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.start_clicked:
            span = self.span_entry.text()
            rate = self.rate_entry.text()
            direction = ''
            match self.rb_group.checkedId():
                case 101:
                    direction = 'H2L'
                case 102:
                    direction = 'L2H'
            self.start_sweep_sig.emit(span, rate, direction)
        event.accept()
        super().closeEvent(event)
