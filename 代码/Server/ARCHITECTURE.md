# Server 代码架构

```
python run.py 一个进程

  ┌─ mavlink/ (包1) ────────────────────────────────┐
  │  MAVLink 收发接口层                              │
  │  drone.py      TCP监听, 收包, 三线程(收/发/狗)    │
  │  dispatch.py   消息路由 (msg_type → handler)      │
  │  handlers.py   消息处理 (更新属性, 写数据库)       │
  │  config.py     端口, ID, 超时                     │
  │  logger.py     日志工具                           │
  │  对外: Drone.registry, .send_command_long()       │
  └──────────────────────────────────────────────────┘
                          ↑ import
  ┌─ mission/ (包2) ────────────────────────────────┐
  │  任务执行层                                      │
  │  任务状态机, 拆指令, ACK 跟踪, 失败 → RTL        │
  │  Depends on: mavlink/                            │
  └──────────────────────────────────────────────────┘
                          ↑ import
  ┌─ web/ (包3) ────────────────────────────────────┐
  │  Web API + 前端                                  │
  │  api.py         Flask 路由 + WebSocket 推送      │
  │  templates/     前端 HTML/JS                     │
  │  Depends on: mission/                            │
  └──────────────────────────────────────────────────┘

  视频: subprocess.Popen(["mediamtx"])
        Pi RTSP → 浏览器 WebRTC, 独立进程
```

## 三层职责

| 层 | 做什么 | 不做什么 |
|----|--------|---------|
| **mavlink** | 收发 MAVLink 原语 | 不知道"该发什么" |
| **mission** | "送货 A→B" 拆成指令序列, 状态机推进 | 不知道 MAVLink 怎么写 |
| **web** | HTTP/WebSocket, 推状态给前端 | 不懂飞控逻辑 |

## 数据流

```
飞控 ──TCP──→ mavlink/drone.receive_loop
                ├─→ dispatch → handler → 实例属性 (实时查询)
                │           │         └─→ SQLite (历史查询)
                │           └─→ mission 状态机 (ACK 推进)
                └─→ (heartbeat_loop 回发心跳)

浏览器 ──HTTP──→ web/api.py
                  ├─→ mission (启动任务)
                  └─→ mavlink (查 registry)
```

## 线程模型 (每架飞机 3 线程, daemon)

```
receive_loop    ← 收 MAVLink 包
heartbeat_loop  ← 1Hz 回发心跳
watch_dog       ← 超时检测, 3s 无心跳 → close()
```

## 扩展点

- `mavlink/handlers.py` 注册新消息类型
- `mission/` 加新任务类型 (送货 / 巡检 / 返航)
- `web/` 加新 API 端点 / 前端页面
