# ESP32 + ADXL355 micro-ROS 加速度采集与可视化系统

## 项目概述

使用 ESP32 驱动 ADXL355 加速度传感器，通过手机热点连接至局域网，将 ESP32 作为完整的 micro-ROS 节点，向同一网络下的 Ubuntu 虚拟机发布传感器数据。虚拟机内运行 ROS2 Humble、micro-ROS Agent 及 Python 可视化程序，实现**实时波形显示、500Hz 全量数据保存、历史回放与数字平滑处理**。

## 系统架构

```
ESP32 (micro-ROS)                  Ubuntu VM (ROS2 Humble)
┌─────────────────┐   UDP:8888   ┌──────────────────────────┐
│ ADXL355 @500Hz   │─────────────>│  micro_ros_agent         │
│ WiFi STA 模式    │              │    ↓                     │
│ 发布 /adxl355/accel│            │  ROS2 Topic (500Hz)      │
│ (geometry_msgs/  │              │    ↓           ↓         │
│  Accel)          │              │  viz_node  arm_sub      │
└─────────────────┘              │  (PyQt5)   (C++/Python) │
                                 │    ↓                     │
                                 │  Windows 显示 (VNC/ssh)  │
                                 └──────────────────────────┘

网络: 手机热点 (192.168.x.x)，ESP32 与宿主机均连接同一热点
虚拟机: Ubuntu 22.04 + ROS2 Humble，桥接网络模式
```

## 硬件需求

| 组件 | 说明 |
|------|------|
| ESP32 DevKit | 开发板（推荐 ESP32-WROOM-32） |
| ADXL355 模块 | SPI 接口加速度传感器 |
| 连接线 | 杜邦线 × 6（VCC/GND/CS/SCK/MOSI/MISO+DRDY） |

### 接线

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

### 1. ESP32 固件烧录

**前置条件**: 安装 [PlatformIO IDE](https://platformio.org/install) (VS Code 插件)

```bash
# 1. 修改 WiFi 配置
# 编辑 config/wifi_config.h，设置:
#   - WIFI_SSID / WIFI_PASSWORD (手机热点)
#   - MICRO_ROS_AGENT_IP (Ubuntu 虚拟机 IP)

# 2. 编译 & 烧录
pio run --target upload

# 3. 查看串口日志
pio device monitor
```

**启动后状态指示**:
- LED 闪烁: 正在连接 WiFi
- LED 熄灭: 已连接 Agent，正常工作
- LED 快闪: Agent 断线，自动重连中

### 2. Ubuntu 虚拟机配置

```bash
# 安装 ROS2 Humble (如未安装)
# 参考: https://docs.ros.org/en/humble/Installation.html

# 进入脚本目录
cd ubuntu_vm
chmod +x *.sh

# 安装 micro-ROS Agent
./setup_microros_agent.sh

# 配置防火墙
./ufw_firewall_setup.sh

# 启动 Agent
./launch_agent.sh 8888 udp4
```

**虚拟机网络要求**: 桥接模式，获得与宿主机同网段 IP。

### 3. 启动可视化程序

```bash
# 编译 ROS2 包
cd ~/ros2_ws
colcon build --packages-select adxl355_viz
source install/setup.bash

# 设置 ROS Domain ID (与 ESP32 端一致)
export ROS_DOMAIN_ID=42

# 启动
ros2 launch adxl355_viz adxl355_viz_launch.py
```

**Windows 端显示**:
- **VNC (推荐)**: Ubuntu 安装 `vnc4server`，Windows 用 VNC Viewer 连接
- **ssh -X**: Windows 安装 VcXsrv，`ssh -X user@vm-ip`

### 4. 验证

```bash
# 查看话题
ros2 topic list
# 应看到 /adxl355/accel

# 查看数据
ros2 topic echo /adxl355/accel --once

# 查看频率
ros2 topic hz /adxl355/accel
# 应接近 500 Hz
```

## 可视化程序功能

| 功能 | 说明 |
|------|------|
| 3 轴实时波形 | X(红)/Y(绿)/Z(蓝)，时间窗口可调 (1~60s) |
| 开始/停止采集 | 暂停/恢复实时显示，数据仍从 ROS2 接收 |
| 保存 CSV | 500Hz 全量保存，格式: timestamp, accel_x, accel_y, accel_z |
| 加载历史 CSV | 加载并回放历史数据，自动扩展到 60s 时间窗 |
| 滑动平均 | 可调窗口大小 (1~100) |
| 指数平滑 | 可调平滑系数 α (0.01~1.0) |
| 清除图表 | 清空缓冲区与显示 |
| 统计面板 | 各轴当前值、均值、峰峰值、RMS |
| 状态栏 | ROS 连接状态、实时频率、累计采样数 |

## 配置参数

### ESP32 端 (`config/wifi_config.h`)

```cpp
#define WIFI_SSID "YourHotspot"          // 手机热点 SSID
#define WIFI_PASSWORD "YourPassword"     // 热点密码
#define MICRO_ROS_AGENT_IP "192.168.1.100"  // 虚拟机 IP
#define MICRO_ROS_AGENT_PORT 8888        // Agent 端口
#define ROS_DOMAIN_ID 42                 // ROS Domain ID
#define PUBLISH_RATE_HZ 500              // 发布频率
```

### Agent 端

```bash
./launch_agent.sh [port] [transport]
# 示例: ./launch_agent.sh 8888 udp4
```

### 可视化端 (launch 参数)

```bash
ros2 launch adxl355_viz adxl355_viz_launch.py \
    history_seconds:=60.0 \
    smoothing_window:=5 \
    smoothing_alpha:=0.3
```

## 机械臂订阅

### Python 示例

```bash
python3 robot_arm_example/py_subscriber/arm_accel_sub.py
```

### C++ 示例

```bash
cd robot_arm_example/cpp_subscriber
colcon build
source install/setup.bash
ros2 run arm_accel_subscriber arm_accel_sub
```

机械臂节点订阅 `/adxl355/accel` (500Hz)，计算加速度幅值，超过阈值 (0.5g) 触发动作事件。替换 `_on_motion_start()` / `_on_motion_end()` 中的逻辑即可对接具体机械臂 SDK。

## 故障排查

| 问题 | 检查 |
|------|------|
| ESP32 连不上 WiFi | 热点名称/密码是否正确，信号强度是否足够 |
| Agent 收不到数据 | 1. 虚拟机 `ping` ESP32 IP 2. 防火墙 `sudo ufw status` 确认 UDP 8888 放行 3. WiFi 是否同一热点 |
| 桥接网络无 IP | VMware: 编辑→虚拟网络编辑器→桥接模式选择正确 WiFi 网卡 |
| `ros2 topic list` 无话题 | `export ROS_DOMAIN_ID=42`，确认与 ESP32 端一致 |
| 可视化程序启动失败 | 确认安装了 `python3-pyqt5 python3-pyqtgraph python3-numpy` |
| GUI 显示延迟高 | ssh -X 带宽不足，改用 VNC |
| 发布频率低于 500Hz | ADXL355 库版本，检查 ODR 配置；WiFi 信号质量 |

## 文件结构

```
ADXL355/
├── platformio.ini          # PlatformIO 项目配置
├── config/
│   └── wifi_config.h       # WiFi/ROS/传感器配置
├── src/
│   ├── main.cpp            # 主入口
│   ├── adxl355_sensor.*    # ADXL355 传感器驱动
│   └── microros_node.*     # micro-ROS 节点/发布者
├── ubuntu_vm/              # 虚拟机部署脚本
├── adxl355_viz/            # ROS2 Python 可视化包
├── robot_arm_example/      # 机械臂订阅示例
└── README.md               # 本文档
```

## 许可证

Apache-2.0
