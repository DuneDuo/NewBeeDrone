# Pi 代码架构 — 树莓派多线程任务

```
树莓派 3B
  │
  ├── USB/UART ──→ 飞控 (MAVLink)
  │
  ├── EC20 4G ──→ 云服务器 (8.152.207.82)
  │
  └── CSI 摄像头 → 视频流 + ArUco

  ┌────────────────────────────────────────────┐
  │  Python 进程 (main.py)                      │
  │                                             │
  │  ┌─ relay/ (模块1) ──────────────────────┐  │
  │  │  MAVLink 双向转发                       │  │
  │  │  transport.py  建连(FC/Server)          │  │
  │  │  main.py       收包→转发循环            │  │
  │  │  已完成                                  │  │
  │  └────────────────────────────────────────┘  │
  │                                             │
  │  ┌─ cv/ (模块2) ─────────────────────────┐  │
  │  │  ArUco 视觉定位 (馨淼)                  │  │
  │  │  OpenCV 识别降落点 ArUco 码             │  │
  │  │  计算位置偏移                           │  │
  │  │  通过 FC 的 MAVLink 发修正指令           │  │
  │  │  待写                                    │  │
  │  └────────────────────────────────────────┘  │
  │                                             │
  └────────────────────────────────────────────┘

  ┌─ video/ (模块3) ──────────────────────────┐
  │  视频推流                                   │
  │  已有: rtsp-server.py (树莓派成品预装)       │
  │  摄像头 → RTSP → 服务器 MediaMTX → 浏览器    │
  │  基本不需要改                                │
  └─────────────────────────────────────────────┘
```

## 三个模块

| 模块 | 做什么 | 状态 |
|------|--------|:---:|
| **relay** | 飞控 ↔ 云服务器 MAVLink 双向转发 | ✅ |
| **cv** | ArUco 码定位，位置修正指令发飞控 | 馨淼写 |
| **video** | 摄像头 RTSP 推流到服务器 | ✅ 已有 |

## 数据流

```
飞控 ──串口──→ relay ──TLS──→ 云服务器
                   ↑                │
                   │                │ 下行指令
                   └──←── TCP ──────┘

摄像头 ──→ video ──RTSP──→ 服务器 mediaMTX → 浏览器

摄像头 ──→ cv ──→ 算偏移 → 调 relay的FC连接发SET_POSITION
```

## 跨模块接口

cv 模块依赖 relay 提供的飞控 MAVLink 连接：

```
relay: fc_conn = open_connection("fc")   ← 这个对象暴露给 cv
cv:    fc_conn.mav.set_position_target_global_int_encode(...)
```

## 当前目录

```
Pi/
  relay/
    transport.py    建连 FC/Server
    main.py         双向转发主循环 (当前入口)
    config.py       ID、端口、超时
    logger.py       日志
  cv/
    __init__.py     (待写)
  video/
    rtsp-server.py  (预装成品，一行启动)
```

## 馨淼的 cv 模块需要什么

1. 从 relay 拿到 `fc_conn` (MAVLink 连接到飞控)
2. OpenCV 读取 CSI 摄像头画面
3. 检测 ArUco 码，计算相对于降落点的偏移 (x, y, z)
4. 通过 `fc_conn` 发送 `SET_POSITION_TARGET_GLOBAL_INT` 修正飞控位置
5. 降落阶段独立线程运行，不影响 relay 转发

需要: OpenCV, ArUco 码物理尺寸, 摄像头内参 (标定一次)
