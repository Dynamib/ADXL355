"""Main window for ADXL355 acceleration visualization."""

import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QToolBar, QAction, QStatusBar,
                             QDockWidget, QFileDialog, QComboBox,
                             QDoubleSpinBox, QSpinBox, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from .plot_widget import PlotWidget
from .stats_panel import StatsPanel
from .data_buffer import RingBuffer, DataProcessor
from .csv_handler import save_csv, load_csv, generate_filename


class MainWindow(QMainWindow):
    """ADXL355 Visualization main window."""

    DISPLAY_HZ = 30  # GUI refresh rate
    STATS_HZ = 5     # Statistics panel refresh rate

    def __init__(self, buffer: RingBuffer, processor: DataProcessor):
        super().__init__()
        self._buffer = buffer
        self._processor = processor
        self._recording = True
        self._msg_count = 0
        self._last_msg_time = 0.0
        self._current_rate = 0.0

        self.setWindowTitle('ADXL355 Acceleration Monitor — ROS2')
        self.resize(1200, 700)

        # Central plot
        self._plot = PlotWidget(self)
        self.setCentralWidget(self._plot)

        # Stats dock
        self._stats = StatsPanel()
        dock = QDockWidget('Statistics', self)
        dock.setWidget(self._stats)
        dock.setFeatures(QDockWidget.DockWidgetMovable |
                         QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Toolbar
        self._create_toolbar()

        # Menu bar
        self._create_menus()

        # Status bar
        self.setStatusBar(QStatusBar(self))
        self._status_ros = QLabel('ROS: —')
        self._status_rate = QLabel('Rate: — Hz')
        self._status_count = QLabel('Samples: 0')
        status_font = QFont('monospace', 9)
        self._status_ros.setFont(status_font)
        self._status_rate.setFont(status_font)
        self._status_count.setFont(status_font)
        self.statusBar().addWidget(self._status_ros)
        self.statusBar().addWidget(self._status_rate)
        self.statusBar().addWidget(self._status_count)

        # Display timer: ~30 Hz decimated plot update
        self._display_timer = QTimer(self)
        self._display_timer.timeout.connect(self._on_display_tick)
        self._display_timer.start(1000 // self.DISPLAY_HZ)

        # Stats timer: ~5 Hz
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._on_stats_tick)
        self._stats_timer.start(1000 // self.STATS_HZ)

    def _create_toolbar(self):
        tb = QToolBar('Controls', self)
        tb.setMovable(False)
        self.addToolBar(tb)

        # Start / Stop
        self._act_record = QAction('⏸ Stop', self)
        self._act_record.setShortcut('Space')
        self._act_record.triggered.connect(self._toggle_recording)
        tb.addAction(self._act_record)

        tb.addSeparator()

        # Clear
        act_clear = QAction('✕ Clear', self)
        act_clear.triggered.connect(self._clear)
        tb.addAction(act_clear)

        # Save CSV
        act_save = QAction('💾 Save CSV', self)
        act_save.setShortcut('Ctrl+S')
        act_save.triggered.connect(self._save_csv)
        tb.addAction(act_save)

        # Load CSV
        act_load = QAction('📂 Load CSV', self)
        act_load.setShortcut('Ctrl+O')
        act_load.triggered.connect(self._load_csv)
        tb.addAction(act_load)

        tb.addSeparator()

        # Smoothing mode
        tb.addWidget(QLabel(' Smooth: '))
        self._smooth_combo = QComboBox()
        self._smooth_combo.addItems(
            ['None', 'Mov. Avg', 'EMA', 'Both'])
        self._smooth_combo.currentIndexChanged.connect(self._on_smooth_mode)
        tb.addWidget(self._smooth_combo)

        # MA window
        tb.addWidget(QLabel(' MA N: '))
        self._ma_spin = QSpinBox()
        self._ma_spin.setRange(1, 100)
        self._ma_spin.setValue(5)
        self._ma_spin.valueChanged.connect(self._on_ma_window)
        tb.addWidget(self._ma_spin)

        # EMA alpha
        tb.addWidget(QLabel(' EMA α: '))
        self._ema_spin = QDoubleSpinBox()
        self._ema_spin.setRange(0.01, 1.0)
        self._ema_spin.setSingleStep(0.05)
        self._ema_spin.setValue(0.3)
        self._ema_spin.valueChanged.connect(self._on_ema_alpha)
        tb.addWidget(self._ema_spin)

        tb.addSeparator()

        # Time window
        tb.addWidget(QLabel(' Window: '))
        self._window_spin = QDoubleSpinBox()
        self._window_spin.setRange(1.0, 60.0)
        self._window_spin.setValue(10.0)
        self._window_spin.setSuffix(' s')
        self._window_spin.valueChanged.connect(
            lambda v: self._plot.set_window_width(v))
        tb.addWidget(self._window_spin)

    def _create_menus(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu('&File')
        file_menu.addAction('Save CSV...', self._save_csv, 'Ctrl+S')
        file_menu.addAction('Load CSV...', self._load_csv, 'Ctrl+O')
        file_menu.addSeparator()
        file_menu.addAction('Quit', self.close, 'Ctrl+Q')

        # View
        view_menu = menubar.addMenu('&View')
        view_menu.addAction('Toggle Dark/Light', self._toggle_theme)

        # Help
        help_menu = menubar.addMenu('&Help')
        help_menu.addAction('About', self._show_about)

    # ---- slots ----

    def _toggle_recording(self):
        self._recording = not self._recording
        if self._recording:
            self._act_record.setText('⏸ Stop')
        else:
            self._act_record.setText('▶ Start')

    def _clear(self):
        self._buffer.clear()
        self._plot.clear_plot()
        self._stats.clear()
        self._processor.reset()
        self._msg_count = 0
        self._current_rate = 0.0

    def _save_csv(self):
        t, x, y, z = self._buffer.get_all()
        if len(t) == 0:
            QMessageBox.warning(self, 'No Data', 'Buffer is empty.')
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save CSV', generate_filename(),
            'CSV Files (*.csv);;All Files (*)')
        if filename:
            save_csv(filename, t, x, y, z)
            self.statusBar().showMessage(
                f'Saved {len(t)} samples to {filename}', 5000)

    def _load_csv(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Load CSV', '', 'CSV Files (*.csv);;All Files (*)')
        if not filename:
            return
        try:
            t, x, y, z = load_csv(filename)
            self._buffer.clear()
            for i in range(len(t)):
                self._buffer.append(t[i], x[i], y[i], z[i])
            self._plot.set_window_width(60.0)
            self._window_spin.setValue(60.0)
            self.statusBar().showMessage(
                f'Loaded {len(t)} samples from {filename}', 5000)
        except Exception as e:
            QMessageBox.critical(self, 'Load Error', str(e))

    def _on_smooth_mode(self, index: int):
        self._processor.mode = index

    def _on_ma_window(self, size: int):
        self._processor.set_ma_window(size)

    def _on_ema_alpha(self, alpha: float):
        self._processor.set_ema_alpha(alpha)

    def _toggle_theme(self):
        if self._plot.backgroundBrush().color().lightness() < 128:
            # Currently dark -> light
            self._plot.setBackground('w')
            self._plot._plot.getAxis('left').setPen('k')
            self._plot._plot.getAxis('bottom').setPen('k')
        else:
            self._plot.setBackground('k')
            self._plot._plot.getAxis('left').setPen('w')
            self._plot._plot.getAxis('bottom').setPen('w')

    def _show_about(self):
        QMessageBox.about(
            self, 'About',
            'ADXL355 Acceleration Monitor\n'
            'ROS2 + micro-ROS + PyQt5 + pyqtgraph\n\n'
            'v0.1.0')

    # ---- timer callbacks ----

    def _on_display_tick(self):
        """Decimated display update (~30 Hz)."""
        if not self._recording:
            return
        t, x, y, z = self._buffer.get_window(self._plot._window_width)
        if len(t) == 0:
            return

        # Decimate to ~30 Hz for display performance
        n = max(1, len(t) // 500)  # show roughly 500 points max
        idx = np.linspace(0, len(t) - 1, min(len(t), 500)).astype(int)

        # Apply smoothing for display
        sx, sy, sz = self._processor.process_array(x, y, z)
        self._plot.update_plot(t[idx], sx[idx], sy[idx], sz[idx])

    def _on_stats_tick(self):
        """Statistics panel update (~5 Hz)."""
        t, x, y, z = self._buffer.get_window(1.0)  # last 1s for stats
        self._stats.update_stats(x, y, z)

    # ---- called by viz_node ----

    def update_status(self, connected: bool, rate: float, count: int):
        self._status_ros.setText(
            f'ROS: {"Connected" if connected else "Disconnected"}')
        self._status_rate.setText(f'Rate: {rate:.1f} Hz')
        self._status_count.setText(f'Samples: {count}')
