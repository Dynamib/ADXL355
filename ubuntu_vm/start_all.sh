#!/bin/bash
# ============================================================
# ADXL355 项目一键启动脚本
# 用法: ./start_all.sh [mode]
#   mode: agent    — 仅启动 micro-ROS Agent (默认)
#         echo     — Agent + ros2 topic echo
#         viz      — Agent + adxl355_viz 可视化
#         all      — Agent + echo + viz
# ============================================================
set -e

MODE=${1:-agent}
AGENT_PORT=${AGENT_PORT:-8888}
AGENT_TRANSPORT=${AGENT_TRANSPORT:-udp4}

# ====================== 环境清理与配置 ======================
# 清理 conda，避免库版本冲突
unset CONDA_PREFIX CONDA_EXE CONDA_PYTHON_EXE CONDA_SHLVL _CE_CONDA
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/ros/humble/bin

# 清理旧的 ros2 daemon (避免 domain/RMW 不匹配干扰)
echo "[清理] 关闭旧 ros2 daemon..."
pkill -f "ros2 daemon" 2>/dev/null || true
pkill -f "micro_ros_agent" 2>/dev/null || true
sleep 1
export HOME=/home/dy

# DDS 配置 — micro_ros_agent 必须使用 rmw_fastrtps_cpp
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/dds_profile.xml

# 如果 DDS profile 不存在，自动生成 (禁用 SHM，仅 UDP)
if [ ! -f "$FASTRTPS_DEFAULT_PROFILES_FILE" ]; then
    cat > "$FASTRTPS_DEFAULT_PROFILES_FILE" << 'XMLEOF'
<?xml version="1.0" encoding="UTF-8"?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>udp_only</transport_id>
      <type>UDPv4</type>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="default">
    <rtps>
      <useBuiltinTransports>false</useBuiltinTransports>
      <userTransports>
        <transport_id>udp_only</transport_id>
      </userTransports>
    </rtps>
  </participant>
</profiles>
XMLEOF
fi

# ====================== ROS2 环境 ======================
source /opt/ros/humble/setup.bash

# micro-ROS Agent
if [ -f "$HOME/microros_ws/install/local_setup.bash" ]; then
    source "$HOME/microros_ws/install/local_setup.bash"
fi

# adxl355_viz (如果已编译)
VIZ_WS="${ADXL355_VIZ_WS:-/tmp/viz_ws}"
if [ -f "$VIZ_WS/install/local_setup.bash" ]; then
    source "$VIZ_WS/install/local_setup.bash"
fi

# ====================== 1. 启动 Agent ======================
echo "=============================================="
echo "  ADXL355 micro-ROS 系统启动器"
echo "  模式: $MODE"
echo "=============================================="
echo ""

# 检查 Agent 是否已在运行
if pgrep -f "micro_ros_agent.*$AGENT_PORT" > /dev/null; then
    echo "[OK] micro-ROS Agent 已在运行 (port $AGENT_PORT)"
else
    echo "[启动] micro-ROS Agent (${AGENT_TRANSPORT}:${AGENT_PORT})..."
    ros2 run micro_ros_agent micro_ros_agent ${AGENT_TRANSPORT} --port ${AGENT_PORT} -v4 &
    AGENT_PID=$!
    sleep 2

    if ! kill -0 $AGENT_PID 2>/dev/null; then
        echo "[错误] Agent 启动失败!"
        exit 1
    fi
    echo "[OK] Agent 已启动 (PID $AGENT_PID)"
fi

# ====================== 2. 等待 ESP32 连接 ======================
echo ""
echo "[等待] 等待 ESP32 连接..."

WAIT_START=$(date +%s)
while true; do
    if ros2 topic list 2>/dev/null | grep -q "/adxl355/accel"; then
        echo "[OK] ESP32 已连接，话题 /adxl355/accel 就绪"
        break
    fi
    elapsed=$(( $(date +%s) - WAIT_START ))
    if [ $elapsed -gt 30 ]; then
        echo "[警告] 30 秒内未检测到 ESP32 连接"
        echo "  请检查: 1) ESP32 是否上电  2) WiFi 是否同一热点"
        echo "  将继续启动后续服务..."
        break
    fi
    sleep 2
done

# ====================== 3. 按模式启动服务 ======================
case "$MODE" in
    echo|all)
        echo ""
        echo "[启动] ros2 topic echo /adxl355/accel"
        ros2 topic echo /adxl355/accel &
        ECHO_PID=$!
        ;;&

    viz|all)
        echo ""
        if command -v ros2 > /dev/null && ros2 pkg list 2>/dev/null | grep -q adxl355_viz; then
            echo "[启动] adxl355_viz 可视化界面"
            ros2 run adxl355_viz viz_node &
            VIZ_PID=$!
        else
            echo "[跳过] adxl355_viz 未编译，请先运行:"
            echo "  mkdir -p /tmp/viz_ws/src"
            echo "  ln -s /home/dy/PCB/ADXL355/adxl355_viz /tmp/viz_ws/src/"
            echo "  cd /tmp/viz_ws && colcon build"
        fi
        ;;&

    agent)
        echo ""
        echo "[就绪] Agent 运行中，可使用以下命令查看数据:"
        echo "  ros2 topic echo /adxl355/accel --once"
        echo "  ros2 topic hz   /adxl355/accel"
        echo "  或运行: ./start_all.sh echo    (查看实时数据)"
        echo "  或运行: ./start_all.sh viz     (启动可视化)"
        ;;
esac

# ====================== 4. 显示运行状态 ======================
echo ""
echo "=============================================="
echo "  服务状态"
echo "=============================================="

# Agent
if pgrep -f "micro_ros_agent.*$AGENT_PORT" > /dev/null; then
    echo "  micro-ROS Agent : 运行中 (port $AGENT_PORT)"
else
    echo "  micro-ROS Agent : 已停止"
fi

# Echo
if [ -n "$ECHO_PID" ] && kill -0 $ECHO_PID 2>/dev/null; then
    echo "  topic echo      : 运行中"
fi

# Viz
if [ -n "$VIZ_PID" ] && kill -0 $VIZ_PID 2>/dev/null; then
    echo "  adxl355_viz     : 运行中"
fi

echo ""
echo "[提示] 按 Ctrl+C 停止所有服务"
echo "=============================================="

# ====================== 5. 等待退出 ======================
trap "echo ''; echo '[退出] 正在停止所有服务...'; kill \${AGENT_PID:-} \${ECHO_PID:-} \${VIZ_PID:-} 2>/dev/null; exit 0" INT TERM

# 持续运行直到用户中断
while true; do
    sleep 1
done
