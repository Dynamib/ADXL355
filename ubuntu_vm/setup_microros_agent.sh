#!/bin/bash
# ============================================================
# micro-ROS Agent 一键安装脚本
# 适用于 Ubuntu 22.04 + ROS2 Humble
# ============================================================
set -e

echo "=== micro-ROS Agent 安装脚本 ==="

# 1. 检查 ROS2 Humble 是否已安装
if [ ! -f /opt/ros/humble/setup.bash ]; then
    echo "错误: 未找到 ROS2 Humble，请先安装 ROS2 Humble。"
    echo "参考: https://docs.ros.org/en/humble/Installation.html"
    exit 1
fi

source /opt/ros/humble/setup.bash

# 2. 创建工作空间
WORKSPACE_DIR="$HOME/microros_ws"
if [ -d "$WORKSPACE_DIR" ]; then
    echo "工作空间 $WORKSPACE_DIR 已存在，跳过克隆步骤。"
    echo "如需重新安装，请先删除该目录。"
else
    mkdir -p "$WORKSPACE_DIR/src"
    cd "$WORKSPACE_DIR"

    echo "正在克隆 micro_ros_setup (humble 分支)..."
    git clone -b humble https://github.com/micro-ROS/micro_ros_setup.git src/micro_ros_setup

    echo "正在安装依赖..."
    sudo apt-get update
    rosdep update
    rosdep install --from-paths src --ignore-src -y

    echo "正在编译 micro_ros_setup..."
    colcon build
fi

source "$WORKSPACE_DIR/install/local_setup.bash"

# 3. 创建并编译 agent 工作空间
AGENT_WS="$WORKSPACE_DIR/agent_ws"
if [ -d "$AGENT_WS" ]; then
    echo "Agent 工作空间 $AGENT_WS 已存在，跳过创建。"
else
    echo "正在创建 agent 工作空间..."
    ros2 run micro_ros_setup create_agent_ws.sh
    echo "正在编译 micro-ROS Agent..."
    ros2 run micro_ros_setup build_agent.sh
fi

echo ""
echo "=== 安装完成 ==="
echo "使用以下命令启动 Agent:"
echo "  source /opt/ros/humble/setup.bash"
echo "  source $WORKSPACE_DIR/install/local_setup.bash"
echo "  ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888 -v4"
echo ""
echo "或使用 launch_agent.sh 脚本一键启动。"
