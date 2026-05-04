"""Data buffer and smoothing filters for ADXL355 acceleration data."""

import threading
import numpy as np
from collections import deque


class RingBuffer:
    """Thread-safe fixed-capacity ring buffer for time-series data."""

    def __init__(self, capacity: int = 30000):
        self._capacity = capacity
        self._time = deque(maxlen=capacity)
        self._x = deque(maxlen=capacity)
        self._y = deque(maxlen=capacity)
        self._z = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def append(self, t: float, ax: float, ay: float, az: float):
        with self._lock:
            self._time.append(t)
            self._x.append(ax)
            self._y.append(ay)
            self._z.append(az)

    def get_window(self, seconds: float):
        """Return last N seconds of data as numpy arrays."""
        with self._lock:
            if not self._time:
                return (np.array([]), np.array([]), np.array([]),
                        np.array([]))
            cutoff = self._time[-1] - seconds
            t = np.array(self._time, dtype=np.float64)
            x = np.array(self._x, dtype=np.float64)
            y = np.array(self._y, dtype=np.float64)
            z = np.array(self._z, dtype=np.float64)
            mask = t >= cutoff
            return t[mask], x[mask], y[mask], z[mask]

    def get_all(self):
        """Return all buffered data as numpy arrays."""
        with self._lock:
            return (np.array(self._time, dtype=np.float64),
                    np.array(self._x, dtype=np.float64),
                    np.array(self._y, dtype=np.float64),
                    np.array(self._z, dtype=np.float64))

    def clear(self):
        with self._lock:
            self._time.clear()
            self._x.clear()
            self._y.clear()
            self._z.clear()

    @property
    def size(self) -> int:
        return len(self._time)

    @property
    def latest(self):
        """Return latest (t, ax, ay, az) or None if empty."""
        with self._lock:
            if not self._time:
                return None
            return (self._time[-1], self._x[-1], self._y[-1], self._z[-1])


class MovingAverageFilter:
    """Simple moving average (boxcar) filter."""

    def __init__(self, window_size: int = 5):
        self._window = deque(maxlen=max(1, window_size))

    def apply(self, value: float) -> float:
        self._window.append(value)
        return sum(self._window) / len(self._window)

    def reset(self):
        self._window.clear()


class ExponentialMovingAverage:
    """Exponential moving average filter."""

    def __init__(self, alpha: float = 0.3):
        self._alpha = max(0.0, min(1.0, alpha))
        self._ema = None

    def apply(self, value: float) -> float:
        if self._ema is None:
            self._ema = value
        else:
            self._ema = self._alpha * value + (1.0 - self._alpha) * self._ema
        return self._ema

    def reset(self):
        self._ema = None


class DataProcessor:
    """Combined smoothing: none, moving average, EMA, or both."""

    MODE_NONE = 0
    MODE_MA = 1
    MODE_EMA = 2
    MODE_BOTH = 3

    def __init__(self):
        self._mode = self.MODE_NONE
        self._ma_x = MovingAverageFilter(5)
        self._ma_y = MovingAverageFilter(5)
        self._ma_z = MovingAverageFilter(5)
        self._ema_x = ExponentialMovingAverage(0.3)
        self._ema_y = ExponentialMovingAverage(0.3)
        self._ema_z = ExponentialMovingAverage(0.3)

    @property
    def mode(self) -> int:
        return self._mode

    @mode.setter
    def mode(self, value: int):
        if value != self._mode:
            self.reset()
            self._mode = value

    def set_ma_window(self, size: int):
        self._ma_x = MovingAverageFilter(size)
        self._ma_y = MovingAverageFilter(size)
        self._ma_z = MovingAverageFilter(size)

    def set_ema_alpha(self, alpha: float):
        self._ema_x = ExponentialMovingAverage(alpha)
        self._ema_y = ExponentialMovingAverage(alpha)
        self._ema_z = ExponentialMovingAverage(alpha)

    def process(self, ax: float, ay: float, az: float):
        if self._mode == self.MODE_NONE:
            return ax, ay, az
        elif self._mode == self.MODE_MA:
            return (self._ma_x.apply(ax),
                    self._ma_y.apply(ay),
                    self._ma_z.apply(az))
        elif self._mode == self.MODE_EMA:
            return (self._ema_x.apply(ax),
                    self._ema_y.apply(ay),
                    self._ema_z.apply(az))
        elif self._mode == self.MODE_BOTH:
            return (self._ema_x.apply(self._ma_x.apply(ax)),
                    self._ema_y.apply(self._ma_y.apply(ay)),
                    self._ema_z.apply(self._ma_z.apply(az)))
        return ax, ay, az

    def process_array(self, x: np.ndarray, y: np.ndarray, z: np.ndarray):
        """Batch-process history arrays (offline smoothing)."""
        if self._mode == self.MODE_NONE:
            return x.copy(), y.copy(), z.copy()
        self.reset()
        out_x = np.array([self.process(vx, 0, 0)[0]
                          for vx in x], dtype=np.float64)
        self.reset()
        out_y = np.array([self.process(0, vy, 0)[1]
                          for vy in y], dtype=np.float64)
        self.reset()
        out_z = np.array([self.process(0, 0, vz)[2]
                          for vz in z], dtype=np.float64)
        return out_x, out_y, out_z

    def reset(self):
        self._ma_x.reset()
        self._ma_y.reset()
        self._ma_z.reset()
        self._ema_x.reset()
        self._ema_y.reset()
        self._ema_z.reset()
