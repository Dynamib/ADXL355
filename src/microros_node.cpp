#include "microros_node.h"
#include "adxl355_sensor.h"
#include "wifi_config.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <rmw_microros/time_sync.h>
#include <rmw_microros/custom_transport.h>

// Transport function declarations (defined in micro_ros_transport.cpp)
extern "C" {
bool platformio_transport_open(struct uxrCustomTransport *transport);
bool platformio_transport_close(struct uxrCustomTransport *transport);
size_t platformio_transport_write(struct uxrCustomTransport *transport,
                                  const uint8_t *buf, size_t len, uint8_t *err);
size_t platformio_transport_read(struct uxrCustomTransport *transport,
                                 uint8_t *buf, size_t len, int timeout, uint8_t *err);
}

struct micro_ros_agent_locator {
  IPAddress address;
  int port;
};

static bool setupTransport() {
  static struct micro_ros_agent_locator locator;
  IPAddress agent_ip;
  if (!agent_ip.fromString(MICRO_ROS_AGENT_IP)) {
    return false;
  }
  locator.address = agent_ip;
  locator.port = MICRO_ROS_AGENT_PORT;

  return RCL_RET_OK == rmw_uros_set_custom_transport(
      false,
      (void *)&locator,
      platformio_transport_open,
      platformio_transport_close,
      platformio_transport_write,
      platformio_transport_read);
}

bool microros_connected = false;

static rcl_allocator_t allocator;
static rclc_support_t support;
static rcl_node_t node;
static rcl_publisher_t publisher;
static rcl_timer_t timer;
static rclc_executor_t executor;
static geometry_msgs__msg__Accel accel_msg;

static void timerPublishCallback(rcl_timer_t *timer, int64_t last_call_time) {
  (void)last_call_time;

  VibrationData data;
  // Drain queue: keep the newest sample
  bool gotData = false;
  while (xQueueReceive(sensorQueue, &data, 0) == pdTRUE) {
    gotData = true;
  }

  if (!gotData) {
    return; // no new sensor data, skip this publish slot
  }

  accel_msg.linear.x = static_cast<double>(data.x);
  accel_msg.linear.y = static_cast<double>(data.y);
  accel_msg.linear.z = static_cast<double>(data.z);

  rcl_publish(&publisher, &accel_msg, NULL);
}

bool initMicroROS() {
  // WiFi must already be connected before calling this
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  if (!setupTransport()) {
    return false;
  }

  delay(100); // let transport settle

  allocator = rcl_get_default_allocator();

  if (rclc_support_init(&support, 0, NULL, &allocator) != RCL_RET_OK) {
    return false;
  }

  if (rclc_node_init_default(&node, "esp32_adxl355_node", "", &support) != RCL_RET_OK) {
    return false;
  }

  if (rclc_publisher_init_best_effort(
          &publisher, &node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Accel),
          "/adxl355/accel") != RCL_RET_OK) {
    return false;
  }

  const unsigned int timer_period_ms = 1000 / PUBLISH_RATE_HZ; // 2 ms @ 500 Hz
  if (rclc_timer_init_default(&timer, &support,
                               RCL_MS_TO_NS(timer_period_ms),
                               timerPublishCallback) != RCL_RET_OK) {
    return false;
  }

  if (rclc_executor_init(&executor, &support.context, 1, &allocator) != RCL_RET_OK) {
    return false;
  }
  rclc_executor_add_timer(&executor, &timer);

  accel_msg.linear.x = 0.0;
  accel_msg.linear.y = 0.0;
  accel_msg.linear.z = 0.0;
  accel_msg.angular.x = 0.0;
  accel_msg.angular.y = 0.0;
  accel_msg.angular.z = 0.0;

  return true;
}

void taskMicroROSSpin(void *pvParameters) {
  for (;;) {
    if (microros_connected) {
      rclc_executor_spin_some(&executor, RCL_MS_TO_NS(1));
      digitalWrite(LED_PIN, LOW);  // connected: LED off
    } else {
      // Fast blink: attempting reconnect
      digitalWrite(LED_PIN, (millis() / 200) % 2 ? HIGH : LOW);

      if (WiFi.status() == WL_CONNECTED) {
        microros_connected = initMicroROS();
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}
