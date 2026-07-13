<<<<<<< HEAD
# MAVLink 协议完全解读：从字节流到无人机的通信语言

## 一、MAVLink 是什么

MAVLink（Micro Air Vehicle Link）是一种专为无人机设计的轻量级通信协议。2009 年由苏黎世联邦理工学院的 Lorenz Meier 在 PX4 项目中首次发布，至今已成为无人机领域事实上的标准通信协议。

它解决的**核心问题**是：一架无人机上的飞控计算机（如 Pixhawk）、传感器、摄像头、地面站电脑之间，需要一种可靠、实时、带宽高效的通信方式。

MAVLink 的设计思想是一条线贯穿始终：**在带宽有限的无线链路上，用最小的字节数传输最有价值的信息。**

一个典型的 MAVLink 包（MAVLink 1）只有 8 字节开销 + 有效载荷。这意味着在 915MHz 的无线电链路上（常见数传模块，速率约 250kbps），每秒可以传输数百条消息。

| 通信对象            | 物理链路                    | 典型消息               |
| ------------------- | --------------------------- | ---------------------- |
| 飞控 ↔ 地面站       | 数传电台（915MHz / 2.4GHz） | 位置、姿态、电池       |
| 飞控 ↔ 机载计算机   | 串口 UART / UDP             | 自定义指令、图像元数据 |
| 地面站 ↔ 多个无人机 | WiFi / LTE                  | 航线上传、指令下发     |
| 飞控 ↔ GPS 模块     | 串口（NMEA 协议）           | 不经过 MAVLink         |

------

## 二、MAVLink 1 与 MAVLink 2：两代协议的差异

MAVLink 至今有两个版本：

| 特性         | MAVLink 1      | MAVLink 2                                  |
| ------------ | -------------- | ------------------------------------------ |
| 首发年份     | 2009           | 2017                                       |
| 同步字节     | `0xFE`         | `0xFD`                                     |
| 消息 ID 长度 | 8 位（255 种） | 24 位（1677 万种）                         |
| 包开销       | 8 字节         | 12 字节（含 2 个标志位 + 13 字节可选签名） |
| 签名支持     | 不支持         | 支持（13 字节 HMAC 签名）                  |
| 字段扩展     | 不支持         | 支持（在 XML 中定义扩展字段）              |
| 空字节截断   | 不解           | 自动截断尾部零值字节                       |

**版本协商**：MAVLink 2 的库可以自动检测对方使用的版本。发送方通过 `HEARTBEAT` 消息中的 `mavlink_version` 字段表明自己的能力。如果接收方只支持 MAVLink 1，发送方会自动降级。

**向后兼容**：MAVLink 2 的库完全兼容 MAVLink 1 的包格式。一个运行 MAVLink 2 的飞控可以同时接收两种版本的消息，并在回复时使用接收方使用的版本。

------

## 三、从字节看协议：MAVLink 2 包的二进制结构

MAVLink 2 的包在电线上长这样（共 12 + n 字节，n 是有效载荷长度）：

```
字节偏移   C 类型        字段            说明
  0      uint8_t       magic           同步字节 0xFD
  1      uint8_t       len             有效载荷长度（n 字节，0-255）
  2      uint8_t       incompat_flags   不兼容标志位
  3      uint8_t       compat_flags     兼容标志位
  4      uint8_t       seq             序列号（0-255，发送方递增）
  5      uint8_t       sysid           发送端系统 ID（1-255）
  6      uint8_t       compid          发送端组件 ID（1-255）
  7-9    uint24_t      msgid           消息 ID（0-16777215）
  10     uint8_t[n]    payload          有效载荷
  10+n   uint16_t      checksum        校验和（CRC-16/MCRF4XX）
  12+n   uint8_t[13]   signature       签名（可选，仅 MAVLink 2）
```

**几个关键细节：**

1. **magic 字节区分版本**：`0xFE` 表示 MAVLink 1，`0xFD` 表示 MAVLink 2。接收方可以通过第一个字节区分版本。
2. **24 位消息 ID**：MAVLink 2 用三个字节存储 msgid，小端序。例如 msgid=0x004000 在数据流中呈现为 `0x00 0x40 0x00`。
3. **incompat_flags**：如果接收方不理解某个标志位，必须丢弃该包。目前最重要的标志是 `MAVLINK_IFLAG_SIGNED = 0x01`，表示该包已签名。
4. **序列号和丢包检测**：每个组件（sysid+compid 的组合）维护一个独立的 seq 计数器。地面站收到两个连续包，seq 从 10 跳到了 12，就知道丢了一包。
5. **校验和包含 CRC_EXTRA**：除了正常计算有效载荷的 CRC-16 外，校验和还包含一个叫 CRC_EXTRA 的字节——它是消息定义的哈希值。发送方和接收方如果使用不同的消息定义，CRC_EXTRA 不匹配，包会被拒绝。这防止了协议版本不兼容时的静默误判。

### MAVLink 1 的包结构

MAVLink 1 更紧凑，仅 8 字节开销：

```
字节偏移   C 类型        字段
  0      uint8_t       magic       0xFE
  1      uint8_t       len         有效载荷长度
  2      uint8_t       seq         序列号
  3      uint8_t       sysid       系统 ID
  4      uint8_t       compid      组件 ID
  5      uint8_t       msgid       消息 ID（0-255）
  6      uint8_t[n]    payload     有效载荷
  6+n    uint16_t      checksum    校验和
```

------

## 四、微服务：MAVLink 的高层协议

MAVLink 不只定义了消息格式，还定义了一组”微服务”（microservices）——它们规定了多条消息之间的配合方式。

### 4.1 Heartbeat——连接的基础

所有 MAVLink 系统必须发送 `HEARTBEAT`（msgid=0）。它的频率通常是 1Hz，包含三个关键字段：

- `type`: 系统类型（`MAV_TYPE_QUADROTOR` = 2，`MAV_TYPE_GCS` = 6 等）
- `autopilot`: 飞控类型（`MAV_AUTOPILOT_PX4` = 12，`MAV_AUTOPILOT_ARDUPILOTMEGA` = 3 等）
- `base_mode`: 系统状态（是否已解锁、是否在自动模式等）

**一个 HEARTBEAT 包的十六进制示例**：

```
FD 1C 00 00 00 01 01 00 00 00
01 00 00 00 00 01 00 00 00 02
00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 CA 6B
```

逐字段解析：

| 字节  | 值               | 含义                 |
| ----- | ---------------- | -------------------- |
| 0     | `0xFD`           | MAVLink 2 magic      |
| 1     | `0x1C`           | payload length=28    |
| 2     | `0x00`           | incompat_flags       |
| 3     | `0x00`           | compat_flags         |
| 4     | `0x00`           | seq=0                |
| 5     | `0x01`           | sysid=1              |
| 6     | `0x01`           | compid=1 (autopilot) |
| 7-9   | `0x00 0x00 0x00` | msgid=0 (HEARTBEAT)  |
| 10-37 | (28 bytes)       | payload              |
| 38-39 | `0xCA 0x6B`      | checksum             |

当接收方收到一个 HEARTBEAT 包时，它知道一个 sysid=1, compid=1 的系统在线了。

### 4.2 命令协议（Command Protocol）

命令协议用于发送需要确认的指令。它的工作模式是请求-响应：

1. 地面站发送 `COMMAND_LONG`（msgid=76）或 `COMMAND_INT`（msgid=192）
2. 飞控执行命令后返回 `COMMAND_ACK`（msgid=77）
3. `COMMAND_ACK` 中包含了原始命令的编号和执行结果（`MAV_RESULT_ACCEPTED`/`DENIED`/`TEMPORARILY_REJECTED`/`UNSUPPORTED`/`FAILED`）

常用命令（由 `MAV_CMD` 枚举定义）：

| 命令 ID | 名称                           | 用途             |
| ------- | ------------------------------ | ---------------- |
| 400     | `MAV_CMD_COMPONENT_ARM_DISARM` | 解锁/锁定        |
| 21      | `MAV_CMD_NAV_TAKEOFF`          | 自动起飞         |
| 22      | `MAV_CMD_NAV_LAND`             | 自动降落         |
| 84      | `MAV_CMD_REQUEST_MESSAGE`      | 请求指定消息     |
| 511     | `MAV_CMD_SET_MESSAGE_INTERVAL` | 设置消息发送频率 |
| 520     | `MAV_CMD_DO_SET_MODE`          | 切换飞行模式     |

### 4.3 参数协议（Parameter Protocol）

地面站通过参数协议读取和写入飞控的数百个参数。协议使用三个消息：

- `PARAM_REQUEST_LIST`（msgid=21）：请求所有参数列表
- `PARAM_VALUE`（msgid=22）：单个参数的名称、值和类型
- `PARAM_SET`（msgid=23）：写入参数

参数名是一个最长为 16 字节的 ASCII 字符串（以 `0x00` 结尾），类型由 `MAV_PARAM_TYPE` 枚举标识（`UINT8`=1，`INT16`=3，`FLOAT`=9 等）。所有数值参数在协议中以浮点数传输——即使是整型参数也被转换为浮点，存在精度损失。因此 PX4 和 ArduPilot 后来都引入了扩展参数协议（`PARAM_EXT_*` 系列消息），使用 IEEE 754 双精度浮点。

### 4.4 航线协议（Mission Protocol）

上传一条航线到飞控的典型流程：

1. 地面站发送 `MISSION_COUNT`（msgid=44），声明 n 个航点
2. 飞控回复 `MISSION_REQUEST`（msgid=40），请求第 i 个航点
3. 地面站发送 `MISSION_ITEM_INT`（msgid=73），包含第 i 个航点的坐标、高度、动作
4. 重复步骤 2-3 直到所有航点传输完成
5. 飞控发送 `MISSION_ACK`（msgid=47）确认接收

### 4.5 Offboard 控制（Offboard Control Protocol）

机载计算机通过 Offboard 协议直接控制无人机飞行，不需要经过遥控器。这是无人机自主飞行最常用的方式：

1. 机载计算机以高频率（通常 20-50Hz）发送 `SET_ATTITUDE_TARGET`（msgid=82）或 `SET_POSITION_TARGET_LOCAL_NED`（msgid=84）
2. 飞控进入 `OFFBOARD` 模式后，跟随这些指令飞行
3. 如果停止接收指令超过 0.5 秒，飞控自动退出 Offboard 模式并切换回安全模式

------

## 五、消息定义与代码生成

MAVLink 的消息定义使用 XML 文件描述。最小的定义集是 `minimal.xml`，只包含 HEARTBEAT 和 ERROR。`common.xml` 包含了所有标准消息（231 种），大多数飞控使用这个集合。

一个典型的消息定义：

```
<message id="0" name="HEARTBEAT">
  <description>The heartbeat message shows that a system or component is present and responding.</description>
  <field type="uint8_t" name="type">Type of the MAV (quadrotor, helicopter, etc.)</field>
  <field type="uint8_t" name="autopilot">Autopilot type</field>
  <field type="uint8_t" name="base_mode">System mode bitmap</field>
  <field type="uint32_t" name="custom_mode" display="bitmask">A bitfield for use for autopilot-specific flags</field>
  <field type="uint8_t" name="system_status">System status flag</field>
  <field type="uint8_t" name="mavlink_version">MAVLink version</field>
</message>
```

代码生成器 `mavgen` 从 XML 生成 C/C++/Python 源代码：

```
python -m pymavlink.tools.mavgen --lang Python --output ./mavlink_v2 common.xml
```

生成的代码中包含每个消息的序列化、反序列化、以及 CRC_EXTRA 值。CRC_EXTRA 是 XML 定义经过规范化哈希计算得到的一个字节，保证发送方和接收方使用相同的消息定义。

------

## 六、传输层：UDP、TCP、串口

MAVLink 本身不关心传输层——它只管打包和解包。但不同的传输方式有不同的行为。

### 6.1 UDP

这是仿真和机载计算机最常用的方式。UDP 无连接、无重传，适合实时遥测。

**PX4 默认 UDP 端口**：

| 端口  | 用途                                      |
| ----- | ----------------------------------------- |
| 14540 | 机载计算机（Offboard 控制、高带宽遥测）   |
| 14550 | 地面站（QGroundControl、Mission Planner） |
| 14580 | GCS 桥接（多机编队场景）                  |
| 18570 | 地面站指令通道（ARM、SET_MODE 等）        |

仿真的端口分配：Gazebo SITL 默认在 UDP 14540 监听机载计算机的连接，在 UDP 14550 监听地面站的连接。

### 6.2 TCP

TCP 提供可靠传输，适合航线上传和参数读写等不允许丢包的操作。但 TCP 的拥塞控制和重传机制在高延迟或丢包严重的无线链路上会导致延迟抖动，不适合实时姿态控制。

PX4 在 TCP 4560 端口监听 HIL（Hardware-in-the-Loop）连接——这是仿真模式下将自定义动力学引擎接入 PX4 的标准方式。

### 6.3 串口（UART）

实体飞控与数传模块、GPS、机载计算机间的典型连接。波特率从 57600（数传）到 921600（高速串口）不等。串口上的 MAVLink 需要自己处理分包——通过 sync 字节 `0xFD` 或 `0xFE` 定位包的起始位置。

串口上没有拥塞控制，数据发送方需要自行控制速率，避免缓冲区溢出。

| 传输方式 | 可靠性           | 实时性       | 典型场景           |
| -------- | ---------------- | ------------ | ------------------ |
| UDP      | 低（丢包不重传） | 高           | 遥测、Offboard     |
| TCP      | 高（重传保障）   | 中（抖动大） | 参数读写、航线上传 |
| 串口     | 中（无拥塞控制） | 高           | 数传、机载串口连接 |

------

## 七、消息 ID 大全：常用消息速查

`common.xml` 中定义了 231 种消息。以下是无人机开发中最常用的一些：

| msgid | 名称                          | 频率     | 说明                                    |
| ----- | ----------------------------- | -------- | --------------------------------------- |
| 0     | HEARTBEAT                     | 1Hz      | 心跳、系统状态                          |
| 1     | SYS_STATUS                    | 1Hz      | 电池电压、传感器状态                    |
| 24    | GPS_RAW_INT                   | 5-10Hz   | GPS 位置、速度、精度                    |
| 30    | ATTITUDE                      | 10-50Hz  | 四元数、角速度                          |
| 32    | LOCAL_POSITION_NED            | 20-50Hz  | 机体系 NED 位置                         |
| 33    | GLOBAL_POSITION_INT           | 5-10Hz   | GPS 经纬度+高度+相对高度                |
| 65    | RC_CHANNELS                   | 5-50Hz   | 遥控器通道值                            |
| 74    | VFR_HUD                       | 5Hz      | 空速、地速、高度、爬升率                |
| 82    | SET_ATTITUDE_TARGET           | 20-50Hz  | Offboard 姿态目标                       |
| 84    | SET_POSITION_TARGET_LOCAL_NED | 20-50Hz  | Offboard 位置目标                       |
| 87    | HIL_STATE_QUATERNION          | 250Hz    | HIL 仿真状态（四元数+位置+速度）        |
| 107   | ESTIMATOR_STATUS              | 1Hz      | EKF 状态健康度（GPS/视觉/IMU 融合质量） |
| 147   | BATTERY_STATUS                | 0.5-1Hz  | 电池详细状态                            |
| 253   | STATUSTEXT                    | 事件触发 | 飞控日志/错误信息（INFO/WARN/ERROR）    |

------

## 八、pymavlink 实战

Python 中最常用的 MAVLink 库是 **pymavlink**。

### 8.1 安装

```
pip install pymavlink
```

### 8.2 创建连接

```
from pymavlink import mavutil

# UDP 连接（仿真中的飞控）
master = mavutil.mavlink_connection('udp:127.0.0.1:14540')

# TCP 连接（HIL 仿真）
master = mavutil.mavlink_connection('tcp:127.0.0.1:4560')

# 串口连接（实体飞控）
master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)
```

### 8.3 等待心跳

```
master.wait_heartbeat()
print(f"收到心跳: sysid={master.target_system}, compid={master.target_component}")
```

### 8.4 接收消息

```
# 阻塞等待指定消息
msg = master.recv_match(type='ATTITUDE', blocking=True)
print(f"roll={msg.roll:.2f}, pitch={msg.pitch:.2f}, yaw={msg.yaw:.2f}")

# 非阻塞循环接收
while True:
    msg = master.recv_match(blocking=False)
    if msg:
        msg_type = msg.get_type()
        if msg_type == 'HEARTBEAT':
            print(f"mode={msg.base_mode}, status={msg.system_status}")
        elif msg_type == 'GLOBAL_POSITION_INT':
            print(f"lat={msg.lat/1e7:.6f}, lon={msg.lon/1e7:.6f}, alt={msg.alt/1e3:.1f}m")
```

### 8.5 发送 Offboard 指令

```
# 解锁
master.mav.command_long_send(
    1, 1,  # target_system, target_component
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,     # confirmation
    1,     # param1: 1=arm, 0=disarm
    0, 0, 0, 0, 0
)

# 发送位置目标（Offboard 模式）
master.mav.set_position_target_local_ned_send(
    0,          # time_boot_ms
    1, 1,       # target_system, target_component
    mavutil.mavlink.MAV_FRAME_LOCAL_NED,
    0b0000111111111000,  # type_mask (position only)
    0, 0, -10,  # x, y, z (NED: z 向上为负)
    0, 0, 0,    # vx, vy, vz
    0, 0, 0,    # afx, afy, afz
    0, 0        # yaw, yaw_rate
)
```

`type_mask` 是一个位掩码，每一位代表一个字段是否被忽略：

- 位 0-2：忽略位置 x, y, z
- 位 3-5：忽略速度 vx, vy, vz
- 位 6-8：忽略加速度 afx, afy, afz
- 位 9：忽略偏航
- 位 10：忽略偏航速率

如果要控制位置，设置 type_mask=0b0000111111111000（只使用位置字段，忽略速度和加速度）。

### 8.6 读取参数

```
# 请求参数列表
master.mav.param_request_list_send(1, 1)

# 接收参数
while True:
    msg = master.recv_match(type='PARAM_VALUE', blocking=True)
    param_id = msg.param_id.decode('utf-8').strip('\x00')
    param_value = msg.param_value
    print(f"{param_id} = {param_value}")
```

------

## 九、常见问题与调试

### 9.1 如何抓包分析

Wireshark 原生支持 MAVLink 协议解析。在 UDP 14550 端口上抓包：

```
# 抓包命令
tcpdump -i lo -w mavlink.pcap port 14550
```

在 Wireshark 中打开后，每条 MAVLink 消息都会被自动解析为人类可读的字段。也可以使用 `mavlink-mavgen` 工具：

```
python -m pymavlink.tools.mavgen --test mavlink.pcap
```

### 9.2 丢包怎么办

- 检查无线信号质量（`RSSI` 值）
- 降低消息频率（`SET_MESSAGE_INTERVAL` 命令）
- 使用更短的 payload（避免大消息分片）
- 检查波特率是否设置正确

### 9.3 版本兼容性

如果飞控只发送 MAVLink 1 的包（sync=0xFE），而地面站只收 MAVLink 2 的包（sync=0xFD），大部分现代库会自动协商。但如果使用自定义实现的解析器，需要同时处理两种 sync 字节。

------

## 参考文献

1. MAVLink Developer Guide. https://mavlink.io/en/
2. Meier, L., et al. (2011). “MAVLink: Micro Air Vehicle Communication Protocol.” ETH Zurich.
3. PX4 Autopilot User Guide - MAVLink Telemetry. https://docs.px4.io/main/en/telemetry/
4. Wireshark MAVLink Dissector. https://www.wireshark.org/docs/dfref/m/mavlink.html
=======
# MAVLink 协议完全解读：从字节流到无人机的通信语言

## 一、MAVLink 是什么

MAVLink（Micro Air Vehicle Link）是一种专为无人机设计的轻量级通信协议。2009 年由苏黎世联邦理工学院的 Lorenz Meier 在 PX4 项目中首次发布，至今已成为无人机领域事实上的标准通信协议。

它解决的**核心问题**是：一架无人机上的飞控计算机（如 Pixhawk）、传感器、摄像头、地面站电脑之间，需要一种可靠、实时、带宽高效的通信方式。

MAVLink 的设计思想是一条线贯穿始终：**在带宽有限的无线链路上，用最小的字节数传输最有价值的信息。**

一个典型的 MAVLink 包（MAVLink 1）只有 8 字节开销 + 有效载荷。这意味着在 915MHz 的无线电链路上（常见数传模块，速率约 250kbps），每秒可以传输数百条消息。

| 通信对象            | 物理链路                    | 典型消息               |
| ------------------- | --------------------------- | ---------------------- |
| 飞控 ↔ 地面站       | 数传电台（915MHz / 2.4GHz） | 位置、姿态、电池       |
| 飞控 ↔ 机载计算机   | 串口 UART / UDP             | 自定义指令、图像元数据 |
| 地面站 ↔ 多个无人机 | WiFi / LTE                  | 航线上传、指令下发     |
| 飞控 ↔ GPS 模块     | 串口（NMEA 协议）           | 不经过 MAVLink         |

------

## 二、MAVLink 1 与 MAVLink 2：两代协议的差异

MAVLink 至今有两个版本：

| 特性         | MAVLink 1      | MAVLink 2                                  |
| ------------ | -------------- | ------------------------------------------ |
| 首发年份     | 2009           | 2017                                       |
| 同步字节     | `0xFE`         | `0xFD`                                     |
| 消息 ID 长度 | 8 位（255 种） | 24 位（1677 万种）                         |
| 包开销       | 8 字节         | 12 字节（含 2 个标志位 + 13 字节可选签名） |
| 签名支持     | 不支持         | 支持（13 字节 HMAC 签名）                  |
| 字段扩展     | 不支持         | 支持（在 XML 中定义扩展字段）              |
| 空字节截断   | 不解           | 自动截断尾部零值字节                       |

**版本协商**：MAVLink 2 的库可以自动检测对方使用的版本。发送方通过 `HEARTBEAT` 消息中的 `mavlink_version` 字段表明自己的能力。如果接收方只支持 MAVLink 1，发送方会自动降级。

**向后兼容**：MAVLink 2 的库完全兼容 MAVLink 1 的包格式。一个运行 MAVLink 2 的飞控可以同时接收两种版本的消息，并在回复时使用接收方使用的版本。

------

## 三、从字节看协议：MAVLink 2 包的二进制结构

MAVLink 2 的包在电线上长这样（共 12 + n 字节，n 是有效载荷长度）：

```
字节偏移   C 类型        字段            说明
  0      uint8_t       magic           同步字节 0xFD
  1      uint8_t       len             有效载荷长度（n 字节，0-255）
  2      uint8_t       incompat_flags   不兼容标志位
  3      uint8_t       compat_flags     兼容标志位
  4      uint8_t       seq             序列号（0-255，发送方递增）
  5      uint8_t       sysid           发送端系统 ID（1-255）
  6      uint8_t       compid          发送端组件 ID（1-255）
  7-9    uint24_t      msgid           消息 ID（0-16777215）
  10     uint8_t[n]    payload          有效载荷
  10+n   uint16_t      checksum        校验和（CRC-16/MCRF4XX）
  12+n   uint8_t[13]   signature       签名（可选，仅 MAVLink 2）
```

**几个关键细节：**

1. **magic 字节区分版本**：`0xFE` 表示 MAVLink 1，`0xFD` 表示 MAVLink 2。接收方可以通过第一个字节区分版本。
2. **24 位消息 ID**：MAVLink 2 用三个字节存储 msgid，小端序。例如 msgid=0x004000 在数据流中呈现为 `0x00 0x40 0x00`。
3. **incompat_flags**：如果接收方不理解某个标志位，必须丢弃该包。目前最重要的标志是 `MAVLINK_IFLAG_SIGNED = 0x01`，表示该包已签名。
4. **序列号和丢包检测**：每个组件（sysid+compid 的组合）维护一个独立的 seq 计数器。地面站收到两个连续包，seq 从 10 跳到了 12，就知道丢了一包。
5. **校验和包含 CRC_EXTRA**：除了正常计算有效载荷的 CRC-16 外，校验和还包含一个叫 CRC_EXTRA 的字节——它是消息定义的哈希值。发送方和接收方如果使用不同的消息定义，CRC_EXTRA 不匹配，包会被拒绝。这防止了协议版本不兼容时的静默误判。

### MAVLink 1 的包结构

MAVLink 1 更紧凑，仅 8 字节开销：

```
字节偏移   C 类型        字段
  0      uint8_t       magic       0xFE
  1      uint8_t       len         有效载荷长度
  2      uint8_t       seq         序列号
  3      uint8_t       sysid       系统 ID
  4      uint8_t       compid      组件 ID
  5      uint8_t       msgid       消息 ID（0-255）
  6      uint8_t[n]    payload     有效载荷
  6+n    uint16_t      checksum    校验和
```

------

## 四、微服务：MAVLink 的高层协议

MAVLink 不只定义了消息格式，还定义了一组”微服务”（microservices）——它们规定了多条消息之间的配合方式。

### 4.1 Heartbeat——连接的基础

所有 MAVLink 系统必须发送 `HEARTBEAT`（msgid=0）。它的频率通常是 1Hz，包含三个关键字段：

- `type`: 系统类型（`MAV_TYPE_QUADROTOR` = 2，`MAV_TYPE_GCS` = 6 等）
- `autopilot`: 飞控类型（`MAV_AUTOPILOT_PX4` = 12，`MAV_AUTOPILOT_ARDUPILOTMEGA` = 3 等）
- `base_mode`: 系统状态（是否已解锁、是否在自动模式等）

**一个 HEARTBEAT 包的十六进制示例**：

```
FD 1C 00 00 00 01 01 00 00 00
01 00 00 00 00 01 00 00 00 02
00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 CA 6B
```

逐字段解析：

| 字节  | 值               | 含义                 |
| ----- | ---------------- | -------------------- |
| 0     | `0xFD`           | MAVLink 2 magic      |
| 1     | `0x1C`           | payload length=28    |
| 2     | `0x00`           | incompat_flags       |
| 3     | `0x00`           | compat_flags         |
| 4     | `0x00`           | seq=0                |
| 5     | `0x01`           | sysid=1              |
| 6     | `0x01`           | compid=1 (autopilot) |
| 7-9   | `0x00 0x00 0x00` | msgid=0 (HEARTBEAT)  |
| 10-37 | (28 bytes)       | payload              |
| 38-39 | `0xCA 0x6B`      | checksum             |

当接收方收到一个 HEARTBEAT 包时，它知道一个 sysid=1, compid=1 的系统在线了。

### 4.2 命令协议（Command Protocol）

命令协议用于发送需要确认的指令。它的工作模式是请求-响应：

1. 地面站发送 `COMMAND_LONG`（msgid=76）或 `COMMAND_INT`（msgid=192）
2. 飞控执行命令后返回 `COMMAND_ACK`（msgid=77）
3. `COMMAND_ACK` 中包含了原始命令的编号和执行结果（`MAV_RESULT_ACCEPTED`/`DENIED`/`TEMPORARILY_REJECTED`/`UNSUPPORTED`/`FAILED`）

常用命令（由 `MAV_CMD` 枚举定义）：

| 命令 ID | 名称                           | 用途             |
| ------- | ------------------------------ | ---------------- |
| 400     | `MAV_CMD_COMPONENT_ARM_DISARM` | 解锁/锁定        |
| 21      | `MAV_CMD_NAV_TAKEOFF`          | 自动起飞         |
| 22      | `MAV_CMD_NAV_LAND`             | 自动降落         |
| 84      | `MAV_CMD_REQUEST_MESSAGE`      | 请求指定消息     |
| 511     | `MAV_CMD_SET_MESSAGE_INTERVAL` | 设置消息发送频率 |
| 520     | `MAV_CMD_DO_SET_MODE`          | 切换飞行模式     |

### 4.3 参数协议（Parameter Protocol）

地面站通过参数协议读取和写入飞控的数百个参数。协议使用三个消息：

- `PARAM_REQUEST_LIST`（msgid=21）：请求所有参数列表
- `PARAM_VALUE`（msgid=22）：单个参数的名称、值和类型
- `PARAM_SET`（msgid=23）：写入参数

参数名是一个最长为 16 字节的 ASCII 字符串（以 `0x00` 结尾），类型由 `MAV_PARAM_TYPE` 枚举标识（`UINT8`=1，`INT16`=3，`FLOAT`=9 等）。所有数值参数在协议中以浮点数传输——即使是整型参数也被转换为浮点，存在精度损失。因此 PX4 和 ArduPilot 后来都引入了扩展参数协议（`PARAM_EXT_*` 系列消息），使用 IEEE 754 双精度浮点。

### 4.4 航线协议（Mission Protocol）

上传一条航线到飞控的典型流程：

1. 地面站发送 `MISSION_COUNT`（msgid=44），声明 n 个航点
2. 飞控回复 `MISSION_REQUEST`（msgid=40），请求第 i 个航点
3. 地面站发送 `MISSION_ITEM_INT`（msgid=73），包含第 i 个航点的坐标、高度、动作
4. 重复步骤 2-3 直到所有航点传输完成
5. 飞控发送 `MISSION_ACK`（msgid=47）确认接收

### 4.5 Offboard 控制（Offboard Control Protocol）

机载计算机通过 Offboard 协议直接控制无人机飞行，不需要经过遥控器。这是无人机自主飞行最常用的方式：

1. 机载计算机以高频率（通常 20-50Hz）发送 `SET_ATTITUDE_TARGET`（msgid=82）或 `SET_POSITION_TARGET_LOCAL_NED`（msgid=84）
2. 飞控进入 `OFFBOARD` 模式后，跟随这些指令飞行
3. 如果停止接收指令超过 0.5 秒，飞控自动退出 Offboard 模式并切换回安全模式

------

## 五、消息定义与代码生成

MAVLink 的消息定义使用 XML 文件描述。最小的定义集是 `minimal.xml`，只包含 HEARTBEAT 和 ERROR。`common.xml` 包含了所有标准消息（231 种），大多数飞控使用这个集合。

一个典型的消息定义：

```
<message id="0" name="HEARTBEAT">
  <description>The heartbeat message shows that a system or component is present and responding.</description>
  <field type="uint8_t" name="type">Type of the MAV (quadrotor, helicopter, etc.)</field>
  <field type="uint8_t" name="autopilot">Autopilot type</field>
  <field type="uint8_t" name="base_mode">System mode bitmap</field>
  <field type="uint32_t" name="custom_mode" display="bitmask">A bitfield for use for autopilot-specific flags</field>
  <field type="uint8_t" name="system_status">System status flag</field>
  <field type="uint8_t" name="mavlink_version">MAVLink version</field>
</message>
```

代码生成器 `mavgen` 从 XML 生成 C/C++/Python 源代码：

```
python -m pymavlink.tools.mavgen --lang Python --output ./mavlink_v2 common.xml
```

生成的代码中包含每个消息的序列化、反序列化、以及 CRC_EXTRA 值。CRC_EXTRA 是 XML 定义经过规范化哈希计算得到的一个字节，保证发送方和接收方使用相同的消息定义。

------

## 六、传输层：UDP、TCP、串口

MAVLink 本身不关心传输层——它只管打包和解包。但不同的传输方式有不同的行为。

### 6.1 UDP

这是仿真和机载计算机最常用的方式。UDP 无连接、无重传，适合实时遥测。

**PX4 默认 UDP 端口**：

| 端口  | 用途                                      |
| ----- | ----------------------------------------- |
| 14540 | 机载计算机（Offboard 控制、高带宽遥测）   |
| 14550 | 地面站（QGroundControl、Mission Planner） |
| 14580 | GCS 桥接（多机编队场景）                  |
| 18570 | 地面站指令通道（ARM、SET_MODE 等）        |

仿真的端口分配：Gazebo SITL 默认在 UDP 14540 监听机载计算机的连接，在 UDP 14550 监听地面站的连接。

### 6.2 TCP

TCP 提供可靠传输，适合航线上传和参数读写等不允许丢包的操作。但 TCP 的拥塞控制和重传机制在高延迟或丢包严重的无线链路上会导致延迟抖动，不适合实时姿态控制。

PX4 在 TCP 4560 端口监听 HIL（Hardware-in-the-Loop）连接——这是仿真模式下将自定义动力学引擎接入 PX4 的标准方式。

### 6.3 串口（UART）

实体飞控与数传模块、GPS、机载计算机间的典型连接。波特率从 57600（数传）到 921600（高速串口）不等。串口上的 MAVLink 需要自己处理分包——通过 sync 字节 `0xFD` 或 `0xFE` 定位包的起始位置。

串口上没有拥塞控制，数据发送方需要自行控制速率，避免缓冲区溢出。

| 传输方式 | 可靠性           | 实时性       | 典型场景           |
| -------- | ---------------- | ------------ | ------------------ |
| UDP      | 低（丢包不重传） | 高           | 遥测、Offboard     |
| TCP      | 高（重传保障）   | 中（抖动大） | 参数读写、航线上传 |
| 串口     | 中（无拥塞控制） | 高           | 数传、机载串口连接 |

------

## 七、消息 ID 大全：常用消息速查

`common.xml` 中定义了 231 种消息。以下是无人机开发中最常用的一些：

| msgid | 名称                          | 频率     | 说明                                    |
| ----- | ----------------------------- | -------- | --------------------------------------- |
| 0     | HEARTBEAT                     | 1Hz      | 心跳、系统状态                          |
| 1     | SYS_STATUS                    | 1Hz      | 电池电压、传感器状态                    |
| 24    | GPS_RAW_INT                   | 5-10Hz   | GPS 位置、速度、精度                    |
| 30    | ATTITUDE                      | 10-50Hz  | 四元数、角速度                          |
| 32    | LOCAL_POSITION_NED            | 20-50Hz  | 机体系 NED 位置                         |
| 33    | GLOBAL_POSITION_INT           | 5-10Hz   | GPS 经纬度+高度+相对高度                |
| 65    | RC_CHANNELS                   | 5-50Hz   | 遥控器通道值                            |
| 74    | VFR_HUD                       | 5Hz      | 空速、地速、高度、爬升率                |
| 82    | SET_ATTITUDE_TARGET           | 20-50Hz  | Offboard 姿态目标                       |
| 84    | SET_POSITION_TARGET_LOCAL_NED | 20-50Hz  | Offboard 位置目标                       |
| 87    | HIL_STATE_QUATERNION          | 250Hz    | HIL 仿真状态（四元数+位置+速度）        |
| 107   | ESTIMATOR_STATUS              | 1Hz      | EKF 状态健康度（GPS/视觉/IMU 融合质量） |
| 147   | BATTERY_STATUS                | 0.5-1Hz  | 电池详细状态                            |
| 253   | STATUSTEXT                    | 事件触发 | 飞控日志/错误信息（INFO/WARN/ERROR）    |

------

## 八、pymavlink 实战

Python 中最常用的 MAVLink 库是 **pymavlink**。

### 8.1 安装

```
pip install pymavlink
```

### 8.2 创建连接

```
from pymavlink import mavutil

# UDP 连接（仿真中的飞控）
master = mavutil.mavlink_connection('udp:127.0.0.1:14540')

# TCP 连接（HIL 仿真）
master = mavutil.mavlink_connection('tcp:127.0.0.1:4560')

# 串口连接（实体飞控）
master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)
```

### 8.3 等待心跳

```
master.wait_heartbeat()
print(f"收到心跳: sysid={master.target_system}, compid={master.target_component}")
```

### 8.4 接收消息

```
# 阻塞等待指定消息
msg = master.recv_match(type='ATTITUDE', blocking=True)
print(f"roll={msg.roll:.2f}, pitch={msg.pitch:.2f}, yaw={msg.yaw:.2f}")

# 非阻塞循环接收
while True:
    msg = master.recv_match(blocking=False)
    if msg:
        msg_type = msg.get_type()
        if msg_type == 'HEARTBEAT':
            print(f"mode={msg.base_mode}, status={msg.system_status}")
        elif msg_type == 'GLOBAL_POSITION_INT':
            print(f"lat={msg.lat/1e7:.6f}, lon={msg.lon/1e7:.6f}, alt={msg.alt/1e3:.1f}m")
```

### 8.5 发送 Offboard 指令

```
# 解锁
master.mav.command_long_send(
    1, 1,  # target_system, target_component
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,     # confirmation
    1,     # param1: 1=arm, 0=disarm
    0, 0, 0, 0, 0
)

# 发送位置目标（Offboard 模式）
master.mav.set_position_target_local_ned_send(
    0,          # time_boot_ms
    1, 1,       # target_system, target_component
    mavutil.mavlink.MAV_FRAME_LOCAL_NED,
    0b0000111111111000,  # type_mask (position only)
    0, 0, -10,  # x, y, z (NED: z 向上为负)
    0, 0, 0,    # vx, vy, vz
    0, 0, 0,    # afx, afy, afz
    0, 0        # yaw, yaw_rate
)
```

`type_mask` 是一个位掩码，每一位代表一个字段是否被忽略：

- 位 0-2：忽略位置 x, y, z
- 位 3-5：忽略速度 vx, vy, vz
- 位 6-8：忽略加速度 afx, afy, afz
- 位 9：忽略偏航
- 位 10：忽略偏航速率

如果要控制位置，设置 type_mask=0b0000111111111000（只使用位置字段，忽略速度和加速度）。

### 8.6 读取参数

```
# 请求参数列表
master.mav.param_request_list_send(1, 1)

# 接收参数
while True:
    msg = master.recv_match(type='PARAM_VALUE', blocking=True)
    param_id = msg.param_id.decode('utf-8').strip('\x00')
    param_value = msg.param_value
    print(f"{param_id} = {param_value}")
```

------

## 九、常见问题与调试

### 9.1 如何抓包分析

Wireshark 原生支持 MAVLink 协议解析。在 UDP 14550 端口上抓包：

```
# 抓包命令
tcpdump -i lo -w mavlink.pcap port 14550
```

在 Wireshark 中打开后，每条 MAVLink 消息都会被自动解析为人类可读的字段。也可以使用 `mavlink-mavgen` 工具：

```
python -m pymavlink.tools.mavgen --test mavlink.pcap
```

### 9.2 丢包怎么办

- 检查无线信号质量（`RSSI` 值）
- 降低消息频率（`SET_MESSAGE_INTERVAL` 命令）
- 使用更短的 payload（避免大消息分片）
- 检查波特率是否设置正确

### 9.3 版本兼容性

如果飞控只发送 MAVLink 1 的包（sync=0xFE），而地面站只收 MAVLink 2 的包（sync=0xFD），大部分现代库会自动协商。但如果使用自定义实现的解析器，需要同时处理两种 sync 字节。

------

## 参考文献

1. MAVLink Developer Guide. https://mavlink.io/en/
2. Meier, L., et al. (2011). “MAVLink: Micro Air Vehicle Communication Protocol.” ETH Zurich.
3. PX4 Autopilot User Guide - MAVLink Telemetry. https://docs.px4.io/main/en/telemetry/
4. Wireshark MAVLink Dissector. https://www.wireshark.org/docs/dfref/m/mavlink.html
>>>>>>> 9b9a6c4f18b4d2603d4ca758c7176b5339f068d1
5. pymavlink Documentation. https://github.com/ArduPilot/pymavlink