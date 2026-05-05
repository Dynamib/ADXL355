# ESP32 + ADXL355 micro-ROS 加速度采集与可视化系统

## 项目概述

使用 ESP32 驱动 ADXL355 加速度传感器（500Hz），通过 WiFi 连接至局域网，作为 micro-ROS 节点向 Ubuntu 虚拟机发布传感器数
据。虚拟机内运行 ROS2 Humble、micro-ROS Agent 及可视化程序。

## 系统架构

```
ESP32 (micro-ROS)                  Ubuntu VM (ROS2 Humble)
┌─────────────────┐   UDP:8888   ┌──────────────────────────┐
│ ADXL355 @500Hz   │─────────────>│  micro_ros_agent         │
│ WiFi STA 模式    │              │    ↓                     │
│ 发布 /adxl355/   │              │  DDS (Fast-DDS)          │
│  accel           │              │    ↓           ↓         │
│ (geometry_msgs/  │              │  echo        viz_node    │
│  Accel)          │              │ (终端)      (PyQt5 GUI)  │
└─────────────────┘              └──────────────────────────┘
```

**通信协议**: micro-ROS XRCE over UDP (port 8888) → Fast-DDS domain 0

## 项目服务说明

| 服务 | 位置 | 说明 |
|------|------|------|
| **ESP32 固件** | `src/` | ADXL355 驱动 + micro-ROS 发布节点，需烧录到 ESP32 |
| **micro-ROS Agent** | `ubuntu_vm/` | UDP→DDS 桥接，运行在 Ubuntu VM |
| **adxl355_viz** | `adxl355_viz/` | PyQt5 实时可视化 GUI (ROS2 节点) |
| **topic echo** | `ubuntu_vm/` | 终端查看实时数据 |
| **arm 订阅示例** | `robot_arm_example/` | Python/C++ 订阅 /adxl355/accel 示例 |

## 硬件需求与接线

| ADXL355 | ESP32 |
|---------|-------|
| VCC     | 3.3V  |
| GND     | GND   |
| CS      | GPIO 5 |
| SCK     | GPIO 18 |
| MOSI    | GPIO 23 |
| MISO    | GPIO 19 |
| DRDY    | GPIO 4 |

## 快速开始

### 1. ESP32 固件烧录（一次性）

```bash
# 复制配置模板，填入实际 WiFi 和 Agent IP
cp config/wifi_config.h.example config/wifi_config.h
# 编辑 config/wifi_config.h:
#   WIFI_SSID / WIFI_PASSWORD → 手机热点
#   MICRO_ROS_AGENT_IP       → Ubuntu 虚拟机 IP

# 编译并烧录
pio run --target upload

# 查看串口日志确认状态
pio device monitor
```

**状态指示灯 (GPIO 2)**:
- 慢闪 (500ms) → WiFi 连接中
- 熄灭 → 已连接 Agent，正常工作
- 快闪 (200ms) → Agent 断线，自动重连中

### 2. Ubuntu VM 环境准备（一次性）

```bash
# 安装 ROS2 Humble (如未安装)
# https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html

# 编译安装 micro-ROS Agent
cd ubuntu_vm
./setup_microros_agent.sh

# 编译可视化包 (可选)
mkdir -p /tmp/viz_ws/src
ln -s $(pwd)/../adxl355_viz /tmp/viz_ws/src/adxl355_viz
cd /tmp/viz_ws
colcon build
```

**网络要求**: 虚拟机桥接模式，与 ESP32 连接同一 WiFi（手机热点）。

### 3. 一键启动所有服务

```bash
cd ubuntu_vm

# 仅启动 Agent (终端查看数据)
./start_all.sh

# Agent + 终端 echo
./start_all.sh echo

# Agent + 可视化界面
./start_all.sh viz

# 全部启动
./start_all.sh all
```

**工作流程**: 脚本自动清理 conda 环境 → 启动 Agent → 等待 ESP32 连接 → 启动所选服务。
按 `Ctrl+C` 停止所有服务。

### 4. 单独启动各服务

```bash
# 仅 Agent
./launch_agent.sh 8888 udp4

# 终端查看数据 (另一个终端)
./echo_accel.sh

# 可视化界面 (另一个终端)
unset CONDA_PREFIX && export RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  && export ROS_DOMAIN_ID=0 && source /opt/ros/humble/setup.bash \
  && source /tmp/viz_ws/install/local_setup.bash \
  && ros2 run adxl355_viz viz_node
```

### 5. 验证

```bash
# 查看话题列表
ros2 topic list
# 应看到 /adxl355/accel

# 查看单次数据 (Z 轴应接近 1.0g)
ros2 topic echo /adxl355/accel --once

# 查看发布频率
ros2 topic hz /adxl355/accel
```

## 可视化程序 (adxl355_viz) 功能

| 功能 | 说明 |
|------|------|
| 3 轴实时波形 | X(红) / Y(绿) / Z(蓝)，时间窗口可调 1~60s |
| 开始/停止 | 暂停/恢复显示，数据仍在缓冲 |
| 保存/加载 CSV | 全量保存时间戳+三轴数据，支持回放 |
| 滑动平均 | 可调窗口 1~100 |
| 指数平滑 (EMA) | 可调系数 α 0.01~1.0 |
| 统计面板 | 当前值、均值、峰峰值、RMS |
| 状态栏 | 连接状态、实时频率、累计采样数 |
| 明暗主题 | 切换暗色/亮色主题 |

**依赖**: `python3-pyqt5 python3-pyqtgraph python3-numpy`

## 机械臂订阅示例

接收 `/adxl355/accel`，检测振动幅值 > 阈值时触发运动事件。

```bash
# Python
python3 robot_arm_example/py_subscriber/arm_accel_sub.py

# C++ (需先编译)
cd robot_arm_example/cpp_subscriber
mkdir -p build && cd build
cmake .. && make
./arm_accel_sub
```

> 阈值默认为 0.5g，重力加速度 ~1g 会一直触发。实际使用时请改为 >1.1g，
> 或在 `_accel_callback` 中减去重力分量。

## 配置参考

### ESP32 (`config/wifi_config.h`)

```cpp
#define WIFI_SSID "YourHotspot"
#define WIFI_PASSWORD "YourPassword"
#define MICRO_ROS_AGENT_IP "172.20.10.7"  // 虚拟机 IP
#define MICRO_ROS_AGENT_PORT 8888
#define PUBLISH_RATE_HZ 500
```

### DDS 配置

| 参数 | 值 | 说明 |
|------|-----|------|
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | **必须用 Fast-DDS**，micro_ros_agent 不支持 Cyclone |
| `ROS_DOMAIN_ID` | `0` | micro-ROS 固件硬编码 domain 0 |
| Agent 端口 | `8888` | UDP，需与 ESP32 固件一致 |

## 文件结构

```
ADXL355/
├── platformio.ini              # PlatformIO 项目配置
├── config/
│   ├── wifi_config.h.example   # 配置模板（提交到 git）
│   └── wifi_config.h           # 真实配置（gitignore，需自行创建）
├── src/
│   ├── main.cpp                # 主入口 (WiFi + FreeRTOS 任务)
│   ├── adxl355_sensor.cpp/h    # ADXL355 SPI 驱动 + 中断配置
│   └── microros_node.cpp/h     # micro-ROS 节点 + 500Hz 发布者
├── ubuntu_vm/
│   ├── start_all.sh            # ★ 一键启动脚本
│   ├── launch_agent.sh         # 单独启动 Agent
│   ├── echo_accel.sh           # ros2 topic echo
│   ├── setup_microros_agent.sh # Agent 编译安装
│   └── ufw_firewall_setup.sh   # 防火墙配置
├── adxl355_viz/                # ROS2 可视化包 (PyQt5)
├── robot_arm_example/          # 机械臂订阅示例 (Python/C++)
│   ├── py_subscriber/
│   └── cpp_subscriber/
└── README.md
```

## 故障排查

| 问题 | 检查 |
|------|------|
| ESP32 连不上 WiFi | 热点名称/密码是否正确 |
| Agent 收不到数据 | `ping` ESP32 IP；检查虚拟机是否桥接到同一热点 |
| `ros2 topic list` 无 `/adxl355/accel` | 确认 `ROS_DOMAIN_ID=0`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` |
| Agent 启动失败 | 端口占用: `ss -uln | grep 8888` |
| 可视化无法启动 | 确认安装 `python3-pyqt5 python3-pyqtgraph` |
| 数据全是 0 | 检查 DRDY 引脚连接，确认固件含中断映射修复 |
| 发布频率低于 500Hz | WiFi 信号质量；micro-ROS over WiFi 实际吞吐约 280Hz |
