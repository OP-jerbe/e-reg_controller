from PySide6.QtCore import QObject, QThread, QThreadPool, QTimer, Signal, Slot

import src.helpers.helpers as h
from src.controller.bleed_worker import BleedWorker
from src.controller.polling_worker import PollingWorker
from src.controller.sweep_worker import SweepWorker
from src.model.ereg_driver import eReg
from src.view.main_window import MainWindow


class Controller(QObject):
    pressure_sig = Signal(float)

    def __init__(self, model: eReg, view: MainWindow) -> None:
        super().__init__()
        self.ereg = model
        self.mw = view

        self.worker_thread = QThread()
        self.worker_thread.setObjectName('Pressure Reading')

        self.thread_pool = QThreadPool()

        self.polling_timer = QTimer(interval=250)
        self.polling_timer.timeout.connect(self.receive_polling_timer_timeout_sig)

        self.polling_worker = PollingWorker(self.ereg)
        self.polling_worker.result_sig.connect(self.receive_result_sig)
        self.polling_worker.conn_error_sig.connect(self.receive_conn_error_sig)
        self.polling_worker.unexpected_error_sig.connect(self.receive_unexpected_error)
        self.polling_worker.moveToThread(self.worker_thread)

        self.mw.closing_sig.connect(self.receive_closing_sig)
        self.mw.new_address_sig.connect(self.receive_new_address_sig)
        self.mw.pressure_change_sig.connect(self.receive_pressure_change_sig)
        self.mw.operate_sig.connect(self.receive_operate_sig)
        self.mw.pressurize_sig.connect(self.receive_pressurize_sig)
        self.mw.vent_sig.connect(self.receive_vent_sig)
        self.mw.bypass_sig.connect(self.receive_bypass_sig)
        self.mw.start_pressure_sweep_sig.connect(self.receive_start_pressure_sweep_sig)
        self.mw.stop_pressure_sweep_sig.connect(self.receive_stop_pressure_sweep_sig)
        self.mw.start_bleed_supply_sig.connect(self.receive_start_bleed_supply_sig)
        self.mw.stop_bleed_supply_sig.connect(self.receive_stop_bleed_supply_sig)

        if self.ereg.sock:
            self._init_ereg()
            self._init_mw()

    def _init_ereg(self) -> None:
        self.ereg.valves_off()
        self.ereg.cal_pressure = float(self.ereg.calibration_pressure)
        self.polling_timer.start()

    def _init_mw(self) -> None:
        self.mw.operate_btn.setEnabled(True)
        self.mw.operate_btn.setText('VALVES DISABLED')

    ####################################
    ######### Controller Slots #########
    ####################################

    @Slot()
    def receive_polling_timer_timeout_sig(self) -> None:
        """
        Signal received from `self.timer`

        Tells the `Worker` class to execute the `doWork()` method.
        """
        self.polling_worker.doWork()

    ####################################
    ########## Worker Slots ############
    ####################################

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
        self.polling_timer.stop()
        try:
            if hasattr(self, 'sweep_thread') and self.sweep_thread is not None:
                if self.sweep_thread.isRunning():
                    if hasattr(self, 'sweep_worker') and self.sweep_worker:
                        self.sweep_worker.stop()
        except RuntimeError:
            # This catches cases where the C++ object was deleted but reference remained
            print('whoopsy-daisy')
            self.sweep_thread = None
            self.sweep_worker = None
        self.mw.pressure_reading_label.setText('- - - - mBar')
        self.mw.operate_btn.setChecked(False)
        self.mw.operate_btn.setText('DISCONNECTED')
        self.mw.operate_btn.setEnabled(False)
        self.mw.sweep_tab.setEnabled(False)
        self.mw.change_state_image('disabled')
        self.mw.error_popup(error)

    @Slot()
    def receive_unexpected_error(self, error: str) -> None:
        """
        Signal received from the `Worker` class.

        Stops the timer and shows an popup error message if an unexpected error occurs.
        """
        self.polling_timer.stop()
        self.mw.pressure_reading_label.setText('---- mBar')
        self.mw.error_popup(error)

    ####################################
    ######### MainWindow Slots #########
    ####################################

    # --- Pressure Sweep Tab Signals ---
    @Slot()
    def receive_start_pressure_sweep_sig(
        self, span: str, rate: str, direction: str
    ) -> None:
        # Check if a sweep is already running to prevent duplicates
        try:
            if hasattr(self, 'sweep_thread') and self.sweep_thread is not None:
                if self.sweep_thread.isRunning():
                    print('Sweep already in progress...')
                    return
        except RuntimeError:
            # This catches cases where the C++ object was deleted but reference remained
            self.sweep_thread = None

        current_pressure = int(self.mw.pressure_setting_entry.text())
        self.sweep_worker = SweepWorker(
            self.ereg, current_pressure, int(span), int(rate), direction
        )
        self.sweep_thread = QThread()
        self.sweep_thread.setObjectName('Sweep')
        self.sweep_worker.moveToThread(self.sweep_thread)

        # Stop thread loop
        self.sweep_worker.sweep_finished_sig.connect(self.sweep_thread.quit)
        # Delete worker
        self.sweep_worker.sweep_finished_sig.connect(self.sweep_worker.deleteLater)
        # Delete thread
        self.sweep_thread.finished.connect(self.sweep_thread.deleteLater)

        self.sweep_worker.sweep_finished_sig.connect(self.receive_sweep_finished_sig)
        self.sweep_worker.current_pressure_sig.connect(
            self.receive_current_pressure_sig
        )

        self.sweep_worker.sweep_started_sig.connect(self.receive_sweep_started_sig)
        self.sweep_worker.sweep_progress_sig.connect(self.receive_sweep_progress_sig)

        self.sweep_thread.started.connect(self.sweep_worker.doWork)
        self.sweep_thread.start()

    @Slot()
    def receive_stop_pressure_sweep_sig(self) -> None:
        try:
            if hasattr(self, 'sweep_thread') and self.sweep_thread is not None:
                if self.sweep_thread.isRunning():
                    if hasattr(self, 'sweep_worker') and self.sweep_worker:
                        self.sweep_worker.stop()
        except RuntimeError:
            # This catches cases where the C++ object was deleted but reference remained
            self.sweep_thread = None
            self.sweep_worker = None

    @Slot()
    def receive_sweep_started_sig(self, maximum_steps: int) -> None:
        self.mw.sweep_progress_bar.setMaximum(maximum_steps)

    @Slot()
    def receive_sweep_finished_sig(self) -> None:
        self.mw.operate_btn.setEnabled(True)
        self.mw.pressure_setting_entry.setEnabled(True)
        self.mw.start_sweep_btn.setEnabled(True)
        self.mw.stop_sweep_btn.setEnabled(False)
        self.mw.sweep_progress_bar.setValue(0)

    @Slot()
    def receive_current_pressure_sig(self, pressure: int) -> None:
        if self.mw.pressure_setting_entry.isEnabled():
            self.mw.pressure_setting_entry.setEnabled(False)
        self.mw.pressure_setting_entry.setText(str(pressure))

    @Slot()
    def receive_sweep_progress_sig(self, steps_taken: int) -> None:
        self.mw.sweep_progress_bar.setValue(steps_taken)

    # --- Main Tab Signals ---

    @Slot()
    def receive_operate_sig(self, checked: bool) -> None:
        if checked:
            self.ereg.valves_on()
            self.mw.operate_btn.setText('VALVES ACTIVE')
            match self.mw.operate_rb_group.checkedId():
                case 101:  # PRESSURIZE
                    self.mw.sweep_tab.setEnabled(True)
                    self.mw.pressurize_sig.emit()
                    self.mw.change_state_image('pressurized')
                case 102:  # VENT
                    self.mw.vent_sig.emit()
                    self.mw.change_state_image('venting')
                case 103:  # BYPASS
                    self.mw.bypass_sig.emit()
                    self.mw.change_state_image('bypassed')
        else:
            self.ereg.valves_off()
            self.mw.operate_btn.setText('VALVES DISABLED')
            self.mw.sweep_tab.setEnabled(False)
            self.mw.change_state_image('disabled')

    @Slot()
    def receive_pressurize_sig(self) -> None:
        if not self.mw.operate_btn.isChecked():
            return
        self.mw.handle_pressure_input()  # set the pressure
        self.mw.sweep_tab.setEnabled(True)
        self.mw.change_state_image('pressurized')

    @Slot()
    def receive_vent_sig(self) -> None:
        if not self.mw.operate_btn.isChecked():
            return
        self.ereg.pressure = 0
        self.mw.sweep_tab.setEnabled(False)
        self.mw.change_state_image('venting')

    @Slot()
    def receive_bypass_sig(self) -> None:
        if not self.mw.operate_btn.isChecked():
            return
        self.ereg.pressure = self.ereg.cal_pressure
        self.mw.sweep_tab.setEnabled(False)
        self.mw.change_state_image('bypassed')

    @Slot()
    def receive_pressure_change_sig(self, new_pressure: str, old_pressure: str) -> None:
        """
        Validates and applies a new pressure setpoint to the hardware.

        Receives the current and previous pressure strings from the UI. If the
        new input is empty or falls outside the safety range (0-3033 mBar),
        the UI is reverted to the old value and an error popup is displayed
        where applicable.

        If valid, the value is converted from mBar to PSI, rounded to two
        decimal places, and sent to the e-regulator hardware.

        Args:
            new_pressure (str): The target pressure value entered by the user.
            old_pressure (str): The last successfully applied pressure value.
        """
        if not new_pressure:
            self.mw.pressure_setting_entry.setText(old_pressure)
            return

        p = int(new_pressure)
        if not 0 <= p <= 3033:
            self.mw.pressure_setting_entry.setText(old_pressure)
            error_msg = (
                f'Invalid Pressure: {p} mBar. Please enter a value between 0 and 3033.'
            )
            self.mw.error_popup(error_msg)
            return

        if not self.mw.operate_btn.isChecked():
            return

        p = h.convert_mbar_to_psi(p)
        self.ereg.pressure = p

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
        self._init_ereg()
        self._init_mw()

    @Slot()
    def receive_closing_sig(self) -> None:
        """
        Signal received from the `MainWindow` class.

        Stops the timer and kills the background thread when the main window is closed.
        """
        self.polling_timer.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()

    # --- Bleed Supply Signals ---

    @Slot()
    def receive_start_bleed_supply_sig(self, rate: int) -> None:
        interval = int(3.6e6 / rate)  # milliseconds between blips
        self.bleed_supply_timer = QTimer(interval=interval)
        self.bleed_supply_timer.timeout.connect(self.handle_bleed_supply_timer_timeout)
        self.bleed_supply_timer.start()

    @Slot()
    def handle_bleed_supply_timer_timeout(self) -> None:
        change = 20  # mBar
        pressure_setting = int(self.mw.pressure_setting_entry.text())
        blip_pressure = pressure_setting - change
        bleed_worker = BleedWorker(
            fn=self.bleed_supply_line,
            rtn=False,
            blip_pressure=blip_pressure,
            pressure_setting=pressure_setting,
        )
        self.thread_pool.start(bleed_worker)

    def bleed_supply_line(self, blip_pressure: int, pressure_setting: int) -> None:
        self.ereg.pressure = h.convert_mbar_to_psi(blip_pressure)
        QThread.msleep(20)
        self.ereg.pressure = h.convert_mbar_to_psi(pressure_setting)

    @Slot()
    def receive_stop_bleed_supply_sig(self) -> None:
        self.bleed_supply_timer.stop()
        self.bleed_supply_timer.deleteLater()
