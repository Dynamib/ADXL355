import socket
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import numpy as np

# ================= 配置参数 =================
ESP_IP = '192.168.4.1'
ESP_PORT = 8080

# 实时窗口配置
REALTIME_WINDOW = 500   # 实时图只显示最近500个点
REFRESH_INTERVAL = 30   # 刷新间隔(ms)，30ms约等于33fps

# 全局图配置
DOWNSAMPLE_RATIO = 10   # 全局图降采样比例（每10个点画1个，防止卡死）

# ================= 数据容器 =================
# 实时数据 (定长队列)
rt_time = deque(maxlen=REALTIME_WINDOW)
rt_x = deque(maxlen=REALTIME_WINDOW)
rt_y = deque(maxlen=REALTIME_WINDOW)
rt_z = deque(maxlen=REALTIME_WINDOW)

# 全局历史数据 (列表)
all_time = []
all_x = []
all_y = []
all_z = []

# 线程控制
is_running = True
data_lock = threading.Lock() # 数据锁，防止绘图和接收冲突

def data_receiver_thread():
    """后台接收数据线程"""
    global is_running
    print(f"正在连接到 ESP32 ({ESP_IP}:{ESP_PORT})...")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    
    try:
        client.connect((ESP_IP, ESP_PORT))
        print("连接成功！开始接收数据...")
        socket_file = client.makefile('r', encoding='utf-8', errors='ignore')
        
        start_time_offset = None # 用于将时间戳归零
        
        while is_running:
            try:
                line = socket_file.readline()
                if not line: break
                
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    # 解析数据
                    raw_time = float(parts[0])
                    if start_time_offset is None:
                        start_time_offset = raw_time
                    
                    # 时间转为秒，从0开始
                    t_val = (raw_time - start_time_offset) / 1000.0
                    x_val = float(parts[1])
                    y_val = float(parts[2])
                    z_val = float(parts[3])
                    
                    # 加锁写入数据
                    with data_lock:
                        # 写入实时队列
                        rt_time.append(t_val)
                        rt_x.append(x_val)
                        rt_y.append(y_val)
                        rt_z.append(z_val)
                        
                        # 写入全局列表
                        all_time.append(t_val)
                        all_x.append(x_val)
                        all_y.append(y_val)
                        all_z.append(z_val)
                        
            except ValueError: continue
            except socket.timeout: continue
            except Exception as e: 
                print(f"数据错误: {e}")
                break
                
    except Exception as e:
        print(f"连接失败: {e}")
    finally:
        client.close()
        is_running = False

# ================= 绘图初始化 =================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
plt.subplots_adjust(hspace=0.3)

# 设置子图1：实时数据
ax1.set_title(f'Real-time Window (Last {REALTIME_WINDOW} points)')
ax1.set_ylabel('Accel (g)')
ax1.grid(True)
line1_x, = ax1.plot([], [], 'r-', lw=1, label='X')
line1_y, = ax1.plot([], [], 'g-', lw=1, label='Y')
line1_z, = ax1.plot([], [], 'b-', lw=1, label='Z')
ax1.legend(loc='upper right', fontsize='small')

# 设置子图2：全局历史数据
ax2.set_title('Full History (Global Trend)')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Accel (g)')
ax2.grid(True)
line2_x, = ax2.plot([], [], 'r-', lw=0.5, alpha=0.7)
line2_y, = ax2.plot([], [], 'g-', lw=0.5, alpha=0.7)
line2_z, = ax2.plot([], [], 'b-', lw=0.5, alpha=0.7)

def init():
    """动画初始化函数"""
    # 设置初始范围，避免第一次绘图报错
    ax1.set_xlim(0, 10)
    ax1.set_ylim(-2, 2)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(-2, 2)
    return line1_x, line1_y, line1_z, line2_x, line2_y, line2_z

def update(frame):
    """动画更新函数"""
    with data_lock:
        if not rt_time: return line1_x, line1_y, line1_z, line2_x, line2_y, line2_z
        
        # --- 更新子图1 (实时) ---
        line1_x.set_data(rt_time, rt_x)
        line1_y.set_data(rt_time, rt_y)
        line1_z.set_data(rt_time, rt_z)
        
        # 动态调整子图1坐标轴
        if len(rt_time) > 1:
            ax1.set_xlim(min(rt_time), max(rt_time) + 0.1)
            # 简单的自动Y轴缩放
            current_min = min(min(rt_x), min(rt_y), min(rt_z))
            current_max = max(max(rt_x), max(rt_y), max(rt_z))
            margin = (current_max - current_min) * 0.1
            ax1.set_ylim(current_min - margin, current_max + margin)

        # --- 更新子图2 (全局) ---
        # 降采样优化：每 N 个点取一个，避免渲染百万个点导致卡死
        if len(all_time) > 0:
            # 使用切片 [::STEP] 进行降采样
            global_t = all_time[::DOWNSAMPLE_RATIO]
            global_x = all_x[::DOWNSAMPLE_RATIO]
            global_y = all_y[::DOWNSAMPLE_RATIO]
            global_z = all_z[::DOWNSAMPLE_RATIO]
            
            line2_x.set_data(global_t, global_x)
            line2_y.set_data(global_t, global_y)
            line2_z.set_data(global_t, global_z)
            
            # 动态调整子图2坐标轴
            ax2.set_xlim(0, max(all_time) + 1)
            ax2.set_ylim(ax1.get_ylim()) # 跟随上面的Y轴范围

    return line1_x, line1_y, line1_z, line2_x, line2_y, line2_z

# ================= 主程序 =================
if __name__ == '__main__':
    # 启动数据接收
    recv_thread = threading.Thread(target=data_receiver_thread, daemon=True)
    recv_thread.start()
    
    print("窗口已打开。上图为实时细节，下图为全局历史。")
    print("注意：如果运行时间过长（超过30分钟），全局图可能会因为数据量巨大而变慢。")
    
    # 启动动画
    # blit=True 开启高速渲染模式（只重绘变化部分）
    ani = FuncAnimation(fig, update, init_func=init, interval=REFRESH_INTERVAL, blit=True, cache_frame_data=False)
    
    plt.show()
    is_running = False