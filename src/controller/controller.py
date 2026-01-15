from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from src.controller.worker import Worker
from src.model.ereg_driver import eReg
from src.view.main_window import MainWindow


class Controller(QObject):
    pressure_sig = Signal(float)

    def __init__(self, model: eReg, view: MainWindow) -> None:
        super().__init__()
        self.ereg = model
        self.mw = view

        self.worker_thread = QThread()

        self.timer = QTimer(interval=250)
        self.timer.timeout.connect(self.receive_timeout_sig)

        self.worker = Worker(self.ereg)
        self.worker.result_sig.connect(self.receive_result_sig)
        self.worker.conn_error_sig.connect(self.receive_conn_error_sig)
        self.worker.unexpected_error_sig.connect(self.receive_unexpected_error)
        self.worker.moveToThread(self.worker_thread)

        self.mw.closing_sig.connect(self.receive_closing_sig)
        self.mw.new_address_sig.connect(self.receive_new_address_sig)

        if self.ereg.sock:
            self.timer.start()

    # --- Controller Slots ---

    @Slot()
    def receive_timeout_sig(self) -> None:
        """
        Signal received from `self.timer`

        Tells the `Worker` class to execute the `doWork()` method.
        """
        self.worker.doWork()

    # --- Worker Slots ---

    @Slot()
    def receive_result_sig(self, result: float) -> None:
        """
        Signal received from the `Worker` class.

        Updates the UI with the pressure reading result.
        """
        self.mw.update_pressure_reading(result)

    @Slot()
    def receive_conn_error_sig(self, error: str) -> None:
        """
        Signal received from the `Worker` class.

        Stops the timer and shows an popup error message if a communication error occurs.
        """
        self.timer.stop()
        self.mw.pressure_reading_label.setText('- - - - mBar')
        self.mw.error_popup(error)

    @Slot()
    def receive_unexpected_error(self, error: str) -> None:
        """
        Signal received from the `Worker` class.

        Stops the timer and shows an popup error message if an unexpected error occurs.
        """
        self.timer.stop()
        self.mw.pressure_reading_label.setText('---- mBar')
        self.mw.error_popup(error)

    # --- MainWindow Slots ---

    @Slot()
    def receive_new_address_sig(self, ip: str, port: int) -> None:
        """
        Signal received from the `MainWindow` class.

        Tries to open a socket connection to the e-reg with `ip` and `port`.
        If successful, the ip address is set and the calibration pressure is
        initialized. Then, `self.timer` is started to begin reading data.
        """
        sock = self.ereg.open_connection(ip, port)
        if not sock:
            error = f'Could not connect to {ip}:{port}'
            self.mw.error_popup(error)
            return
        self.ereg.ip_address = ip
        self.ereg.cal_pressure = float(self.ereg.calibration_pressure)
        self.timer.start()

    @Slot()
    def receive_closing_sig(self) -> None:
        """
        Signal received from the `MainWindow` class.

        Stops the timer and kills the background thread when the main window is closed.
        """
        self.timer.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
