# Command 命令层实现教程（逐行讲解版）

> 面向代码基础薄弱的读者。这一版只讲**代码怎么实现、每个方法在干嘛**。
> 配套文件：`command.py`、`models/cmd.py`、`models/cmd_record.py`、`commands.json`、`command_long参数参考.md`。
> 建议：把三个代码文件开着，对着本文读。

---

## 零、一句话说清楚整件事

命令层干的事就是：

> **你调一句 `drone.cmd.takeoff(10)`，它帮你把"起飞到 10 米"这条命令发出去，然后盯着飞控，直到确定"成了"或"超时"才返回。**

中间它自动做了三件事：**翻译**（把 takeoff 这个名字翻成飞控认识的指令）→ **记台账**（记下"这条命令现在到哪一步了"）→ **追踪**（盯 ack 和遥测，判断成没成）。

---

## 一、文件分工（先记住谁放哪）

| 文件 | 放什么 | 你改不改 |
|---|---|---|
| `commands.json` | **定义表**：每条命令"是什么"（名字、指令号、参数、怎么判完成） | ✅ 只改这个 |
| `models/cmd.py` | **定义层**：CommandSpec（定义表）+ load_specs（读 JSON） | ❌ 不改 |
| `models/cmd_record.py` | **台账层**：Command（台账行）+ 状态/error 常量 | ❌ 不改 |
| `command.py` | **引擎层**：CommandManager（构造 + 记台账 + 追踪） | ❌ 不改 |
| `config.py` | 3 个常量 | 偶尔 |
| `drone.py` / `handlers.py` | 接线（挂载 + 收 ack） | 接一次 |

**分层原则**：数据（CommandSpec、Command）放 models，逻辑（CommandManager）放 command.py。引擎 import 数据层，反过来不行。

---

## 二、定义层 models/cmd.py 逐行讲

这个文件回答"每条命令是什么" + "怎么把命令名变成函数"。四块内容。

### 2.1 completion 常量（完成判据）

```python
ON_ACK = "on_ack"              # 收到终态 ack 即完成（arm）
ON_FINAL_ACK = "on_final_ack"  # IN_PROGRESS 后等终态 ack（校准）
ON_TELEMETRY = "on_telemetry"  # ACCEPTED 后等遥测（takeoff/land/rtl）
```

这三个字符串回答"这条命令算完成靠什么"。arm 收到 ack 就算完（ON_ACK）；takeoff 收到 ack 后还得盯遥测看它悬停没（ON_TELEMETRY）。

### 2.2 CommandSpec：定义表（静态，一行一种命令）

```python
@dataclass
class CommandSpec:
    name: str            # 语义名 "takeoff"，三合一：JSON 的 key = 方法名 = 台账外键
    cmd: int             # MAV_CMD 号 22
    signature: tuple     # 实参名顺序 ("alt",)，决定 takeoff(10) 里那个 10 叫什么
    params: dict         # 参数模板 {7: "alt"}，7 号槽取实参 alt
    idempotent: bool     # 能否安全重发
    completion: str      # 完成判据模式 on_ack / on_telemetry

    effect_check: object = None     # 生效谓词（重发前"读回"用）
    complete_check: object = None   # 完成谓词（判"悬停"这种）
    timeout: float = 5.0
    max_retry: int = 3
```

**`@dataclass` 是什么？** 一个装饰器，自动帮你写 `__init__`。没有它你得手写 10 行 `self.name = name`；有了它，声明 10 个字段，构造函数自动生成。

**`name: str` 里的 `: str` 是什么？** 类型注解，告诉别人（和 IDE）这个字段是字符串。Python 不强制检查，写错了也能跑，只是提示用。

**CommandSpec 代表"这一类命令怎么定义"，就一份。** takeoff 的 CommandSpec 固定：cmd=22、signature=("alt",)、completion="on_telemetry"。所有 takeoff 共用这一份。

### 2.3 load_specs：把 JSON 读成字典

```python
def load_specs(path, checks=None):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)               # JSON 文本 → Python dict

    specs = {}
    for name, d in raw.items():          # name="takeoff", d={"cmd":..., "params":...}
        specs[name] = CommandSpec(
            name=name,
            cmd=_cmd_id(d["cmd"]),       # "MAV_CMD_NAV_TAKEOFF" → 22
            signature=tuple(d.get("signature", [])),
            params={int(k): _param_value(v) for k, v in d.get("params", {}).items()},
            idempotent=d.get("idempotent", False),
            completion=d.get("completion", "on_ack"),
            effect_check=_make_check(d.get("effect"), checks),
            complete_check=_make_check(d.get("complete"), checks),
            timeout=d.get("timeout", 5.0),
            max_retry=d.get("max_retry", 3),
        )
    return specs
```

三个辅助函数各管一件事：

- **`_cmd_id(name)`**：`"MAV_CMD_NAV_TAKEOFF"` → `22`。用 `getattr(common, name)`，因为 JSON 里存的是字符串，得拿字符串去 pymavlink 查数字。
- **`_param_value(v)`**：参数三态——字符串 `"alt"` 原样保留（实参名）、数字 `1` 原样保留（字面量）、`null` → `float("nan")`（用默认）。
- **`_make_check(spec, checks)`**：把 `{"state":"hover"}` 变成判断函数 `lambda d: d.state.current == "hover"`。

**记住**：`load_specs` 输入 commands.json，输出 `{"arm": CommandSpec, "takeoff": CommandSpec, ...}`。以后加命令只改 JSON。

### 2.4 转译在哪？（不在定义层）

定义层 cmd.py 是纯数据，不含转译逻辑。把字典转译成"完整命令函数"这一步在**引擎层** command.py 的 `_bind` 里做（见 §4.0）——因为完整函数需要引擎能力（构造消息、记台账、追踪），放纯数据层不合适。

**提前说一句**：这里的"转译"不是"把命令名转发给一个 execute 方法"，而是**给每个命令生成一个完整的函数**（自带构造 + 记台账 + 追踪）。具体见 §4.0。

---

## 三、台账层 models/cmd_record.py 逐行讲

这个文件回答"这一次执行走到哪一步"。

### 3.1 状态 / error 常量

```python
PENDING = "pending"        # 已建好、还没发
SENT = "sent"              # 已发送，等第一个 ack
EXECUTING = "executing"    # 执行中
DONE = "done"              # 终态：完成
TIMEOUT = "timeout"        # 终态：异常

ERROR_TIMEOUT = "timeout"      # 重试耗尽仍没 ack
ERROR_LINK_LOST = "link_lost"  # 链路断了
```

**为什么用字符串不用数字？** 台账要写进 JSON 给人看，`"done"` 一眼懂，`2` 还得查表。

### 3.2 Command：台账行（动态，一次执行一行）

```python
class Command:
    def __init__(self, name, cmd, params):
        # 只记"这一次执行"的最小信息（不抄定义字段）
        self.name = name                  # 命令名（审计 + 查 spec 的 key）
        self.cmd = cmd                    # 重发时用它重建消息
        self.params = params or {}        # 实际填的 param1~7

        # 运行时才填的"动态"字段（这次执行走到哪了）
        self.run_id = None                # 自增主键
        self.state = PENDING              # 当前状态
        self.result = None                # 飞控回的 MAV_RESULT
        self.error = None                 # 本地异常
        self.retry_count = 0
        self.started_at = None
        self.sent_at = None
        self.done_at = None
        self.detail = None
        self.done_event = None            # 阻塞等待用
```

**CommandSpec 和 Command 的区别（关键）：**

| | 代表 | 数量 | 类比 |
|---|---|---|---|
| CommandSpec | "这一类命令" | 一份 | 菜谱（"鱼香肉丝怎么做"） |
| Command | "这一次执行" | 每次一份 | 一盘菜（"这一盘鱼香肉丝"） |

你每调一次 `drone.cmd.takeoff(10)`，就 new 出一个新的 Command，只记"这一次"的执行状态。

**两个"不存"：**

- **不抄定义字段**：completion / idempotent / effect_check / complete_check / timeout / max_retry 这些"这类命令的定义"**不抄进台账**——它们在 spec 里，引擎需要时按 `name` 查 spec 拿（`self.specs[c.name].completion`），避免定义存两份。
- **不存 msg 对象**：只存 `cmd` + `params`，发送时再临时重建（见 §4.2 `_encode`）。

---

## 四、引擎层 command.py 逐行讲

核心是一个类 `CommandManager`，按调用顺序读。

### 4.0 _bind：把字典转译成一套完整命令函数

```python
class CommandManager:
    def __init__(self, drone):
        self.drone = drone
        self.specs = load_specs(config.cmd_spec_path)   # JSON → 字典
        self.current = None                              # 在飞那一条（单槽）
        self.runs = deque(maxlen=50)                    # 所有指令表（有界，每条带状态）
        self._lock = threading.Lock()
        self._seq = 0
        self._bind()                                     # ★ 转译：字典 → 一套完整函数

    def _bind(self):
        for name, spec in self.specs.items():
            setattr(self, name, self._make(spec))   # 每个命令名挂一个完整函数

    def _make(self, spec):
        def command(*args):
            return self._run(spec, *args)          # 完整流程
        command.__name__ = spec.name
        return command
```

**关键：转译是"生成完整函数"，不是"转发到 execute"。**

`_bind` 遍历字典，给每个命令名 `setattr` 挂一个函数。`_make(spec)` 用闭包生成这个函数——它捕获了 `spec` 和 `self`，调用时就执行完整流程。

所以 `self.takeoff` **不是一个"转发壳"**，它本身就是一个完整的命令：`self.takeoff(10)` = 构造消息 + 记台账 + 发送 + 追踪 + 返回结果。字典里每多一个命令名，就自动多一个完整函数，不用写任何 `def`。

`setattr(self, name, func)` 是"给 self 动态加一个属性/方法"，等价于 `self.name = func`。`_make` 里那个 `def command` 是**闭包**——它记住了生成时捕获的 `spec`，以后每次调用都带着这个 spec。

### 4.1 _run + _build（完整流程 + 构造）

```python
def _run(self, spec, *args):
    c = self._build(spec, *args)   # 1. 构造消息 + 建台账行
    return self._send(c)           # 2. 记台账 + 发送 + 追踪

def _build(self, spec, *args):
    kw = dict(zip(spec.signature, args))      # takeoff(10) → {'alt': 10}
    p = {i: 0.0 for i in range(1, 8)}         # param1~7 先全 0
    for slot, src in spec.params.items():     # 用 params 覆盖
        p[slot] = kw[src] if isinstance(src, str) else src
    return Command(name=spec.name, cmd=spec.cmd, params=p, ...)
```

`_run` 是一条命令的完整流程，两步：构造 → 执行。上一步 `_make` 生成的函数（`self.takeoff`）调用的就是 `_run`。

`_build` 的重点是**参数映射**：`spec.params = {7: "alt"}`，`src="alt"` 是字符串 → 取实参 `kw["alt"]=10` → `p[7]=10`。其余槽保持 `0.0`。最终 `takeoff(10)` 得到 `p = {1:0, ..., 7:10}`。

### 4.2 _encode（重建消息）

```python
def _encode(self, c):
    p = c.params
    return self.drone.mav.command_long_encode(
        self.drone.sys_id, 1, c.cmd, 0,
        p[1], p[2], p[3], p[4], p[5], p[6], p[7])
```

台账不存 msg 对象，所以每次发送/重发前，用 `cmd + params` 现场重建一个 MAVLink 消息对象。

### 4.3 _send（发送 + 追踪，核心）

```python
def _send(self, command):
    command.done_event = threading.Event()
    with self._lock:
        command.run_id = self._seq; self._seq += 1
        command.state = SENT
        command.started_at = command.sent_at = time.time()
        self.current = command          # ★ 先挂台账，再发送
    self._record(command, "发送")
    self.drone.send_msg(self._encode(command))   # 发送
    command.done_event.wait(timeout=...)         # 阻塞等终态
    if command.state == TIMEOUT:
        raise CommandTimeout(command, ...)
    return command.result
```

四步：

1. **挂台账**：分配 run_id、置 SENT、`self.current = command`。**必须先挂再发**——ack 回来要靠 current 认领（ack 没序列号），挂晚了 ack 就丢了。
2. **发送**：`_encode` 重建消息 → `send_msg` 发出去。
3. **阻塞等待**：`done_event.wait()` 卡住，直到 on_ack 或 _tick 把命令推到终态、`set()` 才返回。
4. **返回**：成了返回 `result`，超时抛 `CommandTimeout`。

`with self._lock:` 是加锁——_send（调用线程）、on_ack（接收线程）、_tick（扫描线程）三个线程同时碰 `self.current`，得互斥。socket 发送放锁外。

### 4.4 on_ack + _finish（ack 进来）

```python
def on_ack(self, msg):
    with self._lock:
        c = self.current
        if c is None or msg.command != c.cmd:
            return                    # 残留 ack / 对不上
        result = msg.result
        if result == MAV_RESULT_IN_PROGRESS:      # 进度型
            c.state = EXECUTING
            return
        if result == MAV_RESULT_TEMPORARILY_REJECTED:  # 暂时拒绝
            c.state = SENT; c.retry_count += 1
            return
        self._finish(c, result)
```

飞控回 ack 时调这里。先匹配 `msg.command == c.cmd`（确认这条 ack 是对当前在飞的命令），再按 result 分三种：IN_PROGRESS 转 EXECUTING、TEMPORARILY_REJECTED 回 SENT 等重发、其他终态走 `_finish`。

`_finish` 关键：ON_TELEMETRY 模式（takeoff/land/rtl）收到 ACCEPTED **还不算完**——转 EXECUTING，靠遥测判"悬停/落地"才算真完成。

### 4.5 _tick（超时扫描）

`tick_loop` 线程每 0.5 秒跑 `_tick`，处理三件事：

1. **SENT 超时没 ack** → 非幂等先"读回"（effect_check），没生效就重发，重试耗尽就 TIMEOUT。
2. **EXECUTING（ON_TELEMETRY）** → 查 `complete_check`（飞机悬停没），达成 DONE，超时 TIMEOUT。
3. **EXECUTING（ON_FINAL_ACK）** → 等终态 ack，超时 TIMEOUT。

### 4.6 _record（记台账：内存实时，JSON 终态追加）

台账的**内存表**是 `runs`（所有指令，每条带状态）和 `current`（在飞快捷指针），它们的更新已经在调用处做了：

- `_send` 里 `runs.append(c)` + 挂 `current`（创建即进"所有指令表"）
- `on_ack` / `_tick` 里原地改 `c.state`（runs 里的对象状态就跟着变，执行中/完成/错误都能看到）

`_record` 做的是**持久化**：指令到终态（DONE/TIMEOUT）时，追加一行到 JSON——内存只留 50 条，JSON 全量不丢。

```python
def _record(self, c, event):
    log.info(f"[run_id={c.run_id}] {c.name} {c.state} <- {event} params={c.params}")
    if c.state in (DONE, TIMEOUT):
        self._append(c)               # 终态才落盘

def _append(self, c):
    sys_id = self.drone.sys_id or "unknown"
    path = os.path.join(_get_run_dir(), f"{sys_id}.jsonl")   # 每飞机一个文件
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(self._row(c), ensure_ascii=False) + "\n")   # 追加一行

def _row(self, cmd):
    return {"name": cmd.name, "cmd": cmd.cmd, "params": cmd.params,
            "state": cmd.state, "result": cmd.result, "error": cmd.error,
            "retry_count": cmd.retry_count,
            "started_at": cmd.started_at, "sent_at": cmd.sent_at, "done_at": cmd.done_at}
```

`_row` 把台账行转成 dict 时，**丢掉了 `done_event` 这类运行时对象**（threading.Event 不能进 JSON），只留能序列化的字段。

**落盘结构**（一次进程一个文件夹，按日期+时间命名；文件夹里每个飞机一个文件）：

```
command_logs/
  2026-08-28_14-30-00/
    1.jsonl        # sys_id=1 的台账（全量，一行一条终态指令）
    2.jsonl        # sys_id=2 的台账
```

`_get_run_dir()` 是进程级缓存：首次调用时建文件夹，进程内复用，所以几个 drone 共用一个文件夹、各写各的文件。

**前端查台账**：同进程直接读内存 `drone.cmd.runs`（所有指令+状态）和 `drone.cmd.current`（在飞那条），不用读 JSON。

---

## 五、接线（还剩 3 个文件）

### 5.1 config.py

```python
cmd_spec_path = "commands.json"   # 命令定义表 JSON 路径
cmd_tick_interval = 0.5           # 超时扫描间隔（秒）
cmd_first_ack_timeout = 2.0       # 等第一个回执超时（秒）
```

### 5.2 drone.py（3 处）

```python
from .command import CommandManager          # 顶部 import

self.cmd = CommandManager(self)              # __init__ 里挂载

def send_msg(self, msg):                     # 加通用发送
    self._send(msg.pack(self.mav))

# receive_loop 里启动扫描线程：
threading.Thread(target=self.cmd.tick_loop, daemon=True).start()
```

### 5.3 handlers.py

```python
@register("COMMAND_ACK")
def COMMAND_ACK_HANDLER(drone, msg):
    drone.cmd.on_ack(msg)
```

接完这 3 处，`drone.cmd.arm()` / `drone.cmd.takeoff(10)` 就能在 SITL 里跑了。

---

## 六、学习路径（建议顺序）

1. **先跑 `python models/cmd.py`**，看它把 commands.json 加载出来，吃透"定义表"。
2. **读 _bind/_make（§4.0）+ _run/_build（§4.1）**，吃透"翻译"（takeoff → 指令）。
3. **读 send/on_ack/_tick（§4.3~4.5）**，吃透"台账 + 追踪"。
4. **接完第五节**，在 SITL 里调 `drone.cmd.arm()`，加打印看状态流转。

---

## 七、还没写的（下一步）

- `models/state.py`：飞机状态表（`complete_check` 里"悬停/落地"依赖它）。
- `land` / `rtl` / `set_mode` / `goto` 的 JSON 定义行（现在 commands.json 只有 arm/takeoff）。
