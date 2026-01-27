from typing import Literal

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QRegularExpression, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QErrorMessage,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

import src.helpers.helpers as h
from src.model.ereg_driver import eReg
from src.view.bleed_supply_window import BleedSupplyWindow
from src.view.plot_window import PlotWindow
from src.view.reconnect_window import ReconnectWindow
from src.view.scalable_image_label import ScalableImageLabel
from src.view.scrolling_line_edit import ScrollingLineEdit


class MainWindow(QMainWindow):
    closing_sig = Signal()
    try_to_connect_sig = Signal(str, int)
    pressure_change_sig = Signal(str, str)
    operate_sig = Signal(bool)
    pressurize_sig = Signal()
    vent_sig = Signal()
    bypass_sig = Signal()
    start_pressure_sweep_sig = Signal(str, str, str)
    stop_pressure_sweep_sig = Signal()
    ext_sweep_sig = Signal(int)
    start_bleed_supply_sig = Signal(int)
    stop_bleed_supply_sig = Signal()
    purge_start_sig = Signal()
    purge_stop_sig = Signal()
    plot_sweep_sig = Signal(dict)

    def __init__(self, model: eReg) -> None:
        super().__init__()
        self.ereg = model
        self.last_valid_pressure = ''
        self.sweep_list = self.get_sweeps_for_menu()
        self.peak_current = float('nan')
        self.peak_pressure = float('nan')
        self.reading_offset_cal: int = self._set_reading_offset()
        self._create_gui()

    def _set_reading_offset(self) -> int:
        config_data = h.load_ini()
        value = config_data.get('ReadingOffsetCal', 'value')
        return int(value)

    # --- GUI creation methods ---

    def _create_menubar(self) -> None:
        """
        Creates the manubar in the `MainWindow` to allow the user to
        reconnect with the e-reg if the connection is lost or to exit
        the application.
        """
        self.exit_action = QAction(text='&Exit', parent=self)
        self.connect_action = QAction(text='&Connect', parent=self)
        self.bleed_supply_action = QAction(text='&Bleed Supply', parent=self)
        self.bleed_supply_action.setCheckable(True)

        self.plot_sweep_submenu = QMenu('&Plot Sweep', self)
        self.plot_sweep_submenu.aboutToShow.connect(self._refresh_sweep_menu)

        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu('&File')
        self.options_menu = self.menu_bar.addMenu('&Options')
        self.options_menu.addMenu(self.plot_sweep_submenu)

        self.file_menu.addAction(self.connect_action)
        self.file_menu.addAction(self.exit_action)
        self.options_menu.addAction(self.bleed_supply_action)

        self.exit_action.triggered.connect(self.handle_exit_triggered)
        self.connect_action.triggered.connect(self.handle_connect_triggered)
        self.bleed_supply_action.triggered.connect(self.handle_bleed_supply_triggered)

    def _create_main_tab(self) -> None:
        # --- Logic/Validators ---
        pressure_setting_regex = QRegularExpression(r'^[0-9]{0,4}$')
        pressure_setting_validator = QRegularExpressionValidator(pressure_setting_regex)

        # --- Create the "Main" Tab ---
        self.main_tab = QWidget()
        main_tab_layout = QVBoxLayout(self.main_tab)

        # --- Controls Section ---

        # Operate Button Section
        self.operate_btn = QPushButton('DISCONNECTED')  # add to main_tab_layout
        self.operate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.operate_btn.setEnabled(False)
        self.operate_btn.setCheckable(True)
        self.operate_btn.clicked.connect(self.handle_operate_btn_clicked)

        # Radio Button Section
        self.operate_rb_group = QButtonGroup()
        self.pressurize_rb = QRadioButton('PRESSURIZE')
        self.pressurize_rb.setChecked(True)
        self.pressurize_rb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vent_rb = QRadioButton('VENT')
        self.vent_rb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bypass_rb = QRadioButton('BYPASS')
        self.bypass_rb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.operate_rb_group.addButton(self.pressurize_rb, 101)
        self.operate_rb_group.addButton(self.vent_rb, 102)
        self.operate_rb_group.addButton(self.bypass_rb, 103)

        self.purge_btn = QPushButton('PURGE')
        self.purge_btn.setEnabled(False)
        self.purge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.purge_btn.pressed.connect(self.handle_purge_btn_pressed)
        self.purge_btn.released.connect(self.handle_purge_btn_released)

        press_h_layout = QHBoxLayout()
        press_h_layout.addWidget(self.pressurize_rb)
        press_h_layout.addStretch()

        vent_h_layout = QHBoxLayout()
        vent_h_layout.addWidget(self.vent_rb)
        vent_h_layout.addStretch()

        bypass_h_layout = QHBoxLayout()
        bypass_h_layout.addWidget(self.bypass_rb)
        bypass_h_layout.addStretch()

        rb_layout = QHBoxLayout()  # add to main_tab_layout
        rb_layout.addLayout(press_h_layout)
        rb_layout.addLayout(vent_h_layout)
        rb_layout.addLayout(bypass_h_layout)
        rb_layout.addWidget(self.purge_btn)

        self.operate_rb_group.idClicked.connect(self.handle_rb_selected)

        # --- Pressure Section ---
        self.pressure_setting_frame = QFrame()  # add to main_tab_layout
        self.pressure_setting_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.pressure_setting_frame.setLineWidth(2)
        pressure_layout = QHBoxLayout(self.pressure_setting_frame)

        self.pressure_reading_label = QLabel('- - - - mBar')
        self.pressure_reading_label.setStyleSheet('font-size: 24pt;')
        self.pressure_setting_label = QLabel('Setting: ')
        self.pressure_setting_entry = ScrollingLineEdit('0')
        self.pressure_setting_entry.setValidator(pressure_setting_validator)
        self.pressure_setting_entry.setPlaceholderText('Enter Pressure...')
        self.pressure_setting_entry.editingFinished.connect(self.handle_pressure_input)

        pressure_layout.addWidget(self.pressure_setting_label)
        pressure_layout.addWidget(self.pressure_setting_entry)
        pressure_layout.addWidget(self.pressure_reading_label)

        # State Image Section
        self.image_frame = QFrame()  # add to main_tab_layout
        self.image_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.image_frame.setLineWidth(2)
        state_img_layout = QVBoxLayout(self.image_frame)
        state_img_layout.setContentsMargins(0, 0, 0, 0)  # No padding inside the frame
        state_img_layout.setSpacing(0)

        self.state_img = h.get_state_img('disabled')
        self.image_label = ScalableImageLabel(self.state_img)
        self.image_label.setContentsMargins(0, 0, 0, 0)
        state_img_layout.addWidget(self.image_label)

        # Assemble the Main Tab
        main_tab_layout.addWidget(self.operate_btn, 0)
        main_tab_layout.addLayout(rb_layout, 0)
        main_tab_layout.addWidget(self.pressure_setting_frame, 0)
        main_tab_layout.addWidget(self.image_frame, 1)

    def _create_p_sweep_tab(self) -> None:
        # --- Logic/Validators ---
        sweep_regex = QRegularExpression(r'[0-9]*')
        sweep_validator = QRegularExpressionValidator(sweep_regex)

        # --- Create the Pressure Sweep Tab ---
        self.sweep_tab = QWidget()
        self.sweep_tab.setEnabled(False)
        self.sweep_tab_layout = QVBoxLayout(self.sweep_tab)

        # --- Settings Section ---
        self.sweep_settings_frame = QFrame()
        self.sweep_settings_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.sweep_settings_frame.setLineWidth(2)
        self.sweep_settings_frame_layout = QGridLayout()

        self.span_label = QLabel('Span (mBar)')
        self.span_entry = QLineEdit('400')
        self.span_entry.setValidator(sweep_validator)

        self.rate_label = QLabel('Rate (mBar/sec)')
        self.rate_entry = QLineEdit('2')
        self.rate_entry.setValidator(sweep_validator)

        self.sweep_settings_frame_layout.addWidget(self.span_label, 0, 0)
        self.sweep_settings_frame_layout.addWidget(self.span_entry, 1, 0)
        self.sweep_settings_frame_layout.addWidget(self.rate_label, 0, 1)
        self.sweep_settings_frame_layout.addWidget(self.rate_entry, 1, 1)

        # --- Direction Section ---
        self.direction_rb_group_box = QGroupBox('Sweep Direction')

        self.h2l_rb = QRadioButton('High-to-Low')
        self.h2l_rb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.h2l_rb.setChecked(True)

        self.l2h_rb = QRadioButton('Low-to-High')
        self.l2h_rb.setCursor(Qt.CursorShape.PointingHandCursor)

        self.sweep_rb_group = QButtonGroup()
        self.sweep_rb_group.addButton(self.h2l_rb, 201)
        self.sweep_rb_group.addButton(self.l2h_rb, 202)

        self.h2l_layout = QHBoxLayout()
        self.h2l_layout.addWidget(self.h2l_rb)
        self.h2l_layout.addStretch()

        self.l2h_layout = QHBoxLayout()
        self.l2h_layout.addWidget(self.l2h_rb)
        self.l2h_layout.addStretch()

        self.direction_rb_group_layout = QHBoxLayout()
        self.direction_rb_group_layout.addLayout(self.h2l_layout)
        self.direction_rb_group_layout.addLayout(self.l2h_layout)

        self.direction_rb_group_box.setLayout(self.direction_rb_group_layout)

        # --- Start/Stop Section ---
        self.sweep_start_stop_frame = QFrame()
        self.sweep_start_stop_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.sweep_start_stop_frame.setLineWidth(2)
        self.sweep_start_stop_frame_layout = QVBoxLayout()

        self.ext_sweep_btn = QPushButton('Add 50 to span')
        self.ext_sweep_btn.setEnabled(False)
        self.ext_sweep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ext_sweep_btn.clicked.connect(self.handle_ext_sweep_btn_clicked)

        self.start_sweep_btn = QPushButton('Start')
        self.start_sweep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_sweep_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.start_sweep_btn.clicked.connect(self.handle_start_sweep_btn_clicked)
        self.start_sweep_btn.setAutoDefault(True)

        self.stop_sweep_btn = QPushButton('Stop')
        self.stop_sweep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_sweep_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.stop_sweep_btn.setEnabled(False)
        self.stop_sweep_btn.clicked.connect(self.handle_stop_sweep_btn_clicked)
        self.stop_sweep_btn.setAutoDefault(True)

        self.sweep_start_stop_frame_layout.addWidget(self.ext_sweep_btn)
        self.sweep_start_stop_frame_layout.addWidget(self.start_sweep_btn)
        self.sweep_start_stop_frame_layout.addWidget(self.stop_sweep_btn)

        # --- Progress Bar Section ---
        self.sweep_progress_bar = QProgressBar()
        self.sweep_progress_bar.setRange(0, 100)
        self.sweep_progress_bar.setValue(0)
        self.sweep_progress_bar.setTextVisible(True)
        self.sweep_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sweep_progress_bar.setFixedHeight(35)

        # Assemble the Pressure Sweep tab
        self.sweep_tab_layout.addLayout(self.sweep_settings_frame_layout, 0)
        self.sweep_tab_layout.addWidget(self.direction_rb_group_box, 0)
        self.sweep_tab_layout.addLayout(self.sweep_start_stop_frame_layout, 1)
        self.sweep_tab_layout.addWidget(self.sweep_progress_bar, 0)

        # --- 4. Add Tabs to Widget ---
        self.tabs.addTab(self.main_tab, 'Main')
        self.tabs.addTab(self.sweep_tab, 'P. Sweep')

    def _create_gui(self) -> None:
        # --- Window Setup ---
        ver = h.get_app_version()
        self.setWindowTitle(f'e-Reg Controller v{ver}')
        self.setWindowIcon(h.get_icon())
        self.resize(400, 500)  # Increased height slightly to accommodate tab bar
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit {color: lightgreen;}'
        )
        self.setCentralWidget(self.tabs)

        self._create_menubar()
        self._create_main_tab()
        self._create_p_sweep_tab()

    def get_sweeps_for_menu(self) -> list[str]:
        data = h.get_json_data()
        sweeps = [
            f'[{d["start"].split(" ")[0]}] {d["start"].split(" ", 1)[1]} - {d["stop"].split(" ", 1)[1]}'
            for d in data
        ]
        return sweeps

    def handle_sweep_selection(self, action: QAction) -> None:
        i = action.data()
        sweep = h.get_json_data()[i]
        default_dir = r'C://TeststandData'
        filepath = h.select_file(default_dir)
        if not filepath:
            return
        plot_window = PlotWindow(self)
        try:
            fig = plot_window.create_fig(
                filepath, sweep['start'], sweep['stop'], sweep['direction']
            )
        except Exception as e:
            error_message = f'Could not generate plot. Make sure you have selected the correct csv file. [Error: {str(e)}]'
            self.error_popup(error_message)
            return
        fig_canvas = FigureCanvas(fig)
        plot_window.fig_canvas = fig_canvas
        plot_window.create_gui()
        plot_window.show()

    def _refresh_sweep_menu(self) -> None:
        raw_data = h.get_json_data()
        self.plot_sweep_submenu.clear()
        group = QActionGroup(self)

        for index, d in enumerate(raw_data):
            label = f'[{d["start"].split(" ")[0]}] {d["start"].split(" ", 1)[1]} - {d["stop"].split(" ", 1)[1]}'
            action = QAction(label, self)
            action.setData(index)
            group.addAction(action)
            self.plot_sweep_submenu.addAction(action)

        group.triggered.connect(self.handle_sweep_selection)

    # --- UI States ---

    def set_disconnected_state(self) -> None:
        # Main tab
        self.operate_btn.setText('DISCONNECTED')
        self.operate_btn.setChecked(False)
        self.operate_btn.setEnabled(False)
        for rb in self.operate_rb_group.buttons():
            rb.setEnabled(True)
        self.purge_btn.setEnabled(False)
        self.pressure_setting_entry.setEnabled(True)
        self.pressure_reading_label.setText('- - - - mBar')
        self.change_state_image('disabled')

        # P. Sweep tab
        self.sweep_tab.setEnabled(False)

    def set_valves_disabled_state(self) -> None:
        # Main tab
        self.operate_btn.setChecked(False)
        self.operate_btn.setText('VALVES DISABLED')
        self.operate_btn.setEnabled(True)
        self.purge_btn.setEnabled(True)
        for rb in self.operate_rb_group.buttons():
            rb.setEnabled(True)
        self.pressure_setting_entry.setEnabled(True)
        self.change_state_image('disabled')

        # P. Sweep tab
        self.sweep_tab.setEnabled(False)

    def set_valves_active_state(self) -> None:
        # Main tab
        self.operate_btn.setText('VALVES ACTIVE')
        self.operate_btn.setEnabled(True)
        for btn in self.operate_rb_group.buttons():
            btn.setEnabled(True)
        self.purge_btn.setEnabled(True)
        match self.operate_rb_group.checkedId():
            case 101:
                self.set_pressurize_state()
            case 102:
                self.set_vent_state()
            case 103:
                self.set_bypass_state()
        self.pressure_setting_entry.setEnabled(True)

    def set_pressurize_state(self) -> None:
        # Main tab
        if self.operate_btn.isEnabled() and self.operate_btn.isChecked():
            self.change_state_image('pressurized')

        # P. Sweep tab
        self.sweep_tab.setEnabled(True)
        self.span_entry.setEnabled(True)
        self.rate_entry.setEnabled(True)
        for btn in self.sweep_rb_group.buttons():
            btn.setEnabled(True)
        self.ext_sweep_btn.setEnabled(False)
        self.start_sweep_btn.setEnabled(True)
        self.stop_sweep_btn.setEnabled(False)

    def set_vent_state(self) -> None:
        # Main tab
        if self.operate_btn.isEnabled() and self.operate_btn.isChecked():
            self.change_state_image('venting')

        # P. Sweep tab
        self.sweep_tab.setEnabled(False)

    def set_bypass_state(self) -> None:
        # Main tab
        if self.operate_btn.isEnabled() and self.operate_btn.isChecked():
            self.change_state_image('bypassed')

        # P. Sweep tab
        self.sweep_tab.setEnabled(False)

    def set_pressure_sweep_state(self) -> None:
        # Main tab
        self.operate_btn.setEnabled(False)
        for rb in self.operate_rb_group.buttons():
            rb.setEnabled(False)
        self.purge_btn.setEnabled(False)
        self.pressure_setting_entry.setEnabled(False)

        # P. Sweep tab
        for btn in self.sweep_rb_group.buttons():
            btn.setEnabled(False)
        self.ext_sweep_btn.setEnabled(True)
        self.start_sweep_btn.setEnabled(False)
        self.stop_sweep_btn.setEnabled(True)

    def change_state_image(
        self, state: Literal['disabled', 'pressurized', 'venting', 'bypassed']
    ) -> None:
        new_img = h.get_state_img(state)
        self.state_img = new_img
        self.image_label.update_pixmap(new_img)

    # --- Main tab methods ---

    def handle_rb_selected(self, id: int) -> None:
        match id:
            case 101:
                self.pressurize_sig.emit()
            case 102:
                self.vent_sig.emit()
            case 103:
                self.bypass_sig.emit()

    def update_pressure_reading(self, pressure: float) -> None:
        """
        Updates the pressure reading on the UI.

        Args:
            pressure (float): The pressure reading from the e-reg in PSI.
        """
        pressure_mbar = h.convert_psi_to_mbar(pressure) - self.reading_offset_cal
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
        if not self.operate_btn.isEnabled():
            self.pressure_setting_entry.clearFocus()
            return
        match self.operate_rb_group.checkedId():
            case 101:  # PRESSURIZE
                old_pressure = self.last_valid_pressure
                new_pressure = self.pressure_setting_entry.text().strip()
                self.last_valid_pressure = new_pressure
                self.pressure_change_sig.emit(new_pressure, old_pressure)
                self.pressure_setting_entry.clearFocus()
            case _:
                self.pressure_setting_entry.clearFocus()
                return

    def handle_operate_btn_clicked(self) -> None:
        rb_id: int = self.sweep_rb_group.checkedId()
        self.operate_sig.emit(self.operate_btn.isChecked())
        self.handle_rb_selected(rb_id)

    def handle_purge_btn_pressed(self) -> None:
        if self.operate_btn.isChecked():
            self.purge_start_sig.emit()

    def handle_purge_btn_released(self) -> None:
        if self.operate_btn.isChecked():
            self.purge_stop_sig.emit()

    # --- Pressure Sweep tab methods ---

    def _check_span(self) -> bool:
        current_pressure_setting = int(self.pressure_setting_entry.text())
        span = int(self.span_entry.text())
        match self.sweep_rb_group.checkedId():
            case 201:
                direction = 'H2L'
                if current_pressure_setting - span < 0:
                    self.span_error_popup(span, direction)
                    return False
                if current_pressure_setting - span < 1000:
                    return self.low_pressure_warning_popup(span)
            case 202:
                direction = 'L2H'
                if current_pressure_setting + span > 3033:
                    self.span_error_popup(span, direction)
                    return False
        return True

    def handle_start_sweep_btn_clicked(self) -> None:
        if not self._check_span():
            return
        span = self.span_entry.text()
        rate = self.rate_entry.text()
        direction = ''
        match self.sweep_rb_group.checkedId():
            case 201:
                direction = 'H2L'
            case 202:
                direction = 'L2H'
        # self.operate_btn.setEnabled(False)
        # self.start_sweep_btn.setEnabled(False)
        # self.stop_sweep_btn.setEnabled(True)
        # self.purge_btn.setEnabled(False)
        # self.ext_sweep_btn.setEnabled(True)
        # for rb in self.operate_rb_group.buttons():
        #     rb.setEnabled(False)
        self.start_pressure_sweep_sig.emit(span, rate, direction)

    def handle_stop_sweep_btn_clicked(self) -> None:
        self.stop_pressure_sweep_sig.emit()

    def handle_ext_sweep_btn_clicked(self) -> None:
        self.ext_sweep_sig.emit(50)

    def low_pressure_warning_popup(self, span: int) -> bool:
        window_title = 'Span Warning'
        warning_message = f'A sweep of {span} mBar will cause the gas line pressure to fall below 1000 mBar are you sure you want to procede?'
        reply = QMessageBox.warning(
            self,
            window_title,
            warning_message,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            defaultButton=QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            return True
        else:
            return False

    def span_error_popup(self, span: int, direction: str) -> None:
        window_title = 'Span Error'
        error_message = ''
        match direction:
            case 'H2L':
                error_message = f'A sweep of {span} mBar will attempt to set the gas line pressure below 0 mBar which is not allowed.'
            case 'L2H':
                error_message = f'A sweep of {span} mBar will attempt to set the gas line pressure above 3033 mBar which is not allowed.'
        _ = QMessageBox.critical(
            self, window_title, error_message, QMessageBox.StandardButton.Ok
        )

    # --- Reconnect to device ---

    def handle_connect_triggered(self) -> None:
        """
        Opens the `ReconnectWindow`.
        """
        ip = self.ereg.ip_address
        port = self.ereg.PORT
        sock = self.ereg.sock
        recon_window = ReconnectWindow(self, ip, port, sock)
        recon_window.try_to_connect_sig.connect(self.receive_try_to_connect_sig)
        recon_window.show()

    @Slot()
    def receive_try_to_connect_sig(self, ip: str, port: str) -> None:
        """
        Signal received from `ReconnectWindow`.

        Passes along the `ip` address and `port` number from
        the `ReconnectWindow` to the `Controller`.
        """
        self.try_to_connect_sig.emit(ip, int(port))

    # --- Exit/Closing Application ---

    def handle_exit_triggered(self) -> None:
        """
        Closes the `MainWindow`.
        """
        self.close()

    # --- Bleed Supply Option ---

    def handle_bleed_supply_triggered(self) -> None:
        if not self.bleed_supply_action.isChecked():
            self.stop_bleed_supply_sig.emit()
            return
        bleed_supply_window = BleedSupplyWindow(self)
        bleed_supply_window.start_bleed_supply_sig.connect(
            self.receive_start_bleed_supply_sig
        )
        bleed_supply_window.show()

    @Slot()
    def receive_start_bleed_supply_sig(self, rate: int) -> None:
        self.start_bleed_supply_sig.emit(rate)

    # --- Error popup ---

    def error_popup(self, error: str) -> None:
        """
        Displays a popup window with an error message.
        """
        error_dialog = QErrorMessage(self)
        error_dialog.showMessage(error)

    # --- Hidden Events ---

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        This method runs when the `MainWindow` is closed.

        The `closing_sig` is sent to the `Controller` to
        stop the timer and background thread.
        """
        self.closing_sig.emit()
        event.accept()
        super().closeEvent(event)
