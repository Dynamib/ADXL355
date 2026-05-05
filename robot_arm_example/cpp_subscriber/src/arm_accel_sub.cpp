/**
 * Robot arm acceleration subscriber (C++).
 * Subscribes to /adxl355/accel and detects motion events.
 */

#include <chrono>
#include <cmath>
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/accel.hpp"

using namespace std::chrono_literals;

class ArmAccelSubscriber : public rclcpp::Node {
public:
  ArmAccelSubscriber()
  : Node("arm_accel_subscriber"), state_(State::IDLE) {

    rclcpp::QoS qos(rclcpp::KeepLast(10));
    qos.best_effort();

    subscription_ = this->create_subscription<geometry_msgs::msg::Accel>(
      "/adxl355/accel", qos,
      std::bind(&ArmAccelSubscriber::callback, this, std::placeholders::_1));

    RCLCPP_INFO(this->get_logger(),
      "Arm subscriber started. Threshold: %.1fg | Cooldown: %.1fs",
      MOTION_THRESHOLD, COOLDOWN_SECONDS);
  }

private:
  enum class State { IDLE, MOVING };

  static constexpr double MOTION_THRESHOLD = 0.5;  // g
  static constexpr double COOLDOWN_SECONDS = 2.0;

  rclcpp::Subscription<geometry_msgs::msg::Accel>::SharedPtr subscription_;
  State state_;
  rclcpp::Time last_event_time_{0, 0, RCL_ROS_TIME};

  void callback(const geometry_msgs::msg::Accel::SharedPtr msg) {
    double ax = msg->linear.x;
    double ay = msg->linear.y;
    double az = msg->linear.z;
    double magnitude = std::sqrt(ax * ax + ay * ay + az * az);

    auto now = this->now();

    if (state_ == State::IDLE) {
      if (magnitude > MOTION_THRESHOLD) {
        state_ = State::MOVING;
        last_event_time_ = now;
        RCLCPP_INFO(this->get_logger(),
          "MOTION DETECTED | mag=%.3fg | ax=%.3f ay=%.3f az=%.3f",
          magnitude, ax, ay, az);
        on_motion_start(magnitude, ax, ay, az);
      }
    } else if (state_ == State::MOVING) {
      if (magnitude <= MOTION_THRESHOLD) {
        double elapsed = (now - last_event_time_).seconds();
        if (elapsed > COOLDOWN_SECONDS) {
          state_ = State::IDLE;
          RCLCPP_INFO(this->get_logger(),
            "Motion ended. Returning to IDLE.");
          on_motion_end();
        }
      }
    }
  }

  void on_motion_start(double mag, double ax, double ay, double az) {
    // TODO: Replace with actual robot arm control logic.
    // Example:
    //   arm_client_->send_command("compensate_vibration",
    //                             ax, ay, az);
  }

  void on_motion_end() {
    // TODO: Replace with actual robot arm control logic.
    // Example:
    //   arm_client_->send_command("return_to_idle");
  }
};

int main(int argc, char * argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ArmAccelSubscriber>());
  rclcpp::shutdown();
  return 0;
}
