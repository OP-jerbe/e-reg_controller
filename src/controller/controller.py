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

        self.worker = Worker(self.ereg)
        self.worker.result_sig.connect(self.receive_result_sig)
        self.worker.conn_error_sig.connect(self.receive_conn_error_sig)
        self.worker.unexpected_error_sig.connect(self.receive_unexpected_error)
        self.worker.moveToThread(self.worker_thread)

        self.timer = QTimer(interval=250)
        self.timer.timeout.connect(self.receive_timer_timeout_sig)

        self.mw.closing_sig.connect(self.stop_bg_thread)

        self._check_connection()

    def _check_connection(self) -> None:
        if self.ereg.sock:
            self.timer.start()

    @Slot()
    def receive_timer_timeout_sig(self) -> None:
        self.worker.doWork()

    @Slot()
    def receive_result_sig(self, result: float) -> None:
        self.mw.update_pressure_reading(result)

    @Slot()
    def receive_conn_error_sig(self, error: str) -> None:
        print(error)

    @Slot()
    def receive_unexpected_error(self, error: str) -> None:
        print(error)

    def stop_bg_thread(self) -> None:
        if self.worker_thread.isRunning():
            print('worker thread stopping')
            self.timer.stop()
            self.worker_thread.quit()
            self.worker_thread.wait()
