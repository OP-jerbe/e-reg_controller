from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pandas import DataFrame
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

import src.helpers.helpers as h


class PlotWindow(QMainWindow):
    """
    Shows a plot from the hyperion test stand software csv.

    Example usage:
    >>> filepath = "path/to/hyperion/csv.csv"
    >>> sweep_start = "1/1/2026 9:03:24 AM"
    >>> sweep_stop = "1/1/2026 9:10:03 AM"
    >>> direction = "H2L"  # or "L2H"
    >>> plot_window = PlotWindow(self)  # `self` would be a QWidget parent object
    >>> fig = plot_window.create_fig(filepath, sweep_start, sweep_stop, direction)
    >>> fig_canvas = FigureCanvas(fig)
    >>> plot_window.fig_canvas = fig_canvas
    >>> plot_window.create_gui()
    >>> plot_window.show()
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.fig_canvas = FigureCanvas()
        self.peak_current = float('nan')
        self.peak_pressure = float('nan')
        self.peak_ang_int = float('nan')

    def create_fig(
        self, filepath: str, start_time: str, stop_time: str, direction: str
    ) -> Figure:
        df: DataFrame = pd.read_csv(filepath)
        df['Beam Current (A)'] = df['Beam Current (A)'] * 1e9  # convert to nanoamps
        df['Total Current (A)'] = df['Total Current (A)'] * 1e6  # convert to microamps
        df['Angular Intensity (mA/str)'] = abs(df['Angular Intensity (mA/str)'])
        start_idx: int = df.loc[df['Time'] == start_time].index.tolist()[0]
        stop_idx: int = df.loc[df['Time'] == stop_time].index.tolist()[0]

        fig = Figure(layout='constrained')

        sn = Path(filepath).name.split()[0]
        date = start_time.split()[0]
        start = f'{start_time.split()[1]} {start_time.split()[2]}'
        stop = f'{stop_time.split()[1]} {stop_time.split()[2]}'
        self.fig_title = f'{direction} sweep of {sn} on {date} {start} - {stop}'

        fig.suptitle(self.fig_title, size=15)

        x = df['Source Pressure (mBar)'][start_idx:stop_idx]

        # --- Cup Current Plot ---
        ax_cup = fig.add_subplot(231)
        y_cup = df['Beam Current (A)'][start_idx:stop_idx]

        peak_idx = y_cup.abs().idxmax()
        self.peak_current = df.loc[peak_idx, 'Beam Current (A)']
        self.peak_pressure = df.loc[peak_idx, 'Source Pressure (mBar)']

        # Place the text box
        # transform=ax_cup.transAxes tells matplotlib to use (0,0) to (1,1) coordinates
        ax_cup.text(
            0.95,
            0.95,
            f'Peak P: {self.peak_pressure:.2e} mBar',
            transform=ax_cup.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
        )

        ax_cup.set_title('Cup Current (nA)')
        ax_cup.plot(x, y_cup, c='r')

        # --- Total Current Plot ---
        ax_tot = fig.add_subplot(232)
        y_tot = df['Total Current (A)'][start_idx:stop_idx]

        ax_tot.set_title('Total Current (μA)')
        ax_tot.plot(x, y_tot, c='orange')

        # --- Forward RF Power ---
        ax_fwd = fig.add_subplot(233)
        y_fwd = df['RF Power Forward (W)'][start_idx:stop_idx]

        ax_fwd.set_title('Fwd RF Power (W)')
        ax_fwd.plot(x, y_fwd, c='b')

        # --- Angular Intensity Plot ---
        ax_ang = fig.add_subplot(234)
        y_ang = df['Angular Intensity (mA/str)'][start_idx:stop_idx]
        peak_idx = y_ang.abs().idxmax()
        self.peak_ang_int = df.loc[peak_idx, 'Angular Intensity (mA/str)']

        # Place the text box
        # transform=ax_cup.transAxes tells matplotlib to use (0,0) to (1,1) coordinates
        ax_ang.text(
            0.95,
            0.95,
            f"Peak I': {self.peak_ang_int:.2f} mA/sr",
            transform=ax_ang.transAxes,
            fontsize=10,
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
        )

        ax_ang.set_title('Ang Int (mA/sr)')
        ax_ang.plot(x, y_ang, c='r')

        # --- Beam Supply Current Plot ---
        ax_ibs = fig.add_subplot(235)
        y_ibs = df['Beam Supply Current (uA)'][start_idx:stop_idx]

        ax_ibs.set_title('Beam Supply Current (μA)')
        ax_ibs.plot(x, y_ibs, c='g')

        # --- Reflected RF Power Plot ---
        ax_rfl = fig.add_subplot(236)
        y_rfl = df['RF Power Reverse (W)'][start_idx:stop_idx]

        ax_rfl.set_title('Refl RF Power (W)')
        ax_rfl.plot(x, y_rfl, c='b')

        return fig

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Pressure Sweep')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit, QSpinBox {color: lightgreen;}'
        )

        # --- Create Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')

        save_action = file_menu.addAction('&Save Plot')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.handle_save_plot_clicked)

        peak_pressure_label = QLabel(f'Peak Pressure: {self.peak_pressure:.2e} mBar')
        peak_pressure_label.setStyleSheet('font-size: 16pt;')
        peak_current_label = QLabel(f'Peak Current: {self.peak_current:.2f} nA')
        peak_current_label.setStyleSheet('font-size: 16pt;')
        peak_ang_int_label = QLabel(f"Peak I' = {self.peak_ang_int:.2f} mA/sr")
        peak_ang_int_label.setStyleSheet('font-size: 16pt;')

        peak_layout = QHBoxLayout()
        peak_layout.addWidget(peak_pressure_label)
        peak_layout.addWidget(peak_current_label)
        peak_layout.addWidget(peak_ang_int_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(peak_layout, 0)
        main_layout.addWidget(self.fig_canvas, 1)

        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def handle_save_plot_clicked(self) -> None:
        default_name = self.fig_title.replace('/', '_').replace(':', '_')
        filepath = h.select_save_folder(default_name)
        if not filepath:
            return
        self.fig_canvas.figure.savefig(filepath, dpi=300)
