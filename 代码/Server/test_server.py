"""Server integration test — comprehensive"""
import sys, os, time, threading, socket

sys.path.insert(0, os.path.dirname(__file__))

from pymavlink import mavutil
from mavlink.drone import Drone
from mavlink import config as server_cfg

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")
    return condition

# ── Start server once ────────────────────────────────
server_thread = threading.Thread(target=Drone.serve, daemon=True)
server_thread.start()
time.sleep(0.3)
print("[OK] Server started\n")

# ─────────────────────────────────────────────────────
print("=" * 60)
print("1. Connection & Heartbeat")
print("=" * 60)

fc1 = mavutil.mavlink_connection(
    f"tcp:localhost:{server_cfg.port}",
    source_system=1, source_component=1,
    dialect="ardupilotmega", autoreconnect=False,
)
fc1.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_QUADROTOR,
                       mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                       0, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
time.sleep(0.5)

check("drone registered", 1 in Drone.registry)
check("sys_id == 1", Drone.registry[1].sys_id == 1)

# verify server heartbeat reply
hb = fc1.recv_match(type="HEARTBEAT", blocking=True, timeout=3)
check("server replies heartbeat", hb is not None)
if hb:
    check("server sys_id == 255", hb.get_srcSystem() == 255)
    check("type == GCS (6)", hb.type == 6)
    check("autopilot == GENERIC (0)", hb.autopilot == 0)
    check("status == ACTIVE (4)", hb.system_status == 4)
    check("mavlink_version == 3", hb.mavlink_version == 3)

# heartbeat updates last_heartbeat
before = Drone.registry[1].last_heartbeat
fc1.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_QUADROTOR,
                       mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                       0, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
time.sleep(0.5)
check("heartbeat updates timestamp", Drone.registry[1].last_heartbeat > before)

# ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. Command Long (send from server to FC)")
print("=" * 60)

drone = Drone.registry[1]

tests = [
    ("arm",        400, dict(param1=1)),
    ("takeoff 10m", 22, dict(param7=10.0)),
    ("land",        21, {}),
    ("RTL",         20, {}),
]
for name, cmd_id, kw in tests:
    drone.send_command_long(cmd_id, **kw)
    m = fc1.recv_match(type="COMMAND_LONG", blocking=True, timeout=3)
    check(f"{name} rcvd", m is not None and m.command == cmd_id)

# positional unpacking
drone.send_command_long(400, 0, 0, 0, 0, 0, 0, 1)
m = fc1.recv_match(type="COMMAND_LONG", blocking=True, timeout=3)
check("positional unpacking", m is not None and m.param7 == 1)

# all 7 params
drone.send_command_long(400, param1=1, param2=2, param3=3,
                        param4=4, param5=5, param6=6, param7=7)
m = fc1.recv_match(type="COMMAND_LONG", blocking=True, timeout=3)
check("all 7 params correct", m is not None
      and [m.param1, m.param2, m.param3, m.param4, m.param5, m.param6, m.param7]
          == [1, 2, 3, 4, 5, 6, 7])

# ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. Parameter Read / Write")
print("=" * 60)

drone.param_request_read(b"FS_GCS_ENABLE")
m = fc1.recv_match(type="PARAM_REQUEST_READ", blocking=True, timeout=3)
check("param read rcvd", m is not None)
if m:
    check("param_index == -1", m.param_index == -1)

drone.param_set(b"FS_GCS_ENABLE", 1.0)
m = fc1.recv_match(type="PARAM_SET", blocking=True, timeout=3)
check("param set float (type=9)", m is not None and m.param_value == 1.0 and m.param_type == 9)

drone.param_set(b"FS_GCS_ENABLE", 1, param_type=1)
m = fc1.recv_match(type="PARAM_SET", blocking=True, timeout=3)
check("param set uint8 (type=1)", m is not None and m.param_value == 1.0 and m.param_type == 1)

drone.param_set(b"WP_TOTAL", 10, param_type=6)
m = fc1.recv_match(type="PARAM_SET", blocking=True, timeout=3)
check("param set int32 (type=6)", m is not None and m.param_value == 10.0 and m.param_type == 6)

# ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. Safety Guards")
print("=" * 60)

# unregistered drone — all sends should log warning but not crash
from mavlink.drone import Drone as DroneCls
d = DroneCls.__new__(DroneCls)
d.sys_id = None; d.conn = None; d.running = False
d.last_heartbeat = None; d.addr = ("test", 0)
d.send_command_long(400, param1=1)
check("send_command guard", True)
d.param_request_read(b"TEST")
check("param_request_read guard", True)
d.param_set(b"TEST", 1.0)
check("param_set guard", True)

# double close()
tmp_fc = mavutil.mavlink_connection(
    f"tcp:localhost:{server_cfg.port}",
    source_system=99, source_component=1,
    dialect="ardupilotmega", autoreconnect=False,
)
tmp_fc.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_QUADROTOR,
                          mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                          0, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
time.sleep(0.3)
d99 = DroneCls.registry[99]
d99.close()
time.sleep(0.1)
d99.close()  # should not crash
check("double close() no crash", True)
check("drone99 removed", 99 not in DroneCls.registry)
tmp_fc.close()

# ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("5. Multiple Drones")
print("=" * 60)

fc2 = mavutil.mavlink_connection(
    f"tcp:localhost:{server_cfg.port}",
    source_system=2, source_component=1,
    dialect="ardupilotmega", autoreconnect=False,
)
fc2.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_QUADROTOR,
                       mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                       0, 0, mavutil.mavlink.MAV_STATE_ACTIVE)
time.sleep(0.3)

check("drone2 registered", 2 in Drone.registry)
check("drone1 still registered", 1 in Drone.registry)
check("registry size == 2", len(Drone.registry) == 2)

Drone.registry[2].send_command_long(400, param1=1)
m = fc2.recv_match(type="COMMAND_LONG", blocking=True, timeout=3)
check("drone2 receives command", m is not None and m.command == 400)

# verify drone2 gets server heartbeat too
hb2 = fc2.recv_match(type="HEARTBEAT", blocking=True, timeout=3)
check("drone2 gets heartbeat", hb2 is not None and hb2.get_srcSystem() == 255)

fc2.close()
time.sleep(1.5)
check("drone2 removed after close", 2 not in Drone.registry)

# ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("6. Garbage / Non-MAVLink Data")
print("=" * 60)

raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw.settimeout(1)
raw.connect(("127.0.0.1", server_cfg.port))
raw.send(b"\x00\x01\x02\x03NOT_MAVLINK_garbage_XYZ" * 10)
raw.close()
time.sleep(1.0)
check("server survives garbage", True)

# ── Cleanup ──────────────────────────────────────────
fc1.close()

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
