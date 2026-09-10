# commands.json 命令定义表 —— 书写格式说明

`commands.json` 是命令层的唯一数据源。`command/commandspec.py` 的 `loadspec()` 读它，
每行转成一个 `CommandSpec`，再由 `CommandManager._bind()` 转成可调用的方法
（如 `drone.cmd.takeoff(10)`）。

> **为什么格式说明不写在 JSON 里**：标准 JSON 不支持注释，`json.load` 遇到 `//` 会解析失败。
> 所以 `commands.json` 里保持纯 JSON，书写格式统一写在本文件。

## 一、整体结构

```json
{
  "命令名": { "字段": "值", ... },
  ...
}
```

**命令名三合一**：JSON 的 key = 生成的方法名 = 台账里记录的 name。
比如 `"takeoff"` → 生成 `drone.cmd.takeoff(...)`，日志/台账里也记 `takeoff`。

## 二、字段一览

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|:---:|------|------|
| `cmd` | 字符串 | ✅ | — | MAV_CMD 名，如 `"MAV_CMD_NAV_TAKEOFF"`，加载时 `getattr(common, 名)` 转成数字 |
| `signature` | 字符串数组 | ❌ | `[]` | 位置参数名，如 `["alt"]`。决定 `takeoff(10)` 里 `10` 的名字叫 `alt` |
| `params` | 对象 | ❌ | `{}` | 参数模板，`{槽位(1~7): 值}`。值=字符串时从实参取，值=数字时是字面量 |
| `from` | 字符串 | ❌ | `"long"` | `"long"`→`send_command_long`，`"int"`→`send_command_int` |
| `idempotent` | 布尔 | ❌ | `false` | `true`=可安全重发；`false`=重发有风险，**必须写 `effect`** |
| `completion` | 字符串 | ❌ | `"on_ack"` | 完成判据模式：`on_ack` / `on_telemetry` / `on_final_ack` |
| `effect` | 谓词 | 条件 | — | `idempotent=false` 时必写：重发前「读回」是否已生效 |
| `complete` | 谓词 | 条件 | — | `completion=on_telemetry` 时必写：遥测达到什么状态算完成 |
| `timeout` | 数字 | ❌ | `5.0` | 完成超时（秒） |
| `max_retry` | 整数 | ❌ | `3` | 重试上限 |

## 三、谓词语法（effect / complete）

谓词判断飞机状态，可选的四个字段（对应 `flightstate.py` 里的四个状态轴）：

| 字段 | 含义 | 取值 |
|------|------|------|
| `mode` | 飞行模式 | manual / altctl / posctl / auto / acro / offboard / stabilized / rattitude_legacy / simple / termination / altitude_cruise / ready / takeoff / loiter / mission / rtl / land / follow_target / precland / vtol_takeoff / external1~8 |
| `armed` | 是否武装 | true / false |
| `landed_state` | 着地状态 | undefined / on_ground / in_air / takeoff / landing |
| `system_status` | 系统状态 | uninit / boot / calibrating / standby / active / critical / emergency / poweroff / flight_termination |

谓词写法：

```json
{ "mode": "loiter" }                                        // 相等（取一）
{ "mode": ["takeoff", "loiter"] }                           // 在列表中即可（或）
{ "and": [ {"mode": "loiter"}, {"armed": true} ] }          // 且
{ "or":  [ {"mode": "takeoff"}, {"mode": "loiter"} ] }      // 或
{ "check": "armed" }                                        // 具名谓词（command/checks.py 里的函数）
```

`and` / `or` 里还能再嵌套 `and` / `or`，任意组合。

## 四、完整样例（对照 commands.json）

### 1. arm —— 最简单：幂等 + 等 ACK

```json
"arm": {
    "cmd": "MAV_CMD_COMPONENT_ARM_DISARM",
    "params": { "1": 1 },
    "idempotent": true,
    "completion": "on_ack"
}
```

调用 `drone.cmd.arm()` → 发 `MAV_CMD_COMPONENT_ARM_DISARM`，param1=1（解锁）。
`idempotent=true` 所以不用写 effect；`on_ack` 收到 ACCEPTED 即完成。

### 2. takeoff —— 带参数 + 遥测判完成

```json
"takeoff": {
    "cmd": "MAV_CMD_NAV_TAKEOFF",
    "signature": ["alt"],
    "params": { "7": "alt" },
    "idempotent": false,
    "completion": "on_telemetry",
    "effect": { "mode": ["takeoff", "loiter"] },
    "complete": { "mode": "loiter" },
    "timeout": 20,
    "max_retry": 3
}
```

调用 `drone.cmd.takeoff(10)` → 发 `NAV_TAKEOFF`，param7=10（目标高度 10m）。
`signature=["alt"]` + `params={7:"alt"}` = 把调用时的第一个参数填进 param7。

### 3. land —— 用 landed_state 判完成

```json
"land": {
    "cmd": "MAV_CMD_NAV_LAND",
    "idempotent": false,
    "completion": "on_telemetry",
    "effect": { "mode": "land" },
    "complete": { "landed_state": "on_ground" },
    "timeout": 30
}
```

### 4. rtl —— 同上，返回起飞点

```json
"rtl": {
    "cmd": "MAV_CMD_NAV_RETURN_TO_LAUNCH",
    "idempotent": false,
    "completion": "on_telemetry",
    "effect": { "mode": "rtl" },
    "complete": { "landed_state": "on_ground" },
    "timeout": 60
}
```

## 五、几个约定

- `idempotent=false` 但没写 `effect`，或 `completion=on_telemetry` 但没写 `complete`，
  会在**调用命令时**（`CommandManager._check_spec`）直接抛 `ValueError` 报错。
- `params` 槽位是 1~7（对应 MAVLink 的 param1~param7），字符串值 = 从实参取，数字 = 字面量。
- 命令名会直接成为方法名，别用 Python 关键字或下划线开头的名字。
- `land` / `rtl` 这种「重复发无害」的，其实也可以标 `idempotent=true`（就不用写 effect），
  这里标 `false` 是为了演示 effect 的用法，两种都成立。

## 附录：状态字段取值详解

四个谓词字段的完整取值，来源 `mavlink/models/flightstate.py`。

### `mode` —— 飞行模式

**主模式**（非 AUTO，`custom_mode` bits 16-23）：

| 值 | 中文 | 说人话 | 投递用不用 |
|----|------|--------|:---:|
| `manual` | 纯手动 | 飞控不增稳，摇杆给多少就多少，松杆不回平 | ❌ |
| `altctl` | 高度保持 | 自动定高，你管前后左右 | 测试用 |
| `posctl` | 位置保持 | GPS 定点，松杆原地悬停 | ✅ 手动试飞 |
| `auto` | 自动 | 自主执行，具体看子模式 | ✅ 核心 |
| `acro` | 特技 | 无增稳，做翻滚特技 | ❌ |
| `offboard` | 机外控制 | 外部计算机（树莓派）发位置/速度指令，飞控照做 | ✅✅ ArUco 视觉定位 |
| `stabilized` | 增稳 | 保持水平，控倾斜角度 | 测试用 |
| `rattitude_legacy` | 半自稳(弃用) | 老版本混合模式 | ❌ |
| `simple` | 简单模式(已移除) | 方向相对起飞点 | ❌ |
| `termination` | 飞行终止 | 强制停车/关电机，failsafe 终态 | 可能触发 |
| `altitude_cruise` | 高度巡航 | 固定翼巡航，多旋翼不用 | ❌ |

**AUTO 子模式**（`main=4` 时看，`custom_mode` bits 24-31）：

| 值 | 中文 | 说人话 | 投递用不用 |
|----|------|--------|:---:|
| `ready` | 待命 | 进了 AUTO 还没动作 | — |
| `takeoff` | 起飞 | 自动爬升到目标高度 | ✅ |
| `loiter` | 悬停 | 定点保持位置和高度（原叫 hover） | ✅ |
| `mission` | 任务 | 执行预设航点任务 | ✅ 核心 |
| `rtl` | 返航 | Return To Launch，飞回起飞点 | ✅ |
| `land` | 降落 | 自动降落 | ✅ |
| `follow_target` | 跟随目标 | 跟着移动目标（人/车） | ❌ |
| `precland` | 精准降落 | 视觉（ArUco）引导降落到码上 | ✅✅ 关键 |
| `vtol_takeoff` | VTOL 起飞 | 垂直起降固定翼 | ❌ |
| `external1~8` | 外部自定义 | 预留槽位 | ❌ |

### `landed_state` —— 着地状态

| 值 | 中文 | 说人话 |
|----|------|--------|
| `undefined` | 未知 | 刚上电/无数据 |
| `on_ground` | 在地面 | 已落地 |
| `in_air` | 在空中 | 正常飞行 |
| `takeoff` | 起飞中 | 正在爬升 |
| `landing` | 降落中 | 正在下降 |

> 低频消息（约 1~2Hz），有滞后，适合判「落没落」这种慢状态，别做实时控制。

### `armed` —— 是否解锁

| 值 | 中文 |
|----|------|
| `false` | 未解锁（电机锁定、油门无效，停地面） |
| `true` | 已解锁（电机可转，准备飞/在飞） |

### `system_status` —— 系统状态

| 值 | 中文 | 说人话 |
|----|------|--------|
| `uninit` | 未初始化 | 刚上电 |
| `boot` | 启动中 | 引导中 |
| `calibrating` | 校准中 | 校准陀螺仪/加速度计/罗盘 |
| `standby` | 待命 | 就绪但未解锁 |
| `active` | 活动 | 已解锁运行 |
| `critical` | 危急 | 触发 failsafe（低电量/断连/传感器故障） |
| `emergency` | 紧急 | 紧急状态（紧急降落） |
| `poweroff` | 关机中 | 正在关机 |
| `flight_termination` | 飞行终止 | kill switch 触发，强制停车 |

> 安全监控重点看 `critical` / `emergency`。
