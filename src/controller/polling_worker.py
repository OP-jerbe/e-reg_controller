import statistics as stats

from PySide6.QtCore import QObject, Signal

from src.model.ereg_driver import eReg


class PollingWorker(QObject):
    result_sig = Signal(float)
    conn_error_sig = Signal(str)
    unexpected_error_sig = Signal(str)

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self.working: bool = False

    def doWork(self) -> None:
        """
        Executes the sampling cycle and processes the hardware buffer.

        This method initiates sampling on the eReg device if a cycle is not already
        in progress. It retrieves the data buffer, calculates the median value
        from the results, and emits the processed data via signals.

        The method handles state management using the `self.working` flag to
        prevent overlapping execution cycles.

        Signals Emitted:
            result_sig (float): Emitted with the calculated median of the
                buffer contents upon successful completion.
            conn_error_sig (str): Emitted if a ConnectionError occurs during
                sampling or data retrieval.
            unexpected_error_sig (str): Emitted if any other exception occurs
                during execution.

        Note:
            If the hardware returns 'sbe' (send buffer error) or 'scr'
            (sample complete response), the method returns early without
            emitting a result signal.
        """
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

            # Check if any characters in `response` are letters.
            # Only procede if the response is full of numbers.
            if any(char.isalpha() for char in response):
                return

            buffer_contents: list[str] = response.split()
            if not buffer_contents:
                return

            values: list[float] = [float(value) for value in buffer_contents]
            # print(values)
            result: float = float(stats.median(values))
            self.working = False
            self.result_sig.emit(result)
        except ConnectionError as e:
            self.working = False
            self.conn_error_sig.emit(str(e))
        except Exception as e:
            self.working = False
            self.unexpected_error_sig.emit(str(e))
