#!/bin/bash
# ============================================================
# 防火墙配置 — 放行 micro-ROS Agent UDP 端口
# ============================================================
set -e

AGENT_PORT=${1:-8888}

echo "正在配置防火墙，放行 UDP/TCP 端口 ${AGENT_PORT}..."

sudo ufw allow ${AGENT_PORT}/udp comment 'micro-ROS Agent UDP'
sudo ufw allow ${AGENT_PORT}/tcp comment 'micro-ROS Agent TCP (备用)'

echo ""
echo "当前防火墙状态:"
sudo ufw status verbose
