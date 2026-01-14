import statistics as stats

from PySide6.QtCore import QObject, Signal

from src.model.ereg_driver import eReg


class Worker(QObject):
    result_sig = Signal(float)
    conn_error_sig = Signal(str)
    unexpected_error_sig = Signal(str)

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self.working: bool = False

    def doWork(self) -> None:
        if not self.working:
            self.working = True
            try:
                self.ereg.sample_rate = 10
                self.ereg.start_sampling(21)
            except ConnectionError as e:
                self.working = False
                self.conn_error_sig.emit(str(e))
                return
            except Exception as e:
                self.working = False
                self.unexpected_error_sig.emit(str(e))
                return
        try:
            response: str = self.ereg.send_buffer()
            print(f'{response = }')
            if response == 'sbe':  # send buffer error
                return

            if response == 'scr':  # sample complete response
                return

            buffer_contents: list[str] = response.split()
            if not buffer_contents:
                return

            values: list[float] = [float(value) for value in buffer_contents]
            result: float = float(stats.median(values))
            self.working = False
            self.result_sig.emit(result)
        except ConnectionError as e:
            self.working = False
            self.conn_error_sig.emit(str(e))
        except Exception as e:
            self.working = False
            self.unexpected_error_sig.emit(str(e))
