cmake_minimum_required(VERSION 3.8)
project(arm_accel_subscriber)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

add_executable(arm_accel_sub src/arm_accel_sub.cpp)
ament_target_dependencies(arm_accel_sub rclcpp geometry_msgs)

install(TARGETS arm_accel_sub
  DESTINATION lib/${PROJECT_NAME})

ament_package()
