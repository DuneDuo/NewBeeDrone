"""
模拟 GCS/服务器 — 双向链路测试（飞行指令）

用法：
    python mock_server.py
"""

import socket
import time
import threading
from pymavlink.dialects.v20 import ardupilotmega as mavlink

HOST = "0.0.0.0"
PORT = 57600
SYS_ID = 254
COMP_ID = 190
INTERVAL = 1.0

mav = mavlink.MAVLink(None, srcSystem=SYS_ID, srcComponent=COMP_ID)

server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((HOST, PORT))
server_sock.listen(1)

print(f"模拟服务器已启动")
print(f"  地址: {HOST}:{PORT}（等待Pi连接）")
print(f"  身份: sys={SYS_ID} comp={COMP_ID}")
print()

client_sock, addr = server_sock.accept()
print(f"Pi 已连接: {addr}")
print()

# 心跳线程
def send_heartbeats():
    while True:
        msg = mav.heartbeat_encode(
            mavlink.MAV_TYPE_GCS,
            mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0,
        )
        try:
            client_sock.send(msg.pack(mav))
        except Exception:
            break
        time.sleep(INTERVAL)

threading.Thread(target=send_heartbeats, daemon=True).start()

# 共享位置（收包线程更新，测试线程读取）
pos = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
pos_ready = threading.Event()

# 测试指令线程
def test_commands():
    time.sleep(3)
    print("=== 等待位置信息 ===")
    if not pos_ready.wait(timeout=10):
        print("[错误] 超时未收到位置，放弃测试")
        return

    print(f"[定位] 当前位置: lat={pos['lat']:.6f} lon={pos['lon']:.6f}")
    print("=== 开始飞行测试 ===\n")

    # 1. 切 GUIDED 模式
    msg = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,       # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        4,       # GUIDED
        0, 0, 0, 0, 0,
    )
    client_sock.send(msg.pack(mav))
    print("[测试] 1/5 切 GUIDED 模式")
    time.sleep(3)

    # 2. Arm
    msg = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,       # arm
        0,       # force=0
        0, 0, 0, 0, 0,
    )
    client_sock.send(msg.pack(mav))
    print("[测试] 2/5 Arm")
    time.sleep(3)

    # 3. Takeoff 10m
    msg = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0,       # pitch
        0,       # empty
        0,       # empty
        0,       # yaw
        0, 0,    # lat, lon (unused)
        10,      # altitude 10m
    )
    client_sock.send(msg.pack(mav))
    print("[测试] 3/5 Takeoff → 10m")
    time.sleep(12)

    # 4. 向南 50m（纬度减 0.00045 度 ≈ 50m）
    target_lat = int((pos["lat"] - 0.00045) * 1e7)
    target_lon = int(pos["lon"] * 1e7)
    msg = mav.set_position_target_global_int_encode(
        0,                      # time_boot_ms
        1, 1,                   # target_system, target_component
        mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,  # 相对高度
        0b110111111000,         # type_mask: 只设 pos
        target_lat, target_lon,
        10,                     # altitude 10m (保持)
        0, 0, 0,               # vx, vy, vz
        0, 0, 0,               # afx, afy, afz
        0, 0,                   # yaw, yaw_rate
    )
    client_sock.send(msg.pack(mav))
    print(f"[测试] 4/5 向南 50m → lat={target_lat/1e7:.6f}")
    print("        (等待 15 秒到达...)")
    time.sleep(15)

    # 5. Land
    msg = mav.command_long_encode(
        1, 1,
        mavlink.MAV_CMD_NAV_LAND,
        0,
        0,        # abort=0
        0,        # precision landing mode
        0, 0, 0, 0, 0,
    )
    client_sock.send(msg.pack(mav))
    print("[测试] 5/5 Land")

    print("=== 飞行测试指令发送完毕 ===\n")

threading.Thread(target=test_commands, daemon=True).start()

# 收包循环
while True:
    try:
        data = client_sock.recv(4096)
        if not data:
            print("Pi 断开连接")
            break
        for msg in mav.parse_buffer(data):
            t = msg.get_type()
            # 更新位置
            if t == 'GLOBAL_POSITION_INT':
                pos["lat"] = msg.lat / 1e7
                pos["lon"] = msg.lon / 1e7
                pos["alt"] = msg.relative_alt / 1000.0
                pos_ready.set()
            # 打印关键反馈
            elif t == 'COMMAND_ACK':
                text = {
                    0: "MAV_RESULT_ACCEPTED",
                    1: "MAV_RESULT_TEMPORARILY_REJECTED",
                    2: "MAV_RESULT_DENIED",
                    3: "MAV_RESULT_UNSUPPORTED",
                    4: "MAV_RESULT_FAILED",
                }.get(msg.result, f"UNKNOWN({msg.result})")
                print(f"<<< COMMAND_ACK: cmd={msg.command}, result={text}")
            elif t == 'STATUSTEXT':
                print(f"[飞控] {msg.text}")
            elif t == 'HEARTBEAT':
                pass  # 心跳不打印
    except Exception as e:
        print(f"错误: {e}")
        break
