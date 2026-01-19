from PySide6.QtCore import QRegularExpression, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QErrorMessage,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

import src.helpers.helpers as h
from src.model.ereg_driver import eReg
from src.view.reconnect_window import ReconnectWindow


class MainWindow(QMainWindow):
    closing_sig = Signal()
    new_address_sig = Signal(str, int)
    pressure_change_sig = Signal(str, str)
    operate_sig = Signal(bool)
    pressurize_sig = Signal()
    vent_sig = Signal()
    pressure_sweep_sig = Signal()

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self.last_valid_pressure = ''
        self._create_gui()

    # --- GUI creation methods ---

    def _create_gui(self) -> None:
        # --- Window Setup ---
        ver = h.get_app_version()
        self.setWindowTitle(f'e-Reg Controller v{ver}')
        self.setWindowIcon(h.get_icon())
        self.resize(300, 150)

        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit {color: lightgreen;}'
        )

        # --- Logic/Validators ---
        number_regex = QRegularExpression(r'^[0-9]{0,4}$')
        validator = QRegularExpressionValidator(number_regex)

        self._create_menubar()

        # --- 1. Initialize Central Widget ---
        # This acts as the "canvas" for your window
        central_widget = QWidget()
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(central_widget)

        # The main layout that holds the primary sections
        main_layout = QVBoxLayout(central_widget)

        # --- 2. Controls Section (Frame) ---
        self.controls_frame = QFrame()
        self.controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.controls_frame.setLineWidth(2)

        controls_layout = QVBoxLayout(self.controls_frame)

        self.operate_btn = QPushButton('OFF')
        self.operate_btn.setEnabled(False)
        self.operate_btn.setCheckable(True)
        self.operate_btn.setChecked(False)
        self.operate_btn.clicked.connect(self.handle_operate_btn_clicked)

        self.rb_group = QButtonGroup()

        self.pressurize_rb = QRadioButton('PRESSURIZE')
        self.pressurize_rb.setChecked(True)
        self.vent_rb = QRadioButton('VENT')

        self.rb_group.addButton(self.pressurize_rb, 101)
        self.rb_group.addButton(self.vent_rb, 102)

        press_h_layout = QHBoxLayout()
        press_h_layout.addWidget(self.pressurize_rb)
        press_h_layout.addStretch()  # Pushes the RB to the left

        vent_h_layout = QHBoxLayout()
        vent_h_layout.addWidget(self.vent_rb)
        vent_h_layout.addStretch()  # Pushes the RB to the left

        controls_layout.addWidget(self.operate_btn)
        controls_layout.addLayout(press_h_layout)
        controls_layout.addLayout(vent_h_layout)

        self.rb_group.idClicked.connect(self.handle_rb_selected)

        # --- 3. Pressure Section (Frame) ---
        self.pressure_setting_frame = QFrame()
        self.pressure_setting_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.pressure_setting_frame.setLineWidth(2)

        pressure_layout = QFormLayout(self.pressure_setting_frame)

        self.pressure_reading_label = QLabel('- - - - mBar')
        self.pressure_setting_entry = QLineEdit('0')
        self.pressure_setting_entry.setValidator(validator)
        self.pressure_setting_entry.setPlaceholderText('Enter Pressure...')
        self.pressure_setting_entry.editingFinished.connect(self.handle_pressure_input)

        pressure_layout.addRow('Pressure:', self.pressure_reading_label)
        pressure_layout.addRow('Setting:', self.pressure_setting_entry)

        # --- 4. Assemble ---
        # Add the frames directly to the main layout
        main_layout.addWidget(self.controls_frame)
        main_layout.addWidget(self.pressure_setting_frame)

        # Add a spacer at the bottom to keep everything at the top if window is resized
        main_layout.addStretch()

    def _create_menubar(self) -> None:
        """
        Creates the manubar in the `MainWindow` to allow the user to
        reconnect with the e-reg if the connection is lost or to exit
        the application.
        """
        self.exit_action = QAction(text='Exit', parent=self)
        self.connect_action = QAction(text='Connect', parent=self)
        self.pressure_sweep_action = QAction(text='Pressure Sweep', parent=self)

        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        self.tools_menu = self.menu_bar.addMenu('Tools')
        # self.help_menu = self.menu_bar.addMenu('Help')

        self.file_menu.addAction(self.connect_action)
        self.file_menu.addAction(self.exit_action)
        self.tools_menu.addAction(self.pressure_sweep_action)

        self.exit_action.triggered.connect(self.handle_exit_triggered)
        self.connect_action.triggered.connect(self.handle_connect_triggered)
        self.pressure_sweep_action.triggered.connect(
            self.handle_pressure_sweep_triggered
        )

    # --- GUI Updating methods ---

    def handle_rb_selected(self, id: int) -> None:
        match id:
            case 101:
                self.pressurize_sig.emit()
            case 102:
                self.vent_sig.emit()

    def update_pressure_reading(self, pressure: float) -> None:
        """
        Updates the pressure reading on the UI.

        Args:
            pressure (float): The pressure reading from the e-reg in PSI.
        """
        pressure_mbar = h.convert_psi_to_mbar(pressure)
        text = f'{pressure_mbar:.0f} mBar'
        self.pressure_reading_label.setText(text)

    def handle_pressure_input(self) -> None:
        """
        Triggers the pressure change workflow when user input is finished.

        Captures the text from the pressure setting entry, identifies the
        previously stored valid pressure, and updates the local state.
        Emits 'pressure_change_sig' to notify the Controller that a
        validation and hardware update is requested.

        This method is intended to be connected to the `editingFinished`
        signal of the QLineEdit.
        """
        old_pressure = self.last_valid_pressure
        new_pressure = self.pressure_setting_entry.text().strip()
        self.last_valid_pressure = new_pressure
        self.pressure_change_sig.emit(new_pressure, old_pressure)
        self.pressure_setting_entry.clearFocus()

    def handle_operate_btn_clicked(self) -> None:
        rb_id: int = self.rb_group.checkedId()
        self.operate_sig.emit(self.operate_btn.isChecked())
        self.handle_rb_selected(rb_id)

    # --- Menu Option Handlers ---

    def handle_pressure_sweep_triggered(self) -> None:
        print('pressure sweep triggered')

    def handle_exit_triggered(self) -> None:
        """
        Closes the `MainWindow`.
        """
        self.close()

    def handle_connect_triggered(self) -> None:
        """
        Opens the `ReconnectWindow`.
        """
        ip = self.ereg.ip_address
        port = self.ereg.PORT
        sock = self.ereg.sock
        recon_window = ReconnectWindow(self, ip, port, sock)
        recon_window.new_address_sig.connect(self.receive_new_address_sig)
        recon_window.show()

    @Slot()
    def receive_new_address_sig(self, ip: str, port: str) -> None:
        """
        Signal received from `ReconnectWindow`.

        Passes along the `ip` address and `port` number from
        the `ReconnectWindow` to the `Controller`.
        """
        self.new_address_sig.emit(ip, int(port))

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        This method runs when the `MainWindow` is closed.

        The `closing_sig` is sent to the `Controller` to
        stop the timer and background thread.
        """
        self.closing_sig.emit()
        event.accept()
        super().closeEvent(event)

    # --- Error popup ---

    def error_popup(self, error: str) -> None:
        """
        Displays a popup window with an error message.
        """
        error_dialog = QErrorMessage(self)
        error_dialog.showMessage(error)
