# MAVLink 收包系统 — 功能设计文档

> 从串口接收飞控 MAVLink 数据，分层解耦，模块化处理。
> 不含具体代码，只描述架构、模块职责、数据流、接口约定。

---

## 1. 整体架构

```
硬件层   飞控 TELEM1 ──3.3V TTL──→ USB-TTL ──→ 电脑 COM口
           │
           └── SITL ──UDP──→ 127.0.0.1:14551  （仿真调试用）

─────────────────────────────────────────────────────

软件层
           ┌──────────────────┐
           │   传输层           │  从 COM口 / UDP 读原始字节
           │   mavutil 封装     │  统一接口：connect() → connection 对象
           └────────┬─────────┘
                    │ bytes
                    ▼
           ┌──────────────────┐
           │   解析层           │  pymavlink 内部完成：
           │   recv_match()    │  找帧头 0xFD → 拼帧 → 验CRC → 返回消息对象
           └────────┬─────────┘
                    │ MAVLink message 对象
                    ▼
           ┌──────────────────┐
           │   队列 Queue      │  解耦收发：收包不阻塞，业务不丢包
           │   容量 ~200       │  线程安全
           └────────┬─────────┘
                    │ message
                    ▼
           ┌──────────────────┐
           │   分发层           │  msg_id → handler 字典查表
           │   dispatch()      │  未注册的消息 → 忽略 + 日志
           └───┬───┬───┬──────┘
               │   │   │
      ┌────────┘   │   └────────┐
      ▼            ▼            ▼
  ┌────────┐ ┌──────────┐ ┌──────────┐
  │ 心跳    │ │ 状态收集  │ │ 指令ACK  │
  │ 监控    │ │ 模块      │ │ 追踪     │
  └────────┘ └──────────┘ └──────────┘
```

---

## 2. 传输层

### 职责
屏蔽底层传输方式差异，上层不关心是串口还是 UDP。

### 支持两种输入

| 模式 | 场景 | 连接参数 |
|------|------|----------|
| 串口模式 | 真飞控 TELEM1 通过 USB-TTL 连接 | `COM3, 115200` |
| UDP 模式 | SITL 仿真，飞控发到 14551 | `udp:127.0.0.1:14551` |

### 接口约定
- 对外暴露一个 **connection 对象**（pymavlink 的 `mavutil.mavlink_connection()` 返回值）
- 调用方只需 `conn.recv_match()`，不管底层是串口还是 UDP
- 波特率默认 115200（ArduPilot TELEM1 标准速率）

---

## 3. 解析层

### 职责
从连续字节流中切出完整的、校验通过的 MAVLink 消息。

### 处理的三种情况

| 情况 | 说明 | 处理 |
|------|------|------|
| 正常帧 | 完整一帧，CRC 通过 | 返回消息对象 |
| 半包/粘包 | 帧跨两次 recv / 一包多帧 | pymavlink 内部缓冲区自动拼接拆解 |
| 坏包 | CRC 失败 / 垃圾字节 | pymavlink 返回 `BAD_DATA`，外层丢弃 |

### 接口约定
- `recv_match(blocking=False)` 非阻塞轮询
- 返回 `None` 表示当前无消息
- 返回消息对象（`msg.get_type()` 可获取类型名）
- BAD_DATA 由外层 `if msg_type != 'BAD_DATA'` 过滤

---

## 4. 分发层

### 职责
根据 `msg_id` 将消息路由到对应的处理模块。

### 路由表设计

| msg_id | 消息类型 | 路由目标 |
|:------:|----------|----------|
| 0 | HEARTBEAT | 心跳监控模块 |
| 1 | SYS_STATUS | 状态收集模块 |
| 24 | GPS_RAW_INT | 状态收集模块 |
| 30 | ATTITUDE | 状态收集模块 |
| 33 | GLOBAL_POSITION_INT | 状态收集模块 |
| 74 | VFR_HUD | 状态收集模块 |
| 77 | COMMAND_ACK | 指令ACK追踪模块 |
| 253 | STATUSTEXT | 状态收集模块 |
| 其他 | — | 忽略（计数 + 可选日志） |

### 路由方式
- 字典映射：`msg_id → handler_function`
- 每条消息调用一次对应 handler
- 未注册的消息不打日志（避免刷屏），只计总数

---

## 5. 模块一：心跳监控与断联检测

### 输入
`HEARTBEAT`（msg_id=0），飞控每秒发一次。

### 处理逻辑

**每次收到 HEARTBEAT 时：**
- 记录当前时间戳 `last_heartbeat_time`
- 提取飞控状态：`system_status`、`base_mode`
- 如果状态变化（如从 STANDBY → ACTIVE），输出状态切换日志

**看门狗检查（独立线程，每秒一次）：**
- 计算 `now - last_heartbeat_time`
- 超过阈值（如 3 秒）→ **飞控失联告警**
- 恢复收到心跳 → 清除告警，输出恢复日志

### 状态定义参考

| system_status | 含义 |
|:---:|------|
| 0 | 未初始化 |
| 3 | 待命 (STANDBY) |
| 4 | 已激活 (ACTIVE) |

### 输出
- 控制台实时日志（连接/断开/状态切换）
- 心跳时间戳供看门狗线程读取（需线程安全）

---

## 6. 模块二：状态收集

### 输入
`ATTITUDE`、`GLOBAL_POSITION_INT`、`GPS_RAW_INT`、`VFR_HUD`、`SYS_STATUS`、`STATUSTEXT`

### 处理逻辑

**每条消息：**
- 提取关键字段，组装成结构化的状态快照
- 写入本地文件（CSV 或 JSON Lines）
- 可选：定期打印摘要到控制台（每 N 秒一次）

**各消息提取的字段：**

| 消息 | 提取字段 |
|------|----------|
| ATTITUDE | roll, pitch, yaw（弧度转度） |
| GLOBAL_POSITION_INT | lat/1e7, lon/1e7, alt/1e3（经纬度+高度） |
| GPS_RAW_INT | lat, lon, satellites_visible |
| VFR_HUD | airspeed, groundspeed, alt, throttle |
| SYS_STATUS | voltage_battery, current_battery, battery_remaining |
| STATUSTEXT | text（飞控文字消息，如 "EKF2 active"） |

### 输出
- 本地日志文件（按日期命名，如 `logs/status_20260708.csv`）
- 可选：控制台定期摘要 `[状态] 高度=584m 电池=12.3V 星数=12`

---

## 7. 模块三：指令 ACK 追踪

### 输入
`COMMAND_ACK`（msg_id=77），飞控执行完指令后返回。

### 处理逻辑

**每条 COMMAND_ACK：**
- 提取 `command`（哪个指令）、`result`（结果码）
- 与已发出的指令记录做匹配（通过指令编号 / 时间窗口）
- 记录执行结果（成功 / 失败 / 超时）

### 结果码参考

| result | 含义 |
|:------:|------|
| 0 | MAV_RESULT_ACCEPTED（成功） |
| 1 | MAV_RESULT_TEMPORARILY_REJECTED |
| 4 | MAV_RESULT_UNSUPPORTED |

### 输出
- 指令执行结果日志：`[ACK] MAV_CMD_TAKEOFF → ACCEPTED`
- 失败时突出告警：`[ACK] MAV_CMD_DO_SET_SERVO → FAILED (result=1)`

---

## 8. 线程模型

### 线程分配

| 线程 | 职责 | 频率 |
|------|------|------|
| 收包线程（主线程） | `recv_match` → `queue.put(msg)` | 持续循环，不阻塞 |
| 处理线程 | `queue.get(msg)` → `dispatch(msg)` → 各模块处理 | 持续循环 |
| 看门狗线程 | 检查 `last_heartbeat_time`，超时告警 | 每秒一次 |

### 线程间通信
- 收包 → 处理：`queue.Queue`（线程安全，容量 200）
- 心跳时间戳：`threading.Lock` 保护或 `threading.Event`
- 各模块间互不通信，各自独立

---

## 9. 文件输出

### 输出文件

| 文件 | 格式 | 内容 |
|------|------|------|
| `logs/status_YYYYMMDD.csv` | CSV | 状态类消息字段（时间 + 姿态 + GPS + 电池） |
| `logs/messages_YYYYMMDD.jsonl` | JSON Lines | 所有消息完整记录（原始字段全集） |
| `logs/events_YYYYMMDD.log` | 纯文本 | 连接/断联/告警/ACK 等事件日志 |

### 文件管理
- 按日期自动切分（跨天新建文件）
- 日志目录可配置
- 旧文件不做自动删除（手动清理）

---

## 10. 待扩展功能（后续迭代）

| 功能 | 说明 |
|------|------|
| 下行注入 | 从云端收到指令 → 写入 `conn.write()` 发给飞控 |
| 云端转发 | 收集到的状态 → 打包 JSON → HTTP/MQTT 发往阿里云 |
| 指令发送队列 | 发指令 → 等 ACK → 超时重发 → 标记完成/失败 |
| Web 仪表盘 | 本地起 Flask，浏览器实时看飞控状态 |
| 数据回放 | 读取日志文件，按时间轴回放飞行轨迹 |

---

## 11. 文件结构规划

```
server/
├── mavlink_receiver.py      # 主入口：启动各线程，连接飞控
├── transport.py             # 传输层：串口/UDP 连接工厂
├── dispatch.py              # 分发层：msg_id → handler 路由表
├── heartbeat_watchdog.py    # 模块一：心跳监控 + 断联检测
├── status_collector.py      # 模块二：状态收集 + 写文件
├── command_tracker.py       # 模块三：指令 ACK 追踪
├── logger.py                # 通用日志工具（文件轮转、格式化）
├── config.py                # 配置项（端口、波特率、超时阈值、日志路径）
└── logs/                    # 运行时生成的日志目录
```
