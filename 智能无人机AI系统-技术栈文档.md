# 智能无人机 AI 系统 — 技术栈文档

> 纯代码实现 + 3D 仿真验证 | 不涉及硬件 | 半个月交付
>
> 场景：抢险救灾 — 无人机自动搜索目标 → AI 识别判断 → 自主决策飞行

---

## 1. 系统总架构

```
┌─────────────────── 仿真层 (SITL + 3D) ───────────────────┐
│                                                            │
│  Gazebo/FlightGear ←→ ArduPilot SITL                       │
│       │                    │                               │
│       │ 飞机姿态            │ MAVLink (UDP 14550/14551)     │
│       ▼                    ▼                               │
│  ┌─────────────────────────────────────┐                  │
│  │        地面控制端 (全部代码)          │                  │
│  │                                     │                  │
│  │  MAVLink 通信  ←→  AI 决策  ←→  YOLO 视觉             │
│  │       │               │              │                  │
│  │       └─────── 全部在本地运行 ───────┘                  │
│  └─────────────────────────────────────┘                  │
│                                                            │
│  3D 场景提供视觉输入（仿真画面截图 → YOLO）                   │
└────────────────────────────────────────────────────────────┘
```

### 核心原则

- **零硬件**：飞控用 SITL 仿真，视觉用 3D 仿真相机或测试图片
- **纯 Python**：全链路一种语言
- **本地运行**：不依赖云服务器，开发阶段全部跑在本机
- **可迁移**：后期接真飞机只需把 UDP 换成串口，架构不变

---

## 2. 子系统及技术栈

### 2.1 飞控仿真

| 组件 | 技术 | 说明 |
|------|------|------|
| 飞控固件 | ArduPilot SITL | WSL 中运行，代码和真飞控完全一致 |
| 通信协议 | MAVLink v2 | 无人机领域标准协议 |
| 3D 场景 | FlightGear | 轻量，原生支持，提供物理环境 + 视角画面 |
| 备选 | Gazebo Classic 11 | 功能更强，支持 Camera Plugin |
| 地面站 | QGroundControl | 监控飞机状态，验证飞行效果 |

**仿真相机方案**：抓取 FlightGear/Gazebo 窗口截图，作为 YOLO 的视觉输入。后期换真实摄像头只需改图像来源，检测和决策层不动。

### 2.2 MAVLink 通信

| 组件 | 技术 | 说明 |
|------|------|------|
| 协议 | MAVLink v2 | 无人机主流通信协议，飞控默认格式 |
| Python 库 | `pymavlink` | 封装了帧解析、CRC 校验、消息字典 |
| 收包 | `mavutil.mavlink_connection()` | 连接飞控，阻塞/非阻塞接收消息 |
| 发包 | `conn.mav.command_long_send()` | 下发飞行指令到飞控 |
| 仿真传输 | UDP `127.0.0.1:14550` | 默认地面站端口 |
| 额外输出 | UDP `127.0.0.1:14551` | 我们的程序监听端口，和 QGC 并行 |

**MAVLink 通信系统独立为底层模块**，负责：
- 收包解析：HEARTBEAT / ATTITUDE / GPS / SYS_STATUS 等消息
- 指令下发：MAV_CMD_NAV_* 系列飞行指令
- 心跳监控：断联检测 + 看门狗告警
- 状态收集：飞机实时姿态、位置、电池等汇总

### 2.3 视觉检测

| 组件 | 技术 | 说明 |
|------|------|------|
| 检测框架 | **Ultralytics YOLO** | `pip install ultralytics` 一行命令 |
| 模型 | **YOLO11n** (nano) | 5.4 MB，CPU 推理 ~30ms/帧 |
| 图像处理 | OpenCV + Pillow | 截图、缩放、格式转换 |
| 输入源 | 仿真截图 / 图片文件 / 后期接摄像头 | 接口统一，来源可插拔 |
| 预训练权重 | COCO 官方权重 | 80 类通用目标，人/车可直接用 |
| 微调 | 可选 | 火灾 / 烟雾 / 废墟 ~200 张标注即可 |

### 2.4 大模型 AI 决策

| 组件 | 技术 | 说明 |
|------|------|------|
| 模型 | **通义千问 API** 或 **DeepSeek API** | 国内访问快，中文能力强，有免费额度 |
| 备选 | **Ollama 本地部署** Qwen2.5-7B | 离线可用，需 GPU |
| 调用方式 | HTTP POST（openai SDK 兼容接口） | 标准格式，换模型只需改 URL 和 Key |
| 输入 | 检测结果 JSON + 飞机状态 + 任务上下文 | 拼接为自然语言 prompt |
| 输出 | 结构化决策 JSON | 固定格式，包含动作类型、理由、目标 |

### 2.5 消息与线程

| 组件 | 技术 | 说明 |
|------|------|------|
| 内部通信 | Python `queue.Queue` | 收包线程 → 处理线程解耦 |
| 日志 | Python `logging` | 控制台 + 文件双输出，带时间戳和模块名 |
| 指令集 | MAV_CMD 子集 | 5-10 种救灾常用指令即可 |

---

## 3. 代码架构

```
drone_ai/                         # 项目根目录
├── server/                        # 底层：MAVLink 通信系统
│   ├── main.py                    # 通信系统入口
│   ├── config.py                  # 全局配置
│   ├── logger.py                  # 日志模块
│   ├── transport.py               # 连接层（UDP/串口）
│   ├── dispatch.py                # 消息路由（msg_id→handler）
│   ├── heartbeat_watchdog.py      # 心跳监控 + 断联检测
│   ├── status_collector.py        # 状态收集（姿态/GPS/电池）
│   ├── command_tracker.py         # 指令 ACK 追踪
│   └── logs/                      # 日志输出目录
│
├── vision/                        # 中层：视觉检测
│   ├── detector.py                # YOLO 加载 + 推理
│   ├── image_source.py            # 图像来源（截图/文件/摄像头）
│   └── detection_logger.py        # 检测结果记录
│
├── ai_control/                    # 上层：AI 决策
│   ├── decider.py                 # 大模型调用 + 决策生成
│   ├── commander.py               # 决策 → MAVLink 指令翻译
│   ├── prompts.py                 # 提示词模板
│   └── mission_context.py         # 任务上下文（阶段/目标列表）
│
├── orchestrator.py                # 顶层：编排启动，主循环
└── requirements.txt               # 依赖清单
```

### 模块依赖

```
orchestrator.py          ← 总入口
    │
    ├── server/          ← MAVLink 通信（底层基础设施）
    │
    ├── vision/          ← 视觉检测（独立模块）
    │
    └── ai_control/      ← AI 决策（独立模块）
```

三个子系统各自独立，通过 `orchestrator` 串联。

---

## 4. 数据流

```
循环（每秒一次）：

  3D 仿真截图 ──→ vision/detector.py ──→ 检测结果[]
        │         "发现 2 人，置信度 0.92"
        │
        ▼
  server/status_collector.py ──→ 飞机状态
        │         "高度=50m, 模式=悬停, 电池=70%"
        │
  两个信息汇总
        │
        ▼
  ai_control/decider.py ──→ 大模型推理
        │         "优先救援最近的被困者，下降至 30m 确认"
        │
        ▼
  ai_control/commander.py ──→ 映射为 MAVLink 指令
        │         MAV_CMD_NAV_LOITER_TIME
        │
        ▼
  SITL 飞控执行 ──→ 3D 场景更新 ──→ 下一轮循环
```

---

## 5. 依赖清单

### Python 包

```
# requirements.txt

# === MAVLink 通信 ===
pymavlink>=2.4

# === 视觉检测 ===
ultralytics>=8.3            # YOLO11
opencv-python>=4.8          # 图像处理
Pillow>=10.0                # 图像读写

# === AI 决策 ===
openai>=1.0                 # 通义千问 / DeepSeek 兼容接口
requests>=2.31              # HTTP 调用

# === 仿真交互 ===
mss>=9.0                    # 屏幕截图（抓 3D 窗口）

# === 数据处理 ===
numpy>=1.24                 # YOLO 依赖
```

### 系统依赖

| 工具 | 用途 |
|------|------|
| ArduPilot SITL (WSL) | 飞控仿真 |
| FlightGear / Gazebo (WSL) | 3D 场景 |
| QGroundControl (Windows) | 地面站监控 |

---

## 6. 关键技术点

### 6.1 仿真图像获取方案

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **A: mss 截图** | 抓取 FlightGear/QGC 窗口 | 最简单，3 行代码 | 截图区域需固定 |
| B: Gazebo Camera Plugin | 场景内置虚拟摄像头 | 真实相机视角 | 需写 .world 配置文件 |
| C: 测试图片集 | 预拍场景图片循环输入 | 不依赖仿真渲染 | 不实时 |

**推荐先用方案 A**，跑通流程后换 B。

### 6.2 YOLO 检测目标

从 COCO 80 类中筛选救灾相关：

| 类别 | COCO ID | 预训练 |
|------|:---:|:---:|
| person | 0 | ✅ |
| car | 2 | ✅ |
| truck | 7 | ✅ |
| fire | — | ❌ 需微调 |
| smoke | — | ❌ 需微调 |

先用 COCO 预训练权重跑通，火/烟后期标注 ~200 张图微调。

### 6.3 大模型 Prompt 设计

```text
# 系统提示词（设定角色）
你是一架救援无人机的飞行指挥官。你收到的输入是：

1. 检测结果：YOLO 发现的目标列表（类别、位置、置信度）
2. 飞机状态：当前高度、位置、飞行模式、电池电量
3. 任务目标：搜索并标记被困人员位置

请输出严格 JSON 格式的决策：
{
  "action": "hover|move|descend|return",
  "reason": "简短理由",
  "target": {"lat": 0, "lon": 0} 或 null
}
```

### 6.4 决策到 MAVLink 指令映射

| AI 决策 | MAVLink 指令 | 说明 |
|------|------|------|
| hover | `MAV_CMD_NAV_LOITER_TIME` | 悬停指定秒数 |
| descend | `MAV_CMD_NAV_TAKEOFF` | 负高度下降 |
| move | `MAV_CMD_NAV_WAYPOINT` | 飞向目标坐标 |
| return | `MAV_CMD_NAV_RETURN_TO_LAUNCH` | 返航 |
| 拍照 | `MAV_CMD_IMAGE_START_CAPTURE` | 触发拍照 |
| 空投 | `MAV_CMD_DO_SET_SERVO` | 舵机投放 |

---

## 7. 开发路线（14 天）

### 第 1 阶段：底层通信 + 视觉（3 天）

| 天 | 任务 | 验证标准 |
|:--:|------|------|
| 1 | 搭建 MAVLink 通信框架（transport + dispatch + logger） | 收到 SITL 心跳，打印消息类型 |
| 2 | 安装 YOLO，写 `vision/detector.py` | 能加载 YOLO11n，对图片推理 |
| 3 | 抓仿真截图 → YOLO 检测 → 输出结果 | 截仿真画面，打印检测出的目标 |

### 第 2 阶段：AI 决策（4 天）

| 天 | 任务 | 验证标准 |
|:--:|------|------|
| 4 | 申请大模型 API Key，跑通 HTTP 调用 | 发送 prompt，收到结构化回复 |
| 5 | 写 `prompts.py`，设计救灾场景提示词 | 模型回复格式符合预期 JSON |
| 6 | 写 `decider.py` + `commander.py` | 检测结果 → 大模型 → 决策 MAVLink 指令 |
| 7 | 假数据模拟 → 发指令 → SITL 响应 | SITL 飞机执行 AI 生成的动作 |

### 第 3 阶段：全链路联调（4 天）

| 天 | 任务 | 验证标准 |
|:--:|------|------|
| 8 | 写 `orchestrator.py` 串联三子系统 | 循环跑通：截图→检测→决策→指令 |
| 9 | SITL + 3D 场景全链路测试 | 飞机自动响应视觉检测结果 |
| 10 | 救灾场景模拟（放置虚拟目标） | 系统自动识别并行动 |
| 11 | 边界情况：无目标、多目标、指令失败 | 异常场景不崩溃 |

### 第 4 阶段：收尾（3 天）

| 天 | 任务 | 验证标准 |
|:--:|------|------|
| 12 | 日志完善，记录每次决策链路 | 事后可回溯 |
| 13 | 整理演示脚本 + 使用说明 | 一键启动，可演示 |
| 14 | 演练，修 bug | 完整流程跑 3 遍不出错 |

---

## 8. 不引入的技术及原因

| 不引入 | 原因 |
|--------|------|
| ROS / ROS2 | 学习曲线陡，MAVLink 满足数据通信需求 |
| Docker | 本地开发不需要，部署时再说 |
| LangChain | 大模型调用链简单，手写 prompt 更可控 |
| GPU 训练 | YOLO 预训练权重够用，CPU 推理可达 |
| 边缘计算板 | 纯仿真阶段不需要，后期再考虑部署 |
| Web 前端 | 控制台日志 + QGC 地面站已满足监控需求 |

---

## 9. 启动顺序

```bash
# 1. 启动飞控仿真 (WSL)
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map --out udp:127.0.0.1:14551

# 2. 启动 3D 场景 (WSL，可选)
flightgear

# 3. 启动 QGC 地面站 (Windows)
# 双击 QGroundControl，自动连 14550

# 4. 启动 AI 系统 (Windows)
cd drone_ai
python orchestrator.py
```

---

## 10. 关键接口约定

### vision/detector.py

```python
def load_model(weights: str = "yolo11n.pt") -> YOLOModel:
    """加载 YOLO 模型"""

def detect(model, image: np.ndarray) -> list[dict]:
    """
    输入：BGR 图像 (numpy array)
    输出：[{"class": "person", "confidence": 0.92, "bbox": [x1,y1,x2,y2]}, ...]
    """
```

### ai_control/decider.py

```python
def decide(
    detections: list[dict],
    aircraft_state: dict,
    mission_context: dict
) -> dict:
    """
    输出：{"action": "hover", "reason": "...", "target": {...}}
    """
```

### ai_control/commander.py

```python
def execute_decision(decision: dict, mav_conn) -> dict:
    """决策 → MAVLink 指令 → 返回执行结果 {success: bool, result_code: int}"""
```
