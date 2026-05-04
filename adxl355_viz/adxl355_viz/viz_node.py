"""ROS2 node for ADXL355 acceleration visualization."""

import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from geometry_msgs.msg import Accel

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from .data_buffer import RingBuffer, DataProcessor
from .main_window import MainWindow


class ADXL355VizNode(Node):
    """ROS2 node subscribing to /adxl355/accel and feeding the GUI."""

    def __init__(self, buffer: RingBuffer):
        super().__init__('adxl355_viz_node')

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10)

        self._sub = self.create_subscription(
            Accel, '/adxl355/accel',
            self._accel_callback, qos)

        self._buffer = buffer
        self._msg_count = 0
        self._last_rate_time = time.time()
        self._last_rate_count = 0
        self._current_rate = 0.0

        self.get_logger().info(
            'ADXL355 viz node started, listening on /adxl355/accel')

    def _accel_callback(self, msg: Accel):
        self._msg_count += 1

        # Use header timestamp if valid, else system time
        if msg.header.stamp.sec > 0 or msg.header.stamp.nanosec > 0:
            t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        else:
            t = time.time()

        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z

        self._buffer.append(t, ax, ay, az)

    def get_status(self):
        """Return (connected, rate_hz, sample_count)."""
        now = time.time()
        elapsed = now - self._last_rate_time
        if elapsed >= 1.0:
            delta = self._msg_count - self._last_rate_count
            self._current_rate = delta / elapsed
            self._last_rate_time = now
            self._last_rate_count = self._msg_count
        return (True, self._current_rate, self._msg_count)


def main():
    rclpy.init(args=sys.argv)

    # Qt application
    app = QApplication(sys.argv)
    app.setApplicationName('ADXL355 Monitor')

    # Shared data structures
    buffer = RingBuffer(capacity=30000)  # 500 Hz * 60 s
    processor = DataProcessor()

    # ROS2 node
    node = ADXL355VizNode(buffer)

    # GUI
    window = MainWindow(buffer, processor)
    window.show()

    # ROS spin timer: drives rclpy.spin_once() at high frequency
    # This keeps the ROS subscriber callback in the Qt main thread
    ros_timer = QTimer()
    ros_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0.001))
    ros_timer.start(1)  # ~1 kHz spin, matches 500 Hz incoming rate

    # Status update timer: update status bar at 2 Hz
    def update_status():
        connected, rate, count = node.get_status()
        window.update_status(connected, rate, count)
    status_timer = QTimer()
    status_timer.timeout.connect(update_status)
    status_timer.start(500)

    # Clean shutdown on Qt exit
    def on_quit():
        node.destroy_node()
        rclpy.shutdown()
    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec_())
