# Ubuntu 虚拟机配置指南

## 目录

- `start_all.sh` — **一键启动脚本** (推荐)
- `launch_agent.sh` — 单独启动 micro-ROS Agent
- `echo_accel.sh` — ros2 topic echo /adxl355/accel
- `setup_microros_agent.sh` — 编译安装 micro-ROS Agent
- `ufw_firewall_setup.sh` — 防火墙放行 UDP 8888

## 一键启动

```bash
cd ubuntu_vm

# 仅 Agent
./start_all.sh

# Agent + 终端实时数据
./start_all.sh echo

# Agent + GUI 可视化
./start_all.sh viz

# 全部
./start_all.sh all
```

按 `Ctrl+C` 停止所有服务。

## 单独启动

```bash
# 终端1: 启动 Agent
./launch_agent.sh 8888 udp4

# 终端2: 查看数据
./echo_accel.sh

# 终端3 (可选): 可视化
ros2 run adxl355_viz viz_node
```

## 环境要求

| 参数 | 值 | 说明 |
|------|-----|------|
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | micro_ros_agent 依赖 Fast-DDS |
| `ROS_DOMAIN_ID` | `0` | ESP32 micro-ROS 硬编码 domain 0 |
| Agent 端口 | `UDP 8888` | 与 ESP32 固件 `MICRO_ROS_AGENT_PORT` 一致 |

> 以上环境变量由 `start_all.sh` 和 `launch_agent.sh` 自动设置，无需手动配置。

## 网络配置

1. 虚拟机设置为**桥接模式**，桥接到宿主机 WiFi 网卡
2. 确认虚拟机和 ESP32 连接同一热点，且能互相 ping 通
3. ESP32 IP 固定在 `config/wifi_config.h` 中配置

## 编译可视化包

```bash
mkdir -p /tmp/viz_ws/src
ln -s /home/dy/PCB/ADXL355/adxl355_viz /tmp/viz_ws/src/adxl355_viz
cd /tmp/viz_ws
source /opt/ros/humble/setup.bash
colcon build
```

## 故障排查

| 问题 | 检查 |
|------|------|
| Agent 启动失败 | 端口是否被占用: `ss -uln \| grep 8888` |
| 收不到 ESP32 数据 | 1. ping ESP32 IP 2. ESP32 是否上电 3. 是否同一 WiFi |
| 桥接网络无 IP | VMware: 编辑→虚拟网络编辑器→桥接模式选择正确网卡 |
| ROS2 无话题 | `echo $ROS_DOMAIN_ID` 确认=0, `echo $RMW_IMPLEMENTATION` 确认=fastrtps |
| Agent fmt/spdlog 报错 | conda 冲突，用 `start_all.sh` 自动清理环境 |
