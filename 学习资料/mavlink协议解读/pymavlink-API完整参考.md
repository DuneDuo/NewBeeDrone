# pymavlink 完整 API 参考

> pymavlink 是 MAVLink 协议的 Python 实现，封装了帧解析、CRC 校验、消息字典、签名验证等全部底层细节。
>
> 安装：`pip install pymavlink`

---

## 目录

- [1. 核心概念](#1-核心概念)
- [2. 创建连接](#2-创建连接)
- [3. 接收消息](#3-接收消息)
- [4. 发送消息](#4-发送消息)
- [5. 消息对象操作](#5-消息对象操作)
- [6. 心跳与状态检测](#6-心跳与状态检测)
- [7. 连接信息与管理](#7-连接信息与管理)
- [8. 参数操作](#8-参数操作)
- [9. 航点操作](#9-航点操作)
- [10. 常用消息类型速查](#10-常用消息类型速查)
- [11. 实用代码片段](#11-实用代码片段)

---

## 1. 核心概念

### 1.1 mavutil 模块

整个库的入口，提供连接工厂函数和工具方法。

```python
from pymavlink import mavutil
```

### 1.2 连接字符串格式

pymavlink 通过一个字符串描述连接方式和参数，格式为 `方式:地址:端口`。

| 连接方式 | 字符串格式 | 说明 |
|----------|-----------|------|
| `udp` | `udp:127.0.0.1:14550` | 主动连接远端 UDP（连 SITL） |
| `udpin` | `udpin:0.0.0.0:14550` | 本地监听 UDP（收 SITL 数据） |
| `udpout` | `udpout:192.168.1.100:14550` | 纯输出 UDP（只发不收） |
| `tcp` | `tcp:127.0.0.1:5760` | TCP 连接 |
| `serial` | `COM3` 或 `/dev/ttyUSB0` | 串口（Windows/Linux） |
| `serial:COM3:115200` | 同上，指定波特率 | 带参数 |

### 1.3 system_id 和 component_id

- **system_id**（1-255）：系统中唯一标识一个飞控/无人机
- **component_id**（0-255）：系统中唯一标识一个组件（飞控=1，相机=100 等）

地面站习惯于用 sysid=255, compid=190。

---

## 2. 创建连接

### 2.1 mavlink_connection()

```python
mavutil.mavlink_connection(
    device: str,                    # 连接字符串，如 'udp:127.0.0.1:14550'
    baud: int = 115200,            # 波特率（仅串口有效）
    source_system: int = 255,      # 自己的系统 ID
    source_component: int = 0,     # 自己的组件 ID
    dialect: str = 'ardupilotmega',# 消息方言集
    autoreconnect: bool = False,   # 断开后自动重连
    retries: int = 3,              # 超时重试次数
    source_component: int = 0,
) -> mavutil.mavudp 或 mavutil.mavserial
```

**返回值**：一个连接对象，具体类型取决于连接方式（UDP 返回 `mavudp`，串口返回 `mavserial`）。但使用上完全一样，都是同一个接口。

**示例**：

```python
# SITL 仿真
conn = mavutil.mavlink_connection('udp:127.0.0.1:14550')

# 监听 SITL（被动接收，更稳定）
conn = mavutil.mavlink_connection('udpin:0.0.0.0:14550')

# 串口直连飞控
conn = mavutil.mavlink_connection('COM3', baud=115200)

# Linux 串口
conn = mavutil.mavlink_connection('/dev/ttyUSB0', baud=921600)

# 带完整参数
conn = mavutil.mavlink_connection(
    'udpin:0.0.0.0:14551',
    source_system=255,
    source_component=190,
    autoreconnect=True,
)
```

### 2.2 两种 UDP 连接的区别

```python
# udp  — 主动向目标 IP:端口发起连接
conn = mavutil.mavlink_connection('udp:127.0.0.1:14550')
# 适用：你知道对方在哪，要连上去

# udpin — 本地 bind 一个端口，被动接收任何来源的数据
conn = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
# 适用：你不知道对方 IP，或者对方先发数据过来。SITL 首选这个
```

WSL 中 SITL 的 IP 可能变化，用 `udpin` 最稳，不管 SITL 走什么 IP 都能收到。

---

## 3. 接收消息

### 3.1 recv_match() — 条件接收（最常用）

```python
conn.recv_match(
    type: str = None,              # 消息类型名，如 'HEARTBEAT'、'ATTITUDE'
    blocking: bool = True,         # True=阻塞等消息，False=非阻塞立即返回
    timeout: float = None,         # 超时时间（秒），仅 blocking=True 有效
    condition: str = None,         # Python 表达式过滤，如 'GLOBAL_POSITION_INT.alt>10000'
    sys: int = None,               # 只收指定系统 ID 的消息
    comp: int = None,              # 只收指定组件 ID 的消息
) -> mavlink.MAVLink_message 或 None
```

**返回值**：
- 匹配到消息 → `MAVLink_message` 对象
- 没匹配到 / 超时 → `None`

**示例**：

```python
# 非阻塞，来啥收啥
msg = conn.recv_match(blocking=False)

# 阻塞等心跳
msg = conn.recv_match(type='HEARTBEAT', blocking=True, timeout=5.0)

# 只收高度超过 10m 的 GPS 数据
msg = conn.recv_match(
    type='GLOBAL_POSITION_INT',
    condition='GLOBAL_POSITION_INT.relative_alt>10000',
    blocking=True
)

# 只收系统 1 发来的消息
msg = conn.recv_match(sys=1, blocking=False)
```

### 3.2 recv_msg() — 无条件接收

```python
conn.recv_msg() -> mavlink.MAVLink_message 或 None
```

直接从缓冲区取**下一条**消息，不做任何过滤。相当于 `recv_match(blocking=False)` 的无条件版本。

```python
msg = conn.recv_msg()
# 拿到啥是啥：HEARTBEAT / ATTITUDE / BAD_DATA ...
```

### 3.3 recv_match() vs recv_msg() 对比

| | `recv_msg()` | `recv_match()` |
|--|:---:|:---:|
| 过滤 | ❌ 不做过滤 | ✅ type/condition/sys/comp 过滤 |
| 阻塞 | ❌ 非阻塞 | ✅ 可选阻塞 |
| 内部实现 | 取缓冲区下一条 | 循环 `recv_msg()`，丢弃不匹配的 |
| 丢数据 | 不丢 | 不匹配的消息**被丢弃** |
| 适用场景 | 全收全记（转发/日志） | 等特定消息（指令 ACK） |

**重要**：`recv_match` 不匹配的消息会被扔掉。如果你要全收全记，用 `recv_msg()` 或用 `recv_match(blocking=False)` 什么都不过滤。

### 3.4 recv_bytes() — 收原始字节

```python
conn.recv_bytes() -> bytes 或 None
```

返回原始 MAVLink 字节流，不解析。用于写 `.bin` 日志文件或调试。

```python
raw = conn.recv_bytes()
if raw:
    log_file.write(raw)  # 完整记录原始数据
```

**注意**：`recv_bytes()` 和 `recv_msg()/recv_match()` 共享底层缓冲区，**不能混用**——`recv_bytes` 拿走的字节 `recv_msg` 就拿不到了。

---

## 4. 发送消息

### 4.1 发送 MAVLink 指令（最常用）

pymavlink 为每种 MAVLink 消息类型动态生成了编码方法，命名规则为 `消息名_send()`。例如心跳是 `heartbeat_send()`，指令是 `command_long_send()`。

#### heartbeat_send() — 发送心跳

```python
conn.mav.heartbeat_send(
    type: int,              # 飞行器类型（MAV_TYPE）
    autopilot: int,        # 飞控类型（MAV_AUTOPILOT）
    base_mode: int,        # 基本模式
    custom_mode: int,      # 自定义模式（ArduPilot 用这个表示飞行模式）
    system_status: int,    # 系统状态（MAV_STATE）
)
```

```python
# 发送地面站心跳
conn.mav.heartbeat_send(
    mavutil.mavlink.MAV_TYPE_GCS,         # 地面站类型
    mavutil.mavlink.MAV_AUTOPILOT_INVALID, # 非飞控
    0, 0,                                 # 模式不适用
    mavutil.mavlink.MAV_STATE_ACTIVE       # 在线
)
```

#### command_long_send() — 发送长指令

```python
conn.mav.command_long_send(
    target_system: int,        # 目标系统 ID
    target_component: int,     # 目标组件 ID
    command: int,             # MAV_CMD 指令编号
    confirmation: int,        # 确认序号（0=首次发送）
    param1: float,            # 参数1-7，含义取决于具体指令
    param2: float,
    param3: float,
    param4: float,
    param5: float,
    param6: float,
    param7: float,
)
```

```python
# 解锁
conn.mav.command_long_send(
    1, 1,                               # sysid=1, compid=1（飞控）
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,                                   # 确认序号
    1, 0, 0, 0, 0, 0, 0                  # param1=1 表示解锁
)

# 起飞到 10 米
conn.mav.command_long_send(
    1, 1,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0,
    0, 0, 0, 0, 0, 0, 10                 # param7=10 米
)

# 切换到悬停模式（ArduPilot custom_mode）
# 悬停=custom_mode=4
conn.mav.command_long_send(
    1, 1,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0,
    1, 4, 0, 0, 0, 0, 0                  # param1=1(MAV_MODE_FLAG_CUSTOM_MODE), param2=4(LOITER)
)

# 返航
conn.mav.command_long_send(
    1, 1,
    mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
    0,
    0, 0, 0, 0, 0, 0, 0
)
```

#### command_int_send() — 发送带整数坐标的指令

与 `command_long` 类似，但支持整数坐标（经纬度×1e7）：

```python
conn.mav.command_int_send(
    target_system, target_component,
    frame,                # MAV_FRAME（坐标参考系）
    command,
    current, autocontinue,
    param1, param2, param3, param4,
    x, y, z               # 经纬度×1e7, 高度
)
```

```python
# 飞往指定 GPS 坐标
conn.mav.command_int_send(
    1, 1,
    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
    0, 0,
    0, 0, 0, 0,            # 保持默认
    int(-35.363262 * 1e7), # 纬度 × 1e7
    int(149.165237 * 1e7), # 经度 × 1e7
    50.0                    # 高度 50 米
)
```

### 4.2 发送其他消息

pymavlink 为每个 MAVLink 消息类型自动生成了 `消息名_send()` 方法。例如：

```python
# 发送舵机控制指令
conn.mav.command_do_set_servo_send(1, 1, 5, 1500)

# 请求参数列表
conn.mav.param_request_list_send(1, 1)

# 发送 GPS 注入数据
conn.mav.gps_inject_data_send(1, 1, 0, 100, b'\x00\x01\x02')
```

### 4.3 通用发送方法

```python
# 创建一个消息对象
msg = conn.mav.heartbeat_encode(
    mavutil.mavlink.MAV_TYPE_GCS,
    mavutil.mavlink.MAV_AUTOPILOT_INVALID,
    0, 0,
    mavutil.mavlink.MAV_STATE_ACTIVE
)

# 打包为字节
buf = msg.pack(conn.mav)

# 发送
conn.write(buf)
```

---

## 5. 消息对象操作

### 5.1 获取消息类型名

```python
msg_type = msg.get_type()
# 返回字符串：'HEARTBEAT', 'ATTITUDE', 'GLOBAL_POSITION_INT' 等
```

### 5.2 获取消息 ID

```python
msg_id = msg.get_msgId()
# 返回整数：0=HEARTBEAT, 30=ATTITUDE, 33=GLOBAL_POSITION_INT
```

### 5.3 获取发送方信息

```python
sys_id = msg.get_srcSystem()      # 来源系统 ID
comp_id = msg.get_srcComponent()  # 来源组件 ID
```

### 5.4 转为字典（完整字段）

```python
d = msg.to_dict()
# 返回 dict，包含所有字段，如：
# {'mavpackettype': 'HEARTBEAT', 'type': 3, 'autopilot': 3, 'system_status': 3, ...}
```

### 5.5 转为 JSON

```python
json_str = msg.to_json()
```

### 5.6 直接访问字段

```python
# HEARTBEAT 消息
print(msg.type)               # 飞行器类型
print(msg.autopilot)          # 飞控类型
print(msg.system_status)      # 系统状态
print(msg.base_mode)          # 基本模式
print(msg.custom_mode)        # 自定义模式

# ATTITUDE 消息
print(msg.roll)               # 横滚角（弧度）
print(msg.pitch)              # 俯仰角（弧度）
print(msg.yaw)                # 偏航角（弧度）
print(msg.rollspeed)          # 横滚角速度（rad/s）
print(msg.pitchspeed)         # 俯仰角速度（rad/s）
print(msg.yawspeed)           # 偏航角速度（rad/s）

# GLOBAL_POSITION_INT 消息
print(msg.lat)                # 纬度 × 1e7
print(msg.lon)                # 经度 × 1e7
print(msg.alt)                # 海拔高度（毫米）
print(msg.relative_alt)       # 相对起飞点高度（毫米）
print(msg.hdg)                # 航向（0-36000，厘度）
```

### 5.7 检查消息是否有效

```python
msg_type = msg.get_type()
if msg_type == 'BAD_DATA':
    # CRC 校验失败或帧解析错误
    pass
else:
    # 正常消息
    pass
```

### 5.8 获取消息的原始序列号

```python
seq = msg.get_seq()
# MAVLink 包序列号（0-255 循环），用于检测丢包
```

---

## 6. 心跳与状态检测

### 6.1 wait_heartbeat() — 等待首次心跳

```python
conn.wait_heartbeat(
    blocking: bool = True,     # True=阻塞等，False=直接返回
    timeout: float = None,     # 超时秒数
) -> bool
```

阻塞等待直到收到一次心跳。收到返回 `True`，超时返回 `False`。

```python
# 阻塞一直等
conn.wait_heartbeat()
print("飞控上线！")

# 最多等 10 秒
if conn.wait_heartbeat(timeout=10):
    print("连接成功")
else:
    print("超时，飞控无响应")
```

### 6.2 target_system 和 target_component

收到心跳后自动设置：

```python
conn.wait_heartbeat()
print(conn.target_system)      # 上次心跳的来源 sysid
print(conn.target_component)   # 上次心跳的来源 compid
```

发送指令时就可以直接用：

```python
conn.mav.command_long_send(
    conn.target_system,
    conn.target_component,
    ...指令...
)
```

### 6.3 time_since_last_heartbeat() — 距离上次心跳的时间

```python
conn.time_since_last_heartbeat() -> float 或 None
```

- 从未收到心跳 → `None`
- 收到过心跳 → `float`，从最后一条心跳到现在过了多少秒

```python
last = conn.time_since_last_heartbeat()
if last is None:
    print("还未收到心跳")
elif last > 3.0:
    print(f"飞控失联 {last:.1f} 秒")
else:
    print(f"飞控在线，心跳间隔 {last:.1f} 秒")
```

### 6.4 master.motd（登录欢迎语）

```python
print(conn.motd)
# 输出 MAVLink 协议声明，无实际用途
```

---

## 7. 连接信息与管理

### 7.1 关闭连接

```python
conn.close()
```

释放 socket/串口资源。

### 7.2 设置回放速度

```python
conn.set_speedup(speedup: float)
# 用于回放日志文件时加速
```

### 7.3 获取当前 MAVLink 消息计数

```python
conn.mav.total_packets_received     # 收到的总包数
conn.mav.total_packets_sent         # 发出的总包数
conn.mav.total_receive_errors       # 接收错误总数
conn.mav.total_packets_lost         # 丢包数（检测到序号跳跃）
```

---

## 8. 参数操作

### 8.1 请求并读取所有参数

```python
# 请求参数列表
conn.mav.param_request_list_send(
    conn.target_system,
    conn.target_component
)

# 逐条接收参数
while True:
    msg = conn.recv_match(type='PARAM_VALUE', blocking=True, timeout=30)
    if msg is None:
        break
    print(f"{msg.param_id}: {msg.param_value}")
```

### 8.2 设置参数

```python
conn.mav.param_set_send(
    conn.target_system,
    conn.target_component,
    b'PARAM_NAME',          # 参数名（bytes，最大16字符）
    value,                   # 参数值（float）
    mavutil.mavlink.MAV_PARAM_TYPE_REAL32  # 值类型
)
```

### 8.3 param_fetch_all() — 拉取全部参数

```python
conn.param_fetch_all()
# 内部发送 param_request_list，返回一个字典
```

---

## 9. 航点操作

### 9.1 请求航点数量

```python
conn.mav.mission_request_count_send(
    conn.target_system,
    conn.target_component
)
```

### 9.2 上传航点

```python
conn.mav.mission_count_send(
    conn.target_system,
    conn.target_component,
    count,                           # 航点总数
    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
)
# 然后等待对方请求每个航点，逐个发送
```

### 9.3 清除航点

```python
conn.mav.mission_clear_all_send(
    conn.target_system,
    conn.target_component,
    mavutil.mavlink.MAV_MISSION_TYPE_MISSION
)
```

---

## 10. 常用消息类型速查

### 10.1 消息类型名、msg_id、关键字段

| 类型名 | msg_id | 关键字段 |
|--------|:---:|------|
| `HEARTBEAT` | 0 | `type`, `autopilot`, `base_mode`, `custom_mode`, `system_status` |
| `SYS_STATUS` | 1 | `voltage_battery`, `current_battery`, `battery_remaining` |
| `ATTITUDE` | 30 | `roll`, `pitch`, `yaw`, `rollspeed`, `pitchspeed`, `yawspeed` |
| `GLOBAL_POSITION_INT` | 33 | `lat`, `lon`, `alt`, `relative_alt`, `hdg` |
| `GPS_RAW_INT` | 24 | `lat`, `lon`, `alt`, `satellites_visible`, `fix_type` |
| `VFR_HUD` | 74 | `airspeed`, `groundspeed`, `alt`, `throttle` |
| `COMMAND_ACK` | 77 | `command`, `result` |
| `STATUSTEXT` | 253 | `text`, `severity` |
| `BATTERY_STATUS` | 147 | `voltages`, `current_battery`, `battery_remaining` |
| `RC_CHANNELS` | 65 | `chan1_raw` ~ `chan18_raw` |
| `SERVO_OUTPUT_RAW` | 36 | `servo1_raw` ~ `servo16_raw` |
| `MISSION_CURRENT` | 42 | `seq`（当前航点序号） |
| `NAV_CONTROLLER_OUTPUT` | 62 | `nav_roll`, `nav_pitch`, `nav_bearing` |
| `BAD_DATA` | — | CRC 校验失败，**不是真正的消息类型** |

### 10.2 GLOBAL_POSITION_INT 字段单位

| 字段 | 单位 | 换算 |
|------|------|------|
| `lat` | 1e7 度 | `lat / 1e7` = 度 |
| `lon` | 1e7 度 | `lon / 1e7` = 度 |
| `alt` | 毫米 | `alt / 1e3` = 米（海拔） |
| `relative_alt` | 毫米 | `relative_alt / 1e3` = 米（相对起飞点） |

### 10.3 ATTITUDE 字段单位

| 字段 | 单位 |
|------|------|
| `roll` | 弧度 |
| `pitch` | 弧度 |
| `yaw` | 弧度 |
| `rollspeed` | rad/s |
| `pitchspeed` | rad/s |
| `yawspeed` | rad/s |

弧度转度：`degrees = radians * 180 / 3.14159`

---

## 11. 实用代码片段

### 11.1 最小收包程序

```python
from pymavlink import mavutil

conn = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
print("等待飞控...")
conn.wait_heartbeat()
print(f"飞控在线: sysid={conn.target_system}")

while True:
    msg = conn.recv_match(blocking=True, timeout=1)
    if msg and msg.get_type() != 'BAD_DATA':
        print(f"[{msg.get_type()}] {msg.to_dict()}")
```

### 11.2 按类型处理消息

```python
while True:
    msg = conn.recv_match(blocking=True, timeout=1)
    if msg is None or msg.get_type() == 'BAD_DATA':
        continue

    msg_type = msg.get_type()

    if msg_type == 'HEARTBEAT':
        print(f"心跳: status={msg.system_status}")

    elif msg_type == 'GLOBAL_POSITION_INT':
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        alt = msg.relative_alt / 1e3
        print(f"位置: {lat:.6f}, {lon:.6f}, {alt:.1f}m")

    elif msg_type == 'COMMAND_ACK':
        print(f"指令确认: cmd={msg.command}, result={msg.result}")
```

### 11.3 解锁 + 起飞 + 悬停

```python
import time

# 等待飞控上线
conn.wait_heartbeat()

# 解锁
conn.mav.command_long_send(
    conn.target_system, conn.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 1, 0, 0, 0, 0, 0, 0
)

# 等 ACK
msg = conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
print(f"解锁: {'成功' if msg and msg.result == 0 else '失败'}")

# 起飞到 10 米
conn.mav.command_long_send(
    conn.target_system, conn.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0, 0, 0, 0, 0, 0, 0, 10
)
print("起飞指令已发送")

# 等 5 秒
time.sleep(5)

# 切换到悬停
conn.mav.command_long_send(
    conn.target_system, conn.target_component,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0, 1, 4, 0, 0, 0, 0, 0      # custom_mode=4=LOITER
)
print("已切换悬停")
```

### 11.4 获取飞机实时状态

```python
def get_aircraft_state(conn) -> dict:
    """非阻塞地收集最新的飞机状态快照"""
    state = {}
    
    # 遍历缓冲区里所有消息，取每种类型最新的
    while True:
        msg = conn.recv_match(blocking=False)
        if msg is None:
            break
        
        msg_type = msg.get_type()
        if msg_type == 'HEARTBEAT':
            state['mode'] = msg.custom_mode
            state['status'] = msg.system_status
        elif msg_type == 'ATTITUDE':
            state['roll'] = msg.roll
            state['pitch'] = msg.pitch
            state['yaw'] = msg.yaw
        elif msg_type == 'GLOBAL_POSITION_INT':
            state['lat'] = msg.lat / 1e7
            state['lon'] = msg.lon / 1e7
            state['alt'] = msg.relative_alt / 1e3
        elif msg_type == 'SYS_STATUS':
            state['battery'] = msg.battery_remaining
    
    return state
```

### 11.5 收发线程分离（生产者-消费者）

```python
import threading
import queue

msg_queue = queue.Queue(maxsize=200)

# 生产者线程：收包
def receiver():
    while True:
        msg = conn.recv_match(blocking=True, timeout=0.5)
        if msg and msg.get_type() != 'BAD_DATA':
            msg_queue.put(msg)

# 消费者线程：处理
def handler():
    while True:
        msg = msg_queue.get()
        # 处理消息（写文件 / 转发 / 决策）
        print(f"[{msg.get_type()}]")

# 启动
threading.Thread(target=receiver, daemon=True).start()
threading.Thread(target=handler, daemon=True).start()
```

---

## 常量参考

### MAV_TYPE（飞行器类型）

```python
mavutil.mavlink.MAV_TYPE_QUADROTOR     = 2    # 四旋翼
mavutil.mavlink.MAV_TYPE_HELICOPTER    = 6    # 直升机
mavutil.mavlink.MAV_TYPE_FIXED_WING    = 1    # 固定翼
mavutil.mavlink.MAV_TYPE_GCS           = 6    # 地面站（实际值不同，用 mavutil 查）
```

### MAV_STATE（系统状态）

```python
mavutil.mavlink.MAV_STATE_UNINIT       = 0    # 未初始化
mavutil.mavlink.MAV_STATE_BOOT         = 1    # 启动中
mavutil.mavlink.MAV_STATE_STANDBY      = 3    # 待命
mavutil.mavlink.MAV_STATE_ACTIVE       = 4    # 激活（解锁/飞行中）
mavutil.mavlink.MAV_STATE_CRITICAL     = 5    # 临界（低电量等）
mavutil.mavlink.MAV_STATE_EMERGENCY    = 6    # 紧急
```

### MAV_AUTOPILOT（飞控类型）

```python
mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA  = 3    # ArduPilot
mavutil.mavlink.MAV_AUTOPILOT_PX4            = 12   # PX4
mavutil.mavlink.MAV_AUTOPILOT_INVALID        = 8    # 非飞控
```

### COMMAND_ACK result（指令执行结果）

```python
mavutil.mavlink.MAV_RESULT_ACCEPTED              = 0   # 成功
mavutil.mavlink.MAV_RESULT_TEMPORARILY_REJECTED  = 1   # 暂时拒绝
mavutil.mavlink.MAV_RESULT_DENIED                = 2   # 拒绝
mavutil.mavlink.MAV_RESULT_UNSUPPORTED           = 3   # 不支持
mavutil.mavlink.MAV_RESULT_FAILED                = 4   # 失败
```
