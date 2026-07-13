# 通信链路与 MAVLink 协议 — 分层学习笔记

> 按四层架构拆分：**飞机层**（飞控端硬件+协议栈）和 **通讯层**（树莓派→4G→服务器链路）。
> 原则：**先画清整条链路，再逐段深入；先理解数据怎么流的，再写代码。**

---

## 目录

- [0. 全局视图：一条指令的旅程](#0-全局视图一条指令的旅程)
- [1. 飞机层 — 飞控端的 MAVLink](#1-飞机层--飞控端的-mavlink)
- [2. 通讯层 — 树莓派到服务器的链路](#2-通讯层--树莓派到服务器的链路)
- [3. 层间接口：飞机层 ↔ 通讯层](#3-层间接口飞机层--通讯层)
- [4. 实操任务](#4-实操任务)
- [5. 经验预警](#5-经验预警)

---

## 0. 全局视图：一条指令的旅程

以"服务器下发投放包裹指令"为例，追踪信号从头到尾经过的所有环节：

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       一条 MAVLink 指令的完整路径                          │
│                                                                          │
│  服务层                   通讯层                       飞机层              │
│                                                                          │
│  [Flask API] ──→ [mavlink-router] ──→ UDP ──→ 4G公网 ──→ [树莓派]       │
│  pymavlink         路由转发          14550     互联网      mavproxy      │
│  构造消息                                                      │         │
│                                                     UART /dev/serial0    │
│                                                                │         │
│                                                            [DM-FC01]     │
│                                                            TELEM1/USART2 │
│                                                            ArduPilot     │
│                                                            MAVLink栈     │
│                                                                │         │
│                                                           PWM → 舵机     │
│                                                           PB1引脚        │
│                                                           SERVO5         │
│                                                                          │
│  段④: 服务器内部        段③: 4G链路           段②: 树莓派      段①: 飞控  │
│  延迟 <1ms             30-80ms              ~1ms             <1ms        │
│  协议: Python对象      协议: UDP/IP         协议: MAVLink     协议: PWM   │
│       → MAVLink帧           → MAVLink帧          over UART      50Hz     │
└──────────────────────────────────────────────────────────────────────────┘
```

**核心认知**：MAVLink 是一个"信封格式"——它定义消息怎么打包成二进制字节，但不关心字节走串口、UDP 还是 4G。整条链路每一段都在做同一件事：**把 MAVLink 字节流从一端搬到另一端**，只有终点（飞控/服务器）才解析消息内容。

---

## 1. 飞机层 — 飞控端的 MAVLink

### 1.1 物理连接：飞控怎么接到树莓派

DM-FC01 飞控上有 **TELEM1** 接口（JST-GH 4-pin 连接器），内部接到 STM32H743 的 **USART2**。

```
DM-FC01 TELEM1 (USART2)              树莓派 3B GPIO
┌─────────────────────┐             ┌──────────────────┐
│ Pin1: VCC 5V        │─────────────│ Pin2/4: 5V       │  ← 给树莓派供电（可选）
│ Pin2: TX  (PA2)     │─────────────│ Pin10: RXD (GPIO15)│  ← 飞控发 → 树莓派收
│ Pin3: RX  (PA3)     │─────────────│ Pin8:  TXD (GPIO14)│  ← 树莓派发 → 飞控收
│ Pin4: GND           │─────────────│ Pin6:  GND        │  ← 共地！
└─────────────────────┘             └──────────────────┘

波特率: 115200bps
数据位: 8, 停止位: 1, 无校验
树莓派设备路径: /dev/serial0 (或 /dev/ttyAMA0)
```

> ⚠️ 飞控 USART2 是 **3.3V 电平**，可以直接连树莓派 GPIO（也是 3.3V）。不要用 5V 的 USB-TTL 模块直接连飞控 TELEM1，会烧 MCU。

### 1.2 MAVLink 在飞控内部怎么工作

ArduPilot 固件内置了完整的 MAVLink 协议栈，分成三层：

```
┌──────────────────────────────────────────────┐
│  应用层 (GCS_Mavlink.cpp)                     │
│  - 收到 MAV_CMD_DO_SET_SERVO → 调 SRV_Channels │
│  - 收到 MAV_CMD_NAV_WAYPOINT → 写入航点队列    │
│  - 定时发送 HEARTBEAT、GPS_RAW、ATTITUDE 等    │
│  - 消息 ID → handler 函数 的映射表             │
├──────────────────────────────────────────────┤
│  组帧/解帧层 (mavlink 库)                      │
│  - 收: 字节流 → STX检测 → 拼完整帧 → CRC校验   │
│  - 发: 消息结构体 → 序列化 → 二进制帧 → UART   │
│  - MAVLink v2: 起始标志 0xFD, 最大 280 字节/帧 │
├──────────────────────────────────────────────┤
│  硬件驱动层 (UART 驱动)                        │
│  - USART2 中断收字节 → DMA → ring buffer      │
│  - 发送: 阻塞或 DMA，逐字节推                  │
│  - 115200bps，全双工                           │
└──────────────────────────────────────────────┘
```

**关键认知**：
- MAVLink 解析在飞控里是**逐字节状态机**——收到一个字节就推进一次状态，不是等整帧收完再解析
- 这个过程在微秒级完成，不影响 200Hz 的姿态控制主循环
- ArduPilot 的 MAVLink 代码你不必改——它支持几乎所有标准指令

### 1.3 飞控收到指令后做什么

以 `MAV_CMD_DO_SET_SERVO`（消息 ID=183）为例：

```
MAVLink 二进制帧到达 USART2
        │
        ▼
[UART 中断] 收一个字节 → 写入 ring buffer
        │
        ▼
[主循环调用] GCS_MAVLINK::update() → 从 ring buffer 取字节
        │
        ▼
[mavlink_parse_char()] 逐字节喂入状态机:
  - 找 0xFD (STX) → 读长度 → 读消息ID → 读payload → 校验CRC
        │
        ▼
[CRC 通过] 根据 msgid=183 查到是 MAV_CMD_DO_SET_SERVO
        │
        ▼
[GCS_MAVLINK::handle_command_long()]
  → case MAV_CMD_DO_SET_SERVO:
  → SRV_Channels::set_output_pwm(servo_number=5, pwm=2000)
        │
        ▼
[TIM3_CH4] 硬件定时器输出 2000μs 脉宽的 PWM 信号
        │
        ▼
[PB1 引脚] → 投放舱舵机旋转 → 舱门打开
```

**项目相关的指令速查**：

| 你要做的事 | MAVLink 指令 | 飞控动作 | 不改固件？ |
|-----------|-------------|---------|:---:|
| 投放包裹（开舱门） | `MAV_CMD_DO_SET_SERVO` (183) | SERVO5 输出指定 PWM | ✅ |
| 投放包裹（关舱门） | `MAV_CMD_DO_SET_SERVO` (183) | SERVO5 输出另一 PWM 值 | ✅ |
| 弹降落伞 | `MAV_CMD_DO_PARACHUTE` (209) | CHUTE_SERVO_ON 触发 | ✅ (设参数) |
| 飞向指定坐标 | `MAV_CMD_NAV_WAYPOINT` (16) | 写航点→导航跟随 | ✅ |
| 立即降落 | `MAV_CMD_NAV_LAND` (21) | 切 Land 模式 | ✅ |
| 返航 | `MAV_CMD_NAV_RETURN_TO_LAUNCH` (20) | 切 RTL 模式 | ✅ |
| 切换飞行模式 | `MAV_CMD_DO_SET_MODE` (176) | 改 flight_mode | ✅ |
| 读取参数 | `MAV_CMD_PARAM_REQUEST_READ` | 返回参数值 | ✅ |

> **核心原则**：你们项目中所有对飞控的控制需求，ArduPilot 固件里全有对应的标准 MAVLink 指令，**一行固件代码都不用改**，服务器端用 pymavlink 发指令就行。

### 1.4 飞控的 MAVLink 串口资源

DM-FC01 有 6 个可用串口：

| 串口 | ArduPilot 编号 | 硬件 | 默认用途 | 本项目可改？ |
|------|:---:|------|----------|:---:|
| TELEM1 | SERIAL1 | USART2 | **数传（连接树莓派）** | ← 这就是主链路 |
| TELEM2 | SERIAL4 | USART3 | DJI O3 Air Unit | 可以改，如果不接 DJI |
| TELEM3 | SERIAL7 | UART4 | 辅助数传 | 备用 |
| TELEM4 | SERIAL8 | USART6 | 辅助数传 | 备用 |
| GPS1 | SERIAL3 | USART1 | GPS+罗盘 | 不要动 |
| DEBUG | SERIAL2 | UART8 | 控制台+SWD | 不要动 |

> 如果需要同时接两个 MAVLink 设备（比如树莓派 + 一个额外的通信模块），TELEM2/3/4 都可以配成 MAVLink 协议。

---

## 2. 通讯层 — 树莓派到服务器的链路

### 2.1 物理链路：树莓派 → 4G → 公网 → 服务器

```
[树莓派 3B]               [EC20 4G模块]           [基站]      [阿里云ECS]
    │                          │                    │              │
    │ USB                      │                    │              │
    ├──── USB 线 ──────────────┤                    │              │
    │                          │  4G LTE 空口       │   光纤骨干网  │
    │                          ├────────────────────┤──────────────┤
    │                          │  延迟 10-40ms       │  延迟 20-40ms│
    │                          │                    │              │
    │  树莓派 wwan0 网卡        │                    │  公网 IP      │
    │  运营商内网 IP (10.x.x.x) │                   │  8.152.207.82│
    │                          │                    │              │
    │  发送端:                 │                    │  接收端:      │
    │  mavproxy                │                    │  mavlink-    │
    │  读 /dev/serial0          │                    │  router      │
    │  → UDP → 8.152.207.82   │                    │  监听 :14550  │
    │      :14550              │                    │              │
```

**关键认知**：
- EC20 工作在 **QMI/PPP 拨号模式**，树莓派把它当成一块网卡（`wwan0`），不是串口
- 树莓派拿到的是**运营商内网 IP**（10.x.x.x 或 100.x.x.x），经过运营商 NAT 网关出公网
- 这意味着：服务器**不能主动连接**树莓派，只能树莓派先连服务器，建立连接后双向通信
- 所以树莓派端程序必须**主动发起 UDP 连接到服务器**，服务器在收到第一个包后就能回复了

### 2.2 EC20 模块的上网流程

```
树莓派启动
    │
    ▼
1. EC20 通过 USB 连接 → 内核识别为 /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyUSB2
    │  （一个AT口，一个数据口，一个GPS口）
    ▼
2. 发 AT 命令初始化:
   AT+CSQ           → 查信号强度（≥15 才算可用）
   AT+COPS?         → 查注册到哪个运营商
   AT+QCFG="usbnet" → 确认 USB 网卡模式
    │
    ▼
3. 拨号建立数据连接:
   方案A: pppd call quectel-ppp   → 拿到 ppp0 网卡 + IP
   方案B: qmicli + libqmi         → 拿到 wwan0 网卡 + IP (推荐)
    │
    ▼
4. ping 8.8.8.8 → 确认互联网通了
    │
    ▼
5. 启动 mavproxy:
   mavproxy.py --master=/dev/serial0 --out=8.152.207.82:14550
```

### 2.3 MAVLink 在通讯层的角色：透明转发

**通讯层的核心任务就一个：把 MAVLink 字节从串口搬到 UDP，再从 UDP 搬回串口。仅此而已。**

```
                  ┌── 树莓派 (mavproxy) ──┐
                  │                         │
飞控串口 ──→ 读字节 ──→ 不做任何解析 ──→ UDP 发出
飞控串口 ←── 写字节 ←── 不做任何解析 ←── UDP 收到
                  │                         │
                  └─────────────────────────┘
```

mavproxy **不解析 MAVLink 消息内容**——它只是：
- 从串口读到一堆字节 → 包成 UDP 包发走
- 从 UDP 收到一堆字节 → 通过串口发给飞控

这意味着通讯层同学不需要深入理解 MAVLink 的消息格式，只需要：
1. 保证串口参数正确（115200, 8N1）
2. 保证 UDP 链路通（IP 可达，端口对）
3. 保证延迟可控（4G 信号好，丢包率低）

### 2.4 服务端：mavlink-router 和 Mosquitto

```
                        阿里云 ECS (8.152.207.82)
                        ┌─────────────────────────────────────────┐
                        │                                         │
UDP :14550 ──→ mavlink-router ──→ 路由到多个端点:                   │
    ↑                    │         ├─ UDP :14551 (给 QGC 地面站)    │
    来自飞机              │         ├─ TCP :5760  (给 Flask API)     │
                        │         └─ 也可以转 MQTT                 │
                        │                                         │
                        │  Mosquitto (MQTT)                       │
                        │  ├─ topic: drone/+/telemetry  (上行数据) │
                        │  ├─ topic: drone/+/command    (下行指令) │
                        │  └─ topic: station/+/status   (换电站)   │
                        │                                         │
                        │  Flask API                              │
                        │  ├─ GET  /api/drone/status              │
                        │  ├─ POST /api/drone/drop   (投放)        │
                        │  ├─ POST /api/drone/rtl    (返航)        │
                        │  └─ POST /api/station/charge (充电)      │
                        │                                         │
                        └─────────────────────────────────────────┘
```

**服务内部的数据流**：

```
mavlink-router 收到 UDP 包
       │
       ├──→ 转发到 QGC (UDP :14551)     ← 地面站实时监控
       │
       ├──→ 转发到 Flask (TCP :5760)    ← Python 程序解析
       │      │
       │      └──→ pymavlink 解帧
       │             ├─ HEARTBEAT → 更新飞机在线状态
       │             ├─ GPS_RAW_INT → 存数据库 (lat, lon, alt)
       │             ├─ SYS_STATUS → 电池电压、电流
       │             └─ ATTITUDE → 姿态角 (网页展示用)
       │
       └──→ 可选: 桥接到 MQTT
              └─ 发布到 drone/{id}/telemetry → 其他服务订阅
```

---

## 3. 层间接口：飞机层 ↔ 通讯层

两层之间的边界**就是那条 UART 线**：

```
┌─────── 飞机层 ──────┐     ┌─────── 通讯层 ──────┐
│                      │     │                      │
│  DM-FC01 飞控        │     │  树莓派 3B            │
│  USART2 TX/RX        │◄═══►│  GPIO14/15            │
│  协议: MAVLink v2    │UART │  协议: 透明转发       │
│  波特率: 115200      │     │  mavproxy 进程        │
│  负责: 执行指令       │     │  负责: 搬运字节        │
│                      │     │                      │
└──────────────────────┘     └──────────────────────┘

接口约定:
- 物理: 3.3V UART, 交叉连接 (TX→RX, RX→TX)
- 协议: MAVLink v2, 115200 8N1
- 心跳: 飞控每秒发 HEARTBEAT, 树莓派不做任何处理直接转发
- 错误处理: 飞控端如果 TELEM1 5秒未收到心跳 → 触发 TELEM 失联 failsafe → RTL
```

**这条接口是两层各自独立开发测试的关键**：
- 飞机层同学可以用 USB 线直连电脑，QGC 能收到 MAVLink 数据 → 飞机层没问题
- 通讯层同学可以用两个 USB-TTL 模块做回环测试：A 发→B 收→UDP→服务器→UDP→B 发→A 收

---

## 4. 实操任务

### 飞机层任务

**任务 A1：用 USB 直连飞控，看 MAVLink 原始数据流**
1. DM-FC01 通过 USB-C 连电脑
2. 打开 QGC 或 Mission Planner，确认连接正常
3. 打开 MAVLink Inspector 窗口，看每条消息的原始字段
4. 找一下 `HEARTBEAT`、`GPS_RAW_INT`、`ATTITUDE`、`SYS_STATUS` 这几条消息
5. 拿起飞控动一动，看 `ATTITUDE.roll/pitch/yaw` 数值变化

**任务 A2：理解飞控的 UART 资源分配**
1. 连上 Mission Planner → 参数表
2. 查看 `SERIAL1_PROTOCOL`（应该是 2 = MAVLink2）
3. 查看 `SERIAL1_BAUD`（应该是 115）
4. 查看 `SERIAL3_PROTOCOL`（应该是 5 = GPS）
5. 画出你的飞控上每个串口现在分配给什么用途

**任务 A3：从代码层面理解一条 MAVLink 指令**
1. 克隆 ArduPilot 源码
2. 找到 `libraries/GCS_MAVLink/GCS_Common.cpp`
3. 搜索 `MAV_CMD_DO_SET_SERVO`，看它的处理代码
4. 搜索 `MAV_CMD_NAV_LAND`，看它怎么触发降落
5. 不用读懂全部，只需要知道"在这个文件的这个函数里"

### 通讯层任务

**任务 B1：树莓派串口回环测试**
1. 短接树莓派 GPIO14(TXD) 和 GPIO15(RXD)
2. 打开 `/dev/serial0`，写一段 Python 发 "Hello"，读回来
3. 确认收发一致

**任务 B2：EC20 拨号上网**
1. EC20 模块插树莓派 USB
2. `lsusb` 确认识别到了 Quectel 设备
3. `ls /dev/ttyUSB*` 看有几个串口
4. 用 `screen /dev/ttyUSB2 115200` 连接 AT 口，发 `AT` 确认回应 `OK`
5. 发 `AT+CSQ` 看信号强度
6. 配置 QMI 拨号，拿到 IP 地址
7. `ping 8.8.8.8` 确认互联网通

**任务 B3：端到端 MAVLink 链路打通**
1. 飞控 TELEM1 接树莓派 GPIO 串口
2. 树莓派用 EC20 4G 上网
3. 树莓派启动 mavproxy：
   ```bash
   mavproxy.py --master=/dev/serial0 --out=8.152.207.82:14550
   ```
4. 服务器端启动 mavlink-router：
   ```bash
   mavlink-routerd -e 8.152.207.82:14550 0.0.0.0:14550
   ```
5. 你本地电脑 QGC 连 `8.152.207.82:14551`（mavlink-router 转发端口）
6. 看 QGC 上能不能收到飞控的遥测数据
7. 从 QGC 发一个"切换到 Guided 模式"指令，看飞控能不能收到

**任务 B4：Python 发 MAVLink 指令**
1. 在服务器上用 pymavlink 写一个脚本：
   ```python
   from pymavlink import mavutil
   
   # 连上 mavlink-router
   conn = mavutil.mavlink_connection('tcp:localhost:5760')
   
   # 等心跳
   conn.wait_heartbeat()
   print("飞机在线！")
   
   # 发送投放指令
   conn.mav.command_long_send(
       conn.target_system,    # 目标系统 ID
       conn.target_component, # 目标组件 ID
       mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
       0,                     # confirmation
       5,                     # servo_number = AUX1/SERVO5
       2000,                  # PWM = 2000μs
       0, 0, 0, 0, 0         # 未使用的参数
   )
   print("投放指令已发送！")
   ```
2. 观察飞控上 SERVO5 输出是否变化（用示波器或舵机测试）

---

## 5. 经验预警

### 飞机层专属

| 坑 | 说明 | 教训 |
|----|------|------|
| 串口接反 | TX 接 TX，RX 接 RX → 两边都在发，谁都收不到 | **TX 一定接对方 RX，交叉连接** |
| 波特率不匹配 | 飞控 115200，树莓派 9600 → 乱码 | 两边参数必须完全一致: 115200,8,N,1 |
| 没共地 | 飞控和树莓派没连 GND → 电平没有参考 → 通信不稳 | **GND 必须连！** |
| TELEM1 被占用 | 别的进程占着 `/dev/serial0` → mavproxy 打不开 | 先 `lsof /dev/serial0` 检查 |
| USB 不供电 | 飞控 USB 插着，但 TELEM 口没电 | DM-FC01 的 5V/8.9V 输出必须接电池才有 |
| MAVLink v1 vs v2 | 飞控设的 MAVLink1，服务器发的 v2 消息 | `SERIAL1_PROTOCOL=2` 才是 MAVLink2 |

### 通讯层专属

| 坑 | 说明 | 教训 |
|----|------|------|
| 4G 天线没接就上电 | 功放发射没天线 → 能量反射 → 烧芯片，不可逆 | **任何时候 EC20 上电前先接天线** |
| USB 供电不足 | 树莓派 USB 只能供 1.2A，EC20 峰值要 2A | EC20 最好独立供电，或树莓派用 3A+ 电源 |
| 内网 IP 不能互访 | 两个 EC20 都是运营商内网 IP → 不能直接通信 | 所有通信必须经云服务器中转 |
| UDP 丢包 | 4G 信号差时 UDP 丢包率飙升 | MAVLink 有心跳+超时重传机制，但不保证可靠。关键指令（投放、弹伞）发了后等 ACK |
| 信号波动 | 飞行中 4G 信号随高度和距离剧烈变化 | 飞控 failsafe 必须配好，信号断了飞控自己 RTL |
| QGC 断连 | mavlink-router 没转发心跳 → QGC 5 秒判定断连 | mavlink-router 配 `-e` 端点必须正确 |
| Mosquitto 裸奔 | 公网 MQTT 无密码 → 任何人能订阅你的飞机数据 | 必须加用户名密码 + ACL |
| mavproxy 占用串口 | mavproxy 没关干净 → 重启后打不开串口 | `pkill mavproxy` 后再启 |

### 飞机层+通讯层联调专属

| 坑 | 说明 | 教训 |
|----|------|------|
| 两端都在改，不知道谁的问题 | 联调时飞控和树莓派同时在改 → 出 bug 不知道归谁 | **联调前各层先独立验证通过** |
| 没有测试桩 | 飞机层等通讯层，通讯层等飞机层 → 互相等 | 飞机层用 USB+QGC 独立测；通讯层用串口回环独立测 |
| 延迟误判 | 指令发出去 5 秒没反应 → 以为是链路断了 → 其实飞控在执行任务（比如返航需要先爬升） | 学会看 MAVLink 的 `COMMAND_ACK` 消息——它会告诉你指令是否被接受 |

---

## 附录：关键参数速查

### 飞控端参数 (ArduPilot)

| 参数 | 建议值 | 含义 |
|------|--------|------|
| `SERIAL1_PROTOCOL` | 2 | TELEM1 = MAVLink2 |
| `SERIAL1_BAUD` | 115 | 波特率 115200 |
| `SYSID_MYGCS` | 1 | 本机系统ID（飞控=1） |
| `FS_GCS_ENABLE` | 1 | 启用地面站失联保护 |
| `FS_LOST_TIMEOUT` | 5 | 5 秒无心跳 → RTL |
| `CHUTE_ENABLED` | 1 | 启用降落伞 |
| `CHUTE_SERVO_ON` | 6 | 降落伞释放用 SERVO6 |

### 树莓派端

```bash
# 查看串口是否正常
ls -la /dev/serial0              # 应该指向 ttyAMA0 或 ttyS0

# 检查是谁占着串口
lsof /dev/serial0

# 杀干净 mavproxy
pkill -9 -f mavproxy

# 测试串口回环 (短接 TX+RX 后)
python3 -c "
import serial
s = serial.Serial('/dev/serial0', 115200, timeout=1)
s.write(b'hello')
print(s.read(5))
"

# 查看 EC20 状态
lsusb | grep Quectel
dmesg | grep -i quectel
ifconfig wwan0
```

### 服务器端

```bash
# 启动 mavlink-router
mavlink-routerd \
  -e 127.0.0.1:14551 \     # 给本地 QGC 用
  -e 127.0.0.1:5760 \      # 给 Flask/pymavlink 用
  0.0.0.0:14550             # 监听从飞机来的 UDP

# 检查 Mosquitto 状态
systemctl status mosquitto
mosquitto_sub -v -t 'drone/#'   # 看所有飞机发来的消息

# 检查端口监听
ss -tlnp | grep -E '14550|14551|5760|1883'
```
