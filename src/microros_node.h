#ifndef MICROROS_NODE_H
#define MICROROS_NODE_H

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/accel.h>

extern bool microros_connected;

bool initMicroROS();
void taskMicroROSSpin(void *pvParameters);

#endif
