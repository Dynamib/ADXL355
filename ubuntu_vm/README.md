# Ubuntu 虚拟机配置指南

## 1. 虚拟机网络配置（桥接模式）

### VMware Workstation
1. 虚拟机设置 → 网络适配器 → 选择 **桥接模式**
2. 桥接到 → 选择宿主机的 **WiFi 网卡**（连接手机热点的那个）
3. 启动虚拟机，确认获得与宿主机同网段 IP：
   ```bash
   ip addr show
   ```
   应看到 `192.168.x.x` 的地址。

### VirtualBox
1. 虚拟机设置 → 网络 → 网卡 1 → 连接方式: **桥接网卡**
2. 界面名称 → 选择宿主机的 **WiFi 网卡**
3. 启动虚拟机，确认 IP 地址。

## 2. 安装 ROS2 Humble

参考官方文档: https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html

```bash
# 安装后 source 环境
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## 3. 安装 micro-ROS Agent

```bash
cd /path/to/ADXL355/ubuntu_vm
chmod +x *.sh
./setup_microros_agent.sh
```

## 4. 配置防火墙

```bash
./ufw_firewall_setup.sh
```

## 5. 启动 Agent

```bash
./launch_agent.sh 8888 udp4
```

## 6. 验证连通性

在 ESP32 上电并连接热点后：

```bash
# 查看话题是否收到数据
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
ros2 topic echo /adxl355/accel
```

## 7. 环境变量

在 `/etc/environment` 或 `~/.bashrc` 中设置：

```bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

## 8. 故障排查

| 问题 | 检查项 |
|------|--------|
| Agent 启动失败 | 端口是否被占用: `sudo lsof -i :8888` |
| 收不到 ESP32 数据 | 1. 虚拟机 ping ESP32 IP 2. 防火墙是否放行 UDP 8888 3. WiFi 是否同一热点 |
| 桥接网络无 IP | VMware: 编辑→虚拟网络编辑器→桥接模式选择正确网卡 |
| ROS2 话题无数据 | `ros2 topic list` 查看话题是否出现，确认 ROS_DOMAIN_ID 一致 |
