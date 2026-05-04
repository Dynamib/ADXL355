"""CSV save/load for ADXL355 acceleration data."""

import csv
import numpy as np
from datetime import datetime


def generate_filename() -> str:
    """Generate timestamped CSV filename."""
    return f"adxl355_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def save_csv(filename: str, t: np.ndarray, x: np.ndarray,
             y: np.ndarray, z: np.ndarray):
    """Save data to CSV with header: timestamp, accel_x, accel_y, accel_z."""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'accel_x', 'accel_y', 'accel_z'])
        for i in range(len(t)):
            writer.writerow([f'{t[i]:.6f}',
                             f'{x[i]:.6f}',
                             f'{y[i]:.6f}',
                             f'{z[i]:.6f}'])


def load_csv(filename: str):
    """Load CSV, return (time, x, y, z) as numpy arrays."""
    data = np.loadtxt(filename, delimiter=',', skiprows=1, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return (data[:, 0], data[:, 1], data[:, 2], data[:, 3])
