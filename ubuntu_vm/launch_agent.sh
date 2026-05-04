#!/bin/bash
# ============================================================
# 一键启动 micro-ROS Agent
# 用法: ./launch_agent.sh [port] [transport]
#   port      — UDP 端口 (默认 8888)
#   transport — 传输协议 (默认 udp4)
# ============================================================

AGENT_PORT=${1:-8888}
AGENT_TRANSPORT=${2:-udp4}

echo "=== micro-ROS Agent ==="
echo "Transport: ${AGENT_TRANSPORT}"
echo "Port:      ${AGENT_PORT}"
echo ""

# 清理 conda 环境，避免 fmt 版本冲突
unset CONDA_PREFIX
unset CONDA_EXE
unset CONDA_PYTHON_EXE
unset CONDA_SHLVL
unset _CE_CONDA
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/ros/humble/bin
export HOME=/home/dy

# DDS 配置 (必须与 agent 编译的 RMW 一致)
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/dds_profile.xml

source /opt/ros/humble/setup.bash
source "$HOME/microros_ws/install/local_setup.bash"

ros2 run micro_ros_agent micro_ros_agent ${AGENT_TRANSPORT} --port ${AGENT_PORT} -v4
