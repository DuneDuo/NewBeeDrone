# Command_Long 参数参考

> 用途：写 command 层（`COMMAND_LONG` / `COMMAND_ACK`）时，每个 MAV_CMD 的 `param1~7` 填什么。
> 配套：`command实现教程.md`（命令层架构）
> 来源：`common.xml`（pymavlink 2.4.49 实测，即 MAVLink 官方协议定义）
> ⚠️ **本文件是 command 层（COMMAND_LONG）的参数参考，和 `Mission航点参数参考.md`（MISSION_ITEM_INT）是两回事，别混用。**

---

## 一、最重要的区别：command_long vs mission_item 单位不同

**同一个 MAV_CMD**（比如 `NAV_TAKEOFF`=22）在两种消息里，参数单位和类型完全不同：

| | COMMAND_LONG（command 层） | MISSION_ITEM_INT（mission 层） |
|---|---|---|
| 消息 id | COMMAND_LONG = 76 | MISSION_ITEM_INT = 73 |
| 参数 | `param1~7` 全是 **float** | `param1~4` float + `x/y/z` **int32** |
| 高度 | **米（m）** | **毫米（mm）** |
| 经纬度 | **度（float）** | **度 ×1e7（int32）** |
| 确认消息 | COMMAND_ACK = 77 | MISSION_ACK = 47 |

> ⚠️ 同样 10 米高度：command_long 填 `10.0`，mission_item 填 `10000`。填错就是 **1000 倍**，飞机会飞到天上去。

---

## 二、command 层用到的 MAV_CMD 官方参数

### COMPONENT_ARM_DISARM（400）— 解锁 / 上锁

| param | 官方含义 |
|:---:|---|
| 1 | **1 = 解锁，0 = 上锁**（非 0/1 非法） |
| 2 | 0 = 正常（有安全检查），21196 = 强制 |
| 3~7 | 空 |

### NAV_TAKEOFF（22）— 起飞

| param | 官方含义 | 单位 |
|:---:|---|---|
| 1 | 最小俯仰角 | deg |
| 4 | 起飞后 yaw，**NaN = 用系统当前 yaw** | deg |
| 5 | 起飞点纬度（可填 home） | 度 |
| 6 | 起飞点经度 | 度 |
| 7 | **起飞目标高度** | **m** |

### NAV_LAND（21）— 降落

| param | 官方含义 | 单位 |
|:---:|---|---|
| 1 | 中止降落的最小高度（0 = 系统默认） | m |
| 2 | 精确降落模式 | — |
| 4 | 期望 yaw，**NaN = 用系统当前** | deg |
| 5 | 降落点纬度 | 度 |
| 6 | 降落点经度 | 度 |
| 7 | 降落点地面高度（当前 frame 下） | m |

### NAV_RETURN_TO_LAUNCH（20）— 返航

**param1~7 全空**。返航点（home）飞控自己记录。

### DO_REPOSITION（192）— 定点（guided 模式用）

| param | 官方含义 | 单位 |
|:---:|---|---|
| 1 | 地速，<0（如 -1）= 默认 | m/s |
| 2 | 选项位掩码 | — |
| 3 | 盘旋半径（0 或 NaN = 忽略） | m |
| 4 | yaw，**NaN = 用系统当前 yaw 模式** | **rad** |
| 5 | 纬度 | 度 |
| 6 | 经度 | 度 |
| 7 | 高度 | m |

---

## 三、NaN 的官方语义

官方 `common.xml` 里，带 yaw 的命令统一写着：

> **NaN = 用系统当前 yaw heading 模式**（朝向下一个航点 / 朝 home 等）。

所以 command 层"空参数"用 NaN 表示"用默认"，是官方约定，不是我们发明的。

⚠️ **注意单位不统一**：同样是"yaw"，DO_REPOSITION 是 **rad（弧度）**，TAKEOFF / LAND 是 **deg（度）**。查表时别看串单位。

---

## 四、COMMAND_ACK 字段（command 层的确认消息）

| 字段 | 含义 |
|---|---|
| `command` | 被确认的 MAV_CMD |
| `result` | 执行结果（MAV_RESULT） |
| `progress` | 进度（仅 result=IN_PROGRESS 时有效） |
| `result_param2` | 附加结果信息 |
| `target_system` / `target_component` | 原指令接收方 |

> ⚠️ **COMMAND_ACK 没有序列号字段**，只有 `command`。所以命令层只能"单飞 + current 槽位"来匹配 ack——这也是"必须先挂台账再发送"的根本原因。

`result` 枚举见 `消息字段参考.md` 第 13 节。
