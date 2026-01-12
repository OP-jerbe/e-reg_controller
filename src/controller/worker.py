import traceback

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    # This survives even after the Worker is deleted
    finished = Signal(bool)
    error = Signal(str, str)
    rtn = Signal(object)


class Worker(QRunnable):
    def __init__(self, fn, rtn=False, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.rtn = rtn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()  # Create the signaler

    @Slot()
    def run(self) -> None:
        complete = False
        obj = None
        try:
            obj = self.fn(*self.args, **self.kwargs)
            complete = True
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(str(e), tb)
        finally:
            self.signals.finished.emit(complete)
            if self.rtn and complete:
                self.signals.rtn.emit(obj)
