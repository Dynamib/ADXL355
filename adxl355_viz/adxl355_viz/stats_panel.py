"""Statistics panel for ADXL355 acceleration data."""

import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                             QLabel, QGroupBox)


class StatsPanel(QWidget):
    """Docked panel showing per-axis statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)

        for axis in ['X', 'Y', 'Z']:
            group = QGroupBox(f'{axis}-Axis')
            form = QFormLayout(group)

            self.__dict__[f'_lbl_{axis}_current'] = QLabel('—')
            self.__dict__[f'_lbl_{axis}_mean'] = QLabel('—')
            self.__dict__[f'_lbl_{axis}_pp'] = QLabel('—')
            self.__dict__[f'_lbl_{axis}_rms'] = QLabel('—')

            form.addRow('Current:', self.__dict__[f'_lbl_{axis}_current'])
            form.addRow('Mean:', self.__dict__[f'_lbl_{axis}_mean'])
            form.addRow('Peak-Peak:', self.__dict__[f'_lbl_{axis}_pp'])
            form.addRow('RMS:', self.__dict__[f'_lbl_{axis}_rms'])

            layout.addWidget(group)

        layout.addStretch()

    def update_stats(self, x: np.ndarray, y: np.ndarray, z: np.ndarray):
        """Update statistics from data arrays."""
        for axis, data in [('X', x), ('Y', y), ('Z', z)]:
            if len(data) == 0:
                continue
            self.__dict__[f'_lbl_{axis}_current'].setText(f'{data[-1]:.4f} g')
            self.__dict__[f'_lbl_{axis}_mean'].setText(f'{np.mean(data):.4f} g')
            pp = np.max(data) - np.min(data)
            self.__dict__[f'_lbl_{axis}_pp'].setText(f'{pp:.4f} g')
            rms = np.sqrt(np.mean(data ** 2))
            self.__dict__[f'_lbl_{axis}_rms'].setText(f'{rms:.4f} g')

    def clear(self):
        for axis in ['X', 'Y', 'Z']:
            self.__dict__[f'_lbl_{axis}_current'].setText('—')
            self.__dict__[f'_lbl_{axis}_mean'].setText('—')
            self.__dict__[f'_lbl_{axis}_pp'].setText('—')
            self.__dict__[f'_lbl_{axis}_rms'].setText('—')
