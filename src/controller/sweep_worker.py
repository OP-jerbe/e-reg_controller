from PySide6.QtCore import QObject, QTimer, Signal

import src.helpers.helpers as h
from src.model.ereg_driver import eReg


class SweepWorker(QObject):
    sweep_started_sig = Signal(int)  # target_count / span
    sweep_finished_sig = Signal()
    current_pressure_sig = Signal(int)
    sweep_progress_sig = Signal(int)  # steps_taken

    def __init__(
        self, model: eReg, starting_pressure: int, span: int, rate: int, direction: str
    ) -> None:
        super().__init__()
        self.ereg = model
        self.current_pressure = starting_pressure
        self.target_count = span
        self.steps_taken = 0
        self.direction_val = -1 if direction == 'H2L' else 1
        self._is_running = True  # Control flag

        # Setup Timer
        self.timer = QTimer(self)
        interval = int(1000 / max(1, rate))
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.take_step)

    def doWork(self) -> None:
        self.sweep_started_sig.emit(self.target_count)
        self.timer.start()

    def take_step(self) -> None:
        if not self._is_running:
            self.timer.stop()
            self.sweep_finished_sig.emit()
            return
        if self.steps_taken < self.target_count:
            self.ereg.pressure = h.convert_mbar_to_psi(self.current_pressure)
            self.current_pressure += self.direction_val
            self.steps_taken += 1
            self.current_pressure_sig.emit(self.current_pressure)
            self.sweep_progress_sig.emit(self.steps_taken)
        else:
            self.timer.stop()
            self.sweep_finished_sig.emit()

    def stop(self) -> None:
        self._is_running = False
