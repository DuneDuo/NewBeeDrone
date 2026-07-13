"""Server entry point — mavlink(包1) + mission(包2) + web(包3) 同一进程"""
import sys, os, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mavlink.drone import Drone


def main():
    # 包1：后台 daemon 线程，TCP 监听 MAVLink
    threading.Thread(target=Drone.serve, daemon=True).start()

    # 包2 + 包3 待写：
    # from web.api import app
    # app.run(host="0.0.0.0", port=5000)

    # 视频推流（独立进程，一行命令）
    # import subprocess
    # subprocess.Popen(["mediamtx"], cwd="mediamtx/")

    # 暂代：主线程阻塞，等 Ctrl+C
    print("Server running. Press Ctrl+C to stop.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down.")


if __name__ == "__main__":
    main()
