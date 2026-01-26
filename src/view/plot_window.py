from typing import cast

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pandas import DataFrame
from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet


class PlotWindow(QMainWindow):
    def __init__(self, parent: QWidget, fig_canvas: FigureCanvas) -> None:
        super().__init__(parent)
        self.fig_canvas = fig_canvas
        self.create_gui()

    @staticmethod
    def create_fig(
        filepath: str, start_time: str, stop_time: str, direction: str
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
        peak_pressure = df.loc[peak_idx, 'Source Pressure (mBar)']
        peak_x = float(cast(float, peak_pressure))
        peak_y = float(cast(float, peak_current)) * y_scale

        ax.set_xlabel('Pressure (mBar)')
        ax.set_ylabel('Cup Current (nA)')
        ax.plot(x, y)
        ax.legend([direction])
        ax.annotate(
            f'Peak: {peak_pressure:.2e} mBar',
            xy=(peak_x, peak_y),
            textcoords='offset points',
            xytext=(0, 10),
            ha='center',
        )

        return fig

    def create_gui(self) -> None:
        # Set the window size
        self.setWindowTitle('Pressure Sweep')
        apply_stylesheet(self, theme='dark_lightgreen.xml', invert_secondary=True)
        self.setStyleSheet(
            self.styleSheet() + 'QLineEdit, QTextEdit, QSpinBox {color: lightgreen;}'
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.fig_canvas)

        self.setLayout(main_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
