from pathlib import Path
from typing import cast

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


class PlotWindow(QMainWindow):
    """
    Shows a plot from the hyperion test stand software csv.

    Example usage:
        >>> filepath = "path/to/hyperion/csv.csv"
        >>> sweep_start = "1/1/2026 9:03:24 AM"
        >>> sweep_stop = "1/1/2026 9:10:03 AM"
        >>> direction = "H2L"  # or "L2H"
        >>> plot_window = PlotWindow(parent=self)
        >>> fig = plot_window.create_fig(filepath, sweep_start, sweep_stop)
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

    def create_fig(
        self, filepath: str, start_time: str, stop_time: str, direction: str
    ) -> Figure:
        df: DataFrame = pd.read_csv(filepath)
        start_idx: int = df.loc[df['Time'] == start_time].index.tolist()[0]
        stop_idx: int = df.loc[df['Time'] == stop_time].index.tolist()[0]

        fig = Figure(dpi=120)
        ax = fig.add_subplot(111)
        y_scale = 1e9

        x = df['Source Pressure (mBar)'][start_idx:stop_idx]
        y = df['Beam Current (A)'][start_idx:stop_idx] * y_scale

        current_slice = df['Beam Current (A)'][start_idx:stop_idx]
        peak_idx = current_slice.abs().idxmax()
        peak_current = df.loc[peak_idx, 'Beam Current (A)']
        self.peak_current = float(cast(float, peak_current)) * y_scale
        peak_pressure = df.loc[peak_idx, 'Source Pressure (mBar)']
        self.peak_pressure = float(cast(float, peak_pressure))

        ax.set_title(f'{Path(filepath).name}')
        ax.set_xlabel('Pressure (mBar)')
        ax.set_ylabel('Cup Current (nA)')
        ax.plot(x, y)
        ax.legend([direction])

        return fig

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Pressure Sweep')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit, QSpinBox {color: lightgreen;}'
        )

        peak_current_label = QLabel(f'Peak Current: {self.peak_current:.2f} nA')
        peak_current_label.setStyleSheet('font-size: 18pt;')
        peak_pressure_label = QLabel(f'Peak Pressure: {self.peak_pressure:.2e} mBar')
        peak_pressure_label.setStyleSheet('font-size: 18pt;')

        peak_layout = QHBoxLayout()
        peak_layout.addWidget(peak_current_label)
        peak_layout.addWidget(peak_pressure_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(peak_layout)
        main_layout.addWidget(self.fig_canvas)

        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
