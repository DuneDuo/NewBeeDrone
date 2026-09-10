"""端到端测试：用 mock 飞控（真实 pymavlink + 真实 TCP）测试 param 读写逻辑"""
import socket
import time
import threading

import config
from core.drone import Drone
from pymavlink.dialects.v20.common import (
    MAVLink,
    MAV_TYPE_QUADROTOR,
    MAV_AUTOPILOT_ARDUPILOTMEGA,
    MAV_STATE_ACTIVE,
)

HOST = "127.0.0.1"
PASS, FAIL = 0, 0


def report(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {name}  {detail}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def start_server():
    threading.Thread(target=Drone.serve, daemon=True).start()
    time.sleep(0.5)  # 等监听就绪


class MockFC:
    """模拟一台飞控：有参数表，响应 PARAM_REQUEST_READ / PARAM_SET"""

    def __init__(self):
        self.mav = MAVLink(None, srcSystem=1, srcComponent=1)
        self.params = {
            "RC1_MAX": 2000.0,
            "RC1_MIN": 1000.0,
            "ATC_RAT_PIT_P": 0.08,
        }
        self.sock = None
        self.running = False

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, config.port))
        self.sock.settimeout(3)
        self.running = True
        self.send_heartbeat()
        threading.Thread(target=self.responder, daemon=True).start()
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    def _send(self, m):
        self.sock.send(m.pack(self.mav))

    def send_heartbeat(self):
        self._send(self.mav.heartbeat_encode(
            MAV_TYPE_QUADROTOR, MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, MAV_STATE_ACTIVE))

    def heartbeat_loop(self):
        while self.running:
            time.sleep(1)
            try:
                self.send_heartbeat()
            except OSError:
                break

    def send_param_value(self, pid, value):
        keys = list(self.params.keys())
        idx = keys.index(pid) if pid in keys else 0
        self._send(self.mav.param_value_encode(
            pid.encode(), value, 9, len(self.params), idx))

    def responder(self):
        """模拟飞控对参数请求的响应"""
        while self.running:
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            try:
                msgs = self.mav.parse_buffer(data)
            except Exception:
                continue
            for msg in msgs or []:
                t = msg.get_type()
                if t == "PARAM_REQUEST_READ":
                    pid = msg.param_id
                    if pid in self.params:
                        self.send_param_value(pid, self.params[pid])
                elif t == "PARAM_SET":
                    pid = msg.param_id
                    self.params[pid] = msg.param_value  # 存下 float32 精度的新值
                    self.send_param_value(pid, self.params[pid])  # ACK 回显


def wait_drone(sys_id=1, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        d = Drone.registry.get(sys_id)
        if d is not None:
            return d
        time.sleep(0.1)
    return None


def main():
    print("=" * 60)
    print("param 端到端测试")
    print("=" * 60)

    start_server()
    fc = MockFC()
    fc.connect()

    drone = wait_drone(1)
    report("HEARTBEAT 注册", drone is not None, f"sys_id=1 -> {drone is not None}")
    if drone is None:
        print("  无人机未注册，终止")
        return

    # 1. 读整数参数
    v = drone.param_read("RC1_MAX")
    report("读整数 RC1_MAX", v == 2000.0, f"返回 {v!r}，期望 2000.0")

    # 2. 写整数参数
    r = drone.param_set("RC1_MAX", 1800)
    report("写整数 RC1_MAX=1800", r is True and fc.params["RC1_MAX"] == 1800.0,
           f"返回 {r}，mock飞控表={fc.params['RC1_MAX']!r}")

    # 3. 写浮点参数（验证 _eq 相对容差）
    r = drone.param_set("ATC_RAT_PIT_P", 0.08)
    stored = fc.params["ATC_RAT_PIT_P"]
    report("写浮点 ATC_RAT_PIT_P=0.08", r is True,
           f"返回 {r}，mock飞控表={stored!r}（float32 往返后）")

    # 4. 读不存在的参数（mock 不回 → 超时）
    v = drone.param_read("NOT_EXIST", timeout=1.0)
    report("读不存在参数超时", v is None, f"返回 {v!r}，期望 None")

    # 5. 写一个会让 _eq 判等的浮点（0.08 的 float32 往返值作为目标）
    r = drone.param_set("ATC_RAT_PIT_P", 0.079999998)
    report("写浮点 0.079999998（float32 可表示）", r is True, f"返回 {r}")

    fc.running = False
    try:
        fc.sock.close()
    except Exception:
        pass

    print("=" * 60)
    print(f"结果：{PASS} 通过 / {FAIL} 失败")
    print("=" * 60)


if __name__ == "__main__":
    main()
