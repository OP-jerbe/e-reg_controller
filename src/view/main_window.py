from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent
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

        self._create_menubar()

        self.pressure_label = QLabel('Pressure:')
        self.pressure_reading_label = QLabel('- - - - mBar')
        self.pressure_setting_label = QLabel('Setting:')
        self.pressure_setting_entry = QLineEdit()

        # --- Create the layout ---
        central_widget = QWidget()
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
