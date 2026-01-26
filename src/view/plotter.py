from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from pandas import DataFrame

import src.helpers.helpers as h


def plot_sweep(
    filepath: str, start_time: str, stop_time: str, direction: str
) -> Figure:
    df: DataFrame = pd.read_csv(filepath)
    start_idx: int = df.loc[df['Time'] == start_time].index.tolist()[0]
    stop_idx: int = df.loc[df['Time'] == stop_time].index.tolist()[0]

    fig, ax = plt.subplots()

    x = df['Source Pressure (mBar)'][start_idx:stop_idx]
    y = df['Beam Current (A)'][start_idx:stop_idx]

    ax.plot(x, y)

    return fig


if __name__ == '__main__':
    filepath = r'\\opdata2\Company\PRODUCTION FOLDER\Production History\S-N 1119 18465 H100 Cameca\Raw Test Data\1119 1_12_2026.csv'
    start_time = '1/12/2026 11:55:42 AM'
    end_time = '1/12/2026 11:59:59 PM'
    direction = 'H2L'
    fig = plot_sweep(filepath, start_time, end_time, direction)
    plt.show()
