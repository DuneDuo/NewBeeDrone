拼积木中……

我草safety模块这么贵，吓哭了

| 阶段 | 要完成的东西 | 当前状态 | 进度 |
|---|---|---|---|
| ① 理解整体能力边界 | 飞控、Server、Command、Mission、Security 分别负责什么 | 已完成 | `██████████ 100%` |
| ② 确认 Command 原子操作 | `arm / disarm / takeoff / land / rtl / hold / set_mode / cancel / goto`，区分已实现、待实现、建议新增 | 基本完成 | `█████████░ 90%` |
| ③ 理解 MAVLink Mission Protocol | 明确它是任务列表上传/管理协议，与业务 Mission、`goto` 的关系 | 已完成 | `██████████ 100%` |
| ④ 明确 Mission 的定位 | 对业务层提供简单接口，内部组合 Command + Mission Protocol | 已完成概念设计 | `████████░░ 80%` |
| ⑤ 明确 Security 的定位 | 独立线程循环检查遥测；异常时抢占 Command，再发 `hold/rtl/land` 等 | 已完成概念设计 | `████████░░ 80%` |
| ⑥ 确认 Security 检查项 | 电量、心跳、GPS、飞行状态、任务超时等具体规则 | 尚未定 | `███░░░░░░░ 30%` |
| ⑦ 设计 Mission 状态机 | 配送任务有哪些状态、状态之间怎么转移 | 还没正式画 | `██░░░░░░░░ 20%` |
| ⑧ 设计 Security 状态/策略 | 什么异常对应 Warning / Hold / RTL / Land | 还没正式定 | `██░░░░░░░░ 20%` |
| ⑨ 确定 Mission API | 例如 `start / pause / resume / cancel / status` 等 | 尚未定接口 | `█░░░░░░░░░ 10%` |
| ⑩ 确定 Security API/线程逻辑 | `start / stop / check / trigger`，以及如何清当前 Command | 尚未定接口 | `█░░░░░░░░░ 10%` |
| ⑪ 出文件结构 | `mission/`、`security/` 各有哪些 `.py` 文件 | 尚未正式确定 | `█░░░░░░░░░ 10%` |
| ⑫ 写各文件职责 | 每个文件负责什么、依赖谁、禁止做什么 | 尚未开始 | `░░░░░░░░░░ 0%` |

//9.12 21：20

