# Param 参数读写实现参考

> 讲清楚"怎么读一个参数、怎么改一个参数并确认改成功"。
> 这份是**设计 + 骨架参考**，代码你自己写（骨架里留了 TODO）。
> 配套：`core/drone.py`（已有的 `param_request_read` / `param_set`）、`mavlink/handlers.py`。

---

## 零、一句话说清楚

param 读写就是**"问飞控要一个参数值"或"改一个参数值，然后确认改成功"**。

它比 command 简单得多，因为是一问一答，没有"IN_PROGRESS 等遥测达成"这种复杂生命周期。所以**别建 command 那套**（JSON 定义表 + 台账 + 状态机），一套轻量的"请求-应答配对"就够。

---

## 一、param 是什么 + 协议事实

param = 飞控的**配置项**（PID 增益、failsafe 阈值、RC 量程、电池标定、巡航速度…），就是 Mission Planner / QGC"参数页"里调的那些。**装机/调试时设一次，飞行中基本不改**，存飞控非易失存储。

**三类上行交互的回执不一样，别搞混：**

| 你发的 | 飞控回的 | 回执有没有 result（成功/失败） |
|---|---|---|
| `COMMAND_LONG` (76) | `COMMAND_ACK` (77) | ✅ 有 |
| `PARAM_REQUEST_READ` (20) | `PARAM_VALUE` (22) | ❌ 没有，只有值 |
| `PARAM_SET` (23) | `PARAM_VALUE` (22) | ❌ 没有，只有回显值 |

三个关键结论：

1. **read / set 不回 COMMAND_ACK，回 `PARAM_VALUE`。** 只有 command 类（command_long）才回 COMMAND_ACK。
2. **不会串**：消息类型不同，`dispatch` 按 `msg.get_type()` 分开路由；`PARAM_VALUE` 根本不会进 command 的 `on_ack`。
3. **没有 result 字段**，所以"改成功没成功"**靠回显值/读回值来判断**，不是靠一个 success 标志。

---

## 二、为什么不用 command 那套

| command 需要 | param 需要吗 |
|---|---|
| JSON 定义表（签名、参数映射） | ❌ 不需要，就 `param_id + value + type` 三个东西 |
| 台账（run_id/state/retry） | ❌ 不需要，一问一答没有生命周期 |
| completion 三模式（ack/遥测/终态） | ❌ 不需要 |
| 幂等重发 | ❌ 不需要 |

param 要的只是：**发出去 → 等对应的 PARAM_VALUE 回来 → 拿值/比对**，加一个超时。几十行搞定。

---

## 三、核心设计：单槽操作对象（ParamOp）

### 3.1 什么是"操作对象"

就是一个小数据容器，装"这一次参数操作"的信息：

```python
class ParamOp:
    def __init__(self, param_id):
        self.param_id = param_id   # 操作哪个参数
        self.want = None           # 写操作的目标值（读操作用不到）
        self.result = None         # 回传的值（读结果 / set 的回显）
        self.event = threading.Event()   # 阻塞/唤醒用的信号灯
```

### 3.2 什么是"单槽"

drone 里**只有一个这种对象的坑位**，同一时刻最多一个操作在飞：

```python
self.param_op = None   # None = 空闲；有值 = 正在进行的那个操作
```

因为你的系统是**单飞 + 串行调用**，一次只会有一个参数操作，一个槽位够用。（真要并发多个参数才需要 `dict[param_id, op]`，现在用不上。）

### 3.3 event.wait / set 是什么

**不是回调，也不是线程。** 它是"阻塞-唤醒"：

- 调用线程 `event.wait(timeout)` → 自己睡过去
- 接收线程收到 PARAM_VALUE → `event.set()` → 把调用线程叫醒

这样 `read_param("X")` 看起来就像个普通同步函数，一行拿到返回值。你 command 层 `takeoff(10)` 内部已经这么干了（`done_event.wait`），这里保持一致。

---

## 四、线程怎么配合（不用新开线程）

你已经有**两个线程**，操作对象只是它们之间交接数据的盒子：

```
调用线程（谁调 read_param/set_param）
   │ 填 ParamOp、占单槽
   │ 发 PARAM_REQUEST_READ / PARAM_SET
   │ op.event.wait(超时)   ← 阻塞在这
   │
接收线程（drone.receive_loop，早就存在）
   │ 收到 PARAM_VALUE
   │ param_id 匹配 → op.result = 值
   │ op.event.set()        ← 唤醒调用线程
   │
调用线程  醒来，返回/比对
```

**全程不需要新开线程。**

---

## 五、实现步骤

### 5.1 drone 层（core/drone.py）

在 `__init__` 加单槽：

```python
self.param_op = None   # 进行中的参数操作
```

加两个方法（`param_request_read` / `param_set` 你已经有了，这两个是**带等待的封装**）：

```python
def read_param(self, param_id, timeout=3.0):
    # TODO: 建 ParamOp(param_id) 占单槽 → 调 self.param_request_read(param_id)
    #       → op.event.wait(timeout)，超时则清槽、报错
    #       → 返回 op.result

def set_param(self, param_id, value, param_type=9, timeout=3.0):
    # TODO: 建 ParamOp(param_id)、op.want = value 占单槽 → 调 self.param_set(...)
    #       → wait 等回显 → 比对 op.result == value
    #       → 比对上，再 read 一次确认（严谨版）
    #       → 返回成功 / 失败
```

> 注意：这里 "占单槽" 要处理一个情况——如果上一个操作还没结束（`self.param_op is not None`），要么报"忙"，要么等它结束。单飞串行场景一般直接报"忙"即可。

### 5.2 handlers 层（mavlink/handlers.py）

加一个 PARAM_VALUE handler：

```python
@register("PARAM_VALUE")
def PARAM_VALUE_HANDLER(drone, msg):
    # TODO: op = drone.param_op
    #       if op 且 op.param_id == 清理后的 msg.param_id:
    #           op.result = msg.param_value
    #           op.event.set()
    pass
```

---

## 六、read / set 的完整流程

### read（读）

```
read_param("RC1_MAX")
  → 占单槽
  → 发 PARAM_REQUEST_READ
  → wait（超时 3s）
  → 收到 PARAM_VALUE → 填 result、set
  → 醒来，返回 result
```

### set（改，严谨版）

```
set_param("RC1_MAX", 2000)
  → 占单槽，want = 2000
  → 发 PARAM_SET
  → wait 回显（超时 3s）
  → 收到 PARAM_VALUE，比对 result == 2000
  → 比对上 → 再 read 一次确认（读回值 == 2000）
  → 才返回"成功"
```

**说明：**

- **"先读旧值"不是必需的**——除非你要记录旧值将来回滚。不需要就省掉，直接 set。
- **"回显比对"是基础确认**，飞控回 `PARAM_VALUE` 表示"收到并尝试写入"。
- **"再读确认"是严谨版双保险**——因为回显不一定保证持久化，设完读一遍、读回值对上才真正确认写进去。**改参数推荐用这版。**

---

## 七、三个坑（必踩，提前记）

### 1. 超时必须有

飞控不回（参数名写错、断链）会永远卡住。`wait` 必须带 `timeout`，超时走失败路径、清槽。

### 2. param_id 是 char[16]，回传带 null 填充

你发 `b"RC1_MAX"`，飞控回的 `msg.param_id` 是 16 字节定长：`b"RC1_MAX\x00\x00\x00\x00\x00\x00\x00\x00\x00"`。比对前要 strip：

```python
pid = bytes(msg.param_id).rstrip(b"\x00").decode()   # → "RC1_MAX"
```

不 strip，`msg.param_id == b"RC1_MAX"` 永远比对不上。

### 3. param_set 要带 param_type

`param_set` 默认 `param_type=9`（REAL32）。设整型参数（如 `RC1_MAX`）要用对类型，否则飞控拒。常用：

| 类型 | 值 |
|---|---|
| INT8 | 2 |
| INT16 | 4 |
| INT32 | 6 |
| UINT8 | 1 |
| UINT16 | 3 |
| REAL32 | 9（默认） |
| REAL64 | 10 |

---

## 八、待办清单（明天写的时候对照）

- [ ] `core/drone.py`：加 `self.param_op = None` 单槽 + `ParamOp`（或直接用简单属性）
- [ ] `core/drone.py`：写 `read_param`（带等待 + 超时）
- [ ] `core/drone.py`：写 `set_param`（回显比对 + 再读确认 + 超时）
- [ ] `mavlink/handlers.py`：加 `PARAM_VALUE` handler（param_id 匹配 + strip null + 填值 + set）
- [ ] 处理"占槽时已有操作在飞"的忙状态
- [ ] 测：读一个已知参数（如 `RC1_MAX`），再设一个值、读回确认
