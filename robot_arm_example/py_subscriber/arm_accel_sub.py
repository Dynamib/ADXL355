#!/usr/bin/env python3
"""Robot arm acceleration subscriber with motion detection."""

import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from geometry_msgs.msg import Accel

MOTION_THRESHOLD = 0.5  # g — acceleration magnitude above which to trigger
COOLDOWN_SECONDS = 2.0  # minimum time between motion events


class ArmAccelSubscriber(Node):
    """Subscribes to /adxl355/accel and detects motion events."""

    def __init__(self):
        super().__init__('arm_accel_subscriber')

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10)

        self._sub = self.create_subscription(
            Accel, '/adxl355/accel', self._callback, qos)

        self._state = 'IDLE'
        self._last_event_time = 0.0
        self._msg_count = 0
        self._last_log_time = time.time()

        self.get_logger().info(
            f'Arm subscriber started. Threshold: {MOTION_THRESHOLD}g | '
            f'Cooldown: {COOLDOWN_SECONDS}s')

    def _callback(self, msg: Accel):
        self._msg_count += 1

        ax = msg.linear.x
        ay = msg.linear.y
        az = msg.linear.z
        magnitude = math.sqrt(ax * ax + ay * ay + az * az)

        now = time.time()

        if self._state == 'IDLE':
            if magnitude > MOTION_THRESHOLD:
                self._state = 'MOVING'
                self._last_event_time = now
                self.get_logger().info(
                    f'MOTION DETECTED | mag={magnitude:.3f}g | '
                    f'ax={ax:.3f} ay={ay:.3f} az={az:.3f}')
                self._on_motion_start(magnitude, ax, ay, az)

        elif self._state == 'MOVING':
            if magnitude <= MOTION_THRESHOLD:
                if now - self._last_event_time > COOLDOWN_SECONDS:
                    self._state = 'IDLE'
                    self.get_logger().info(
                        f'Motion ended. Returning to IDLE.')
                    self._on_motion_end()

        # Periodic rate logging
        if now - self._last_log_time >= 5.0:
            rate = self._msg_count / (now - self._last_log_time)
            self.get_logger().info(
                f'Status: {self._state} | Rate: {rate:.1f} Hz')
            self._msg_count = 0
            self._last_log_time = now

    def _on_motion_start(self, mag: float, ax: float, ay: float, az: float):
        """Called when vibration exceeds threshold.
        Replace with actual robot arm control logic."""
        # Example: send command to robot arm
        # self._arm_client.send_command(
        #     f'compensate_vibration {ax:.4f} {ay:.4f} {az:.4f}')
        pass

    def _on_motion_end(self):
        """Called when vibration drops below threshold for cooldown period.
        Replace with actual robot arm control logic."""
        # Example: return arm to normal position
        # self._arm_client.send_command('return_to_idle')
        pass


def main():
    rclpy.init()
    node = ArmAccelSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
