# Server 启动入口
import sys
import threading
from pathlib import Path

# 保证从任意目录运行都能找到 config / core / mavlink / command 等顶层模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.drone import Drone
import command_entry

if __name__ == "__main__":
    # serve 阻塞监听，丢后台线程；主线程跑交互式指令控制台
    threading.Thread(target=Drone.serve, daemon=True).start()
    command_entry.run_console()
