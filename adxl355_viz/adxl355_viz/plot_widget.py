"""pyqtgraph-based real-time plot widget for 3-axis acceleration."""

import pyqtgraph as pg
import numpy as np


class PlotWidget(pg.GraphicsLayoutWidget):
    """Real-time scrolling 3-axis acceleration plot."""

    COLORS = {'x': (255, 60, 60), 'y': (60, 200, 60), 'z': (60, 120, 255)}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('k')

        self._plot = self.addPlot(row=0, col=0)
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel('left', 'Acceleration', units='g')
        self._plot.setLabel('bottom', 'Time', units='s')
        self._plot.addLegend(offset=(5, 5))

        self._curves = {}
        for axis, color in self.COLORS.items():
            pen = pg.mkPen(color=color, width=1.2)
            self._curves[axis] = self._plot.plot(
                [], [], pen=pen, name=axis.upper())

        self._window_width = 10.0  # seconds
        self._y_min = -2.0
        self._y_max = 2.0
        self._auto_y = True

    def set_window_width(self, seconds: float):
        self._window_width = max(1.0, seconds)

    def set_y_range(self, y_min: float, y_max: float):
        self._y_min = y_min
        self._y_max = y_max
        self._auto_y = False

    def set_auto_y(self, enabled: bool):
        self._auto_y = enabled

    def update_plot(self, t: np.ndarray, x: np.ndarray,
                    y: np.ndarray, z: np.ndarray):
        """Update curves. Data is decimated by caller for display performance."""
        self._curves['x'].setData(t, x)
        self._curves['y'].setData(t, y)
        self._curves['z'].setData(t, z)

        if len(t) > 0:
            t_max = t[-1]
            self._plot.setXRange(max(0, t_max - self._window_width), t_max)

        if self._auto_y and len(x) > 0 and len(y) > 0 and len(z) > 0:
            data_min = min(np.min(x), np.min(y), np.min(z))
            data_max = max(np.max(x), np.max(y), np.max(z))
            margin = max((data_max - data_min) * 0.1, 0.01)
            self._plot.setYRange(data_min - margin, data_max + margin)
        else:
            self._plot.setYRange(self._y_min, self._y_max)

    def clear_plot(self):
        for curve in self._curves.values():
            curve.setData([], [])
