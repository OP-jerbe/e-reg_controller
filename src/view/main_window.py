from PySide6.QtCore import QRegularExpression, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QErrorMessage,
    QFormLayout,
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
from src.view.reconnect_window import ReconnectWindow


class MainWindow(QMainWindow):
    closing_sig = Signal()
    new_address_sig = Signal(str, int)
    new_pressure_sig = Signal(str)

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self._create_gui()

    # --- GUI creation methods ---

    def _create_gui(self) -> None:
        """
        Creates the GUI for the `MainWindow`.

        Creates the widgets and sets styling and layout.
        """
        ver = h.get_app_version()
        self.setWindowTitle(f'e-Reg Controller v{ver}')
        icon = h.get_icon()
        self.setWindowIcon(icon)
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + """QLineEdit, QTextEdit {color: lightgreen;}"""
        )
        self.resize(300, 100)

        # Create the validator for numerical inputs
        number_regex = QRegularExpression(r'^[0-9]{0,4}$')
        validator = QRegularExpressionValidator(number_regex)

        self._create_menubar()

        self.pressure_label = QLabel('Pressure:')
        self.pressure_reading_label = QLabel('- - - - mBar')
        self.pressure_setting_label = QLabel('Setting:')
        self.pressure_setting_entry = QLineEdit()
        self.pressure_setting_entry.setValidator(validator)
        self.pressure_setting_entry.setPlaceholderText('Enter Pressure...')
        self.pressure_setting_entry.editingFinished.connect(self.handle_pressure_input)

        # Store the current valid text to revert if pressure_setting_entry is empty.
        self.last_valid_pressure = ''

        # --- Create the layout ---
        central_widget = QWidget()
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.container_frame = QFrame()
        self.container_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.container_frame.setLineWidth(2)

        frame_layout = QFormLayout(self.container_frame)
        frame_layout.addRow(self.pressure_label, self.pressure_reading_label)
        frame_layout.addRow(self.pressure_setting_label, self.pressure_setting_entry)

        main_layout.addWidget(self.container_frame)

    def _create_menubar(self) -> None:
        """
        Creates the manubar in the `MainWindow` to allow the user to
        reconnect with the e-reg if the connection is lost or to exit
        the application.
        """
        self.exit_action = QAction(text='Exit', parent=self)
        self.connect_action = QAction(text='Connect', parent=self)

        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('File')
        # self.help_menu = self.menu_bar.addMenu('Help')

        self.file_menu.addAction(self.connect_action)
        self.file_menu.addAction(self.exit_action)

        self.exit_action.triggered.connect(self.handle_exit_triggered)
        self.connect_action.triggered.connect(self.handle_connect_triggered)

    # --- GUI Updating methods ---

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
        Validates and processes the user input for the pressure setting.

        This method is triggered when the pressure entry field loses focus or
        the Enter key is pressed. It ensures the input consists only of
        numeric digits.

        If the input is invalid or empty, the field is reverted to the
        last successfully processed value. If valid, the new value is
        cached, emitted via 'new_pressure_sig', and the widget focus is cleared.

        Signals Emitted:
            new_pressure_sig (str): Emitted with the validated pressure
                string if the input is numeric.
        """
        current_text = self.pressure_setting_entry.text().strip()

        if not current_text:
            # If blank, repopulate with the last known valid text
            self.pressure_setting_entry.setText(self.last_valid_pressure)
            return

        self.last_valid_pressure = current_text
        self.new_pressure_sig.emit(current_text)
        self.pressure_setting_entry.clearFocus()

    # --- Menu Option Handlers ---

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
