#!/bin/bash
# ============================================================
# 订阅 /adxl355/accel 话题并查看数据
# ============================================================

unset CONDA_PREFIX
unset CONDA_EXE
unset CONDA_PYTHON_EXE
unset CONDA_SHLVL
unset _CE_CONDA
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/ros/humble/bin
export HOME=/home/dy

export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/dds_profile.xml

source /opt/ros/humble/setup.bash

echo "=== Listening to /adxl355/accel ==="
echo "Use Ctrl+C to stop"
ros2 topic echo /adxl355/accel
