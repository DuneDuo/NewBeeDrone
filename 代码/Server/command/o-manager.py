"""命令层引擎：把 JSON 定义表转译成一套完整的命令函数，自带「记台账 + 追踪」。

完整链路：
    commands.json           定义表（纯数据，你只改这里）
      → load_specs()        → SPECS 字典 {name: CommandSpec}
      → _bind() 转译         → 把字典变成一套完整函数：self.takeoff / self.arm / ...
                              每个函数都是完整的命令，不是"转发到 execute"的薄壳
      → self.takeoff(10)    → _run(spec, 10) 完整流程：
                               构造消息 → 记台账 → 发送 → 追踪 → 返回结果
      → on_ack / _tick       → 两个入口把状态推到终态（DONE / FAIL）

本文件是引擎层，只放 CommandManager 和 CommandTimeout。
定义（CommandSpec）在 models/cmd.py，台账（Command）在 models/cmd_record.py。

台账只存 name/cmd/params + 执行状态，不抄定义字段（completion/idempotent/...），
需要时按 name 查 spec 拿。

依赖方向（单向，躲循环导入）：
    command.py 不 import drone，只用 drone.send_command_long / drone.sys_id / drone.running / drone.state 的 duck-typing
    依赖链：drone.py → command.py → models/cmd.py + models/cmd_record.py
"""
import json
import os
import threading
import time
from collections import deque

import config
from logger import logger
from .spec import (
    load_specs,
    ON_ACK, ON_FINAL_ACK, ON_TELEMETRY,
)
from .record import (
    Command,
    PENDING, SENT, EXECUTING, DONE, FAIL,
    ERROR_TIMEOUT, ERROR_LINK_LOST, ERROR_DENIED, ERROR_UNSUPPORTED, ERROR_FAILED,
)
from pymavlink.dialects.v20.common import (
    MAV_RESULT_ACCEPTED,
    MAV_RESULT_IN_PROGRESS,
    MAV_RESULT_TEMPORARILY_REJECTED,
    MAV_RESULT_DENIED,
    MAV_RESULT_UNSUPPORTED,
    MAV_RESULT_FAILED,
)

log = logger("command")


# 飞控明确拒绝/失败的 result → (error 分类, 给人看的说明)
_RESULT_FAILURE = {
    MAV_RESULT_DENIED:      (ERROR_DENIED,      "飞控拒绝该指令"),
    MAV_RESULT_UNSUPPORTED: (ERROR_UNSUPPORTED, "飞控不支持该指令"),
    MAV_RESULT_FAILED:      (ERROR_FAILED,      "飞控执行失败"),
}


# 进程级日志文件夹：一次进程建一个（按日期+时间命名），文件夹里每个飞机一个 .jsonl
_RUN_DIR = None


def _get_run_dir():
    """新建（首次）或复用（后续）进程级的台账文件夹。"""
    global _RUN_DIR
    if _RUN_DIR is None:
        _RUN_DIR = os.path.join(config.cmd_log_dir, time.strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(_RUN_DIR, exist_ok=True)
    return _RUN_DIR


class CommandTimeout(Exception):
    """命令失败（本地超时 / 飞控拒绝 / 链路断）时抛给业务层。"""
    def __init__(self, command, reason):
        self.command = command
        self.reason = reason
        super().__init__(f"命令 {command.name} run_id={command.run_id} 异常: {reason}")


class CommandManager:
    """单飞 + 单锁。三个写入口：_send / on_ack / _tick。

    启动时 _bind 把定义表转译成一套完整函数（self.takeoff / self.arm / ...），
    每个函数内部是完整流程，业务层直接调 drone.cmd.takeoff(10) 即可。

    为什么加锁：三个不同线程写同一份状态（_send=调用线程，on_ack=接收线程，
    _tick=扫描线程），是对 08-12「不加锁」决定的有意例外（遥测是单写者，命令是多写者）。
    """

    def __init__(self, drone):
        self.drone = drone
        self.specs = load_specs(config.cmd_spec_path)   # JSON → {name: CommandSpec}
        self.current = None                              # 在飞那一条（单槽）
        self.runs = deque(maxlen=50)                    # 所有指令表（有界，每条带状态）
        self._lock = threading.Lock()
        self._seq = 0
        self._bind()                                     # 转译：字典 → 一套完整函数

    # ============================================================
    # 转译：把定义表字典变成一套完整的命令函数
    # ============================================================
    def _bind(self):
        """把 specs 字典转译成一套完整命令函数，挂到 self 上。

        转译不是"把名字转发给某个 execute"，而是**给每个命令生成一个完整的函数**：
        调用 self.takeoff(10) 时，函数内部自动做完整流程（构造→台账→发送→追踪）。
        """
        for name, spec in self.specs.items():
            setattr(self, name, self._make(spec))

    def _make(self, spec):
        """生成一个完整的命令函数（闭包捕获 spec 和 self）。"""
        def command(*args):
            return self._run(spec, *args)
        command.__name__ = spec.name
        return command

    # ============================================================
    # 一条命令的完整流程
    # ============================================================
    def _run(self, spec, *args):
        """完整流程：构造消息 + 建台账行 → 记台账 + 发送 + 追踪。"""
        c = self._build(spec, *args)   # 1. 构造：参数映射 + 建台账行
        return self._send(c, spec)     # 2. 执行：记台账 + 发送 + 追踪（阻塞到终态）

    # ---------- 构造：spec + 实参 → Command 台账行 ----------
    def _build(self, spec, *args):
        # 1. 实参按 signature 对号入座：takeoff(10) → {'alt': 10}
        kw = dict(zip(spec.signature, args))
        # 2. 填 param1~7：先全 0，再用 params 覆盖（字符串=取实参，数字/nan=字面量）
        p = {i: 0.0 for i in range(1, 8)}
        for slot, src in spec.params.items():
            p[slot] = kw[src] if isinstance(src, str) else src
        # 3. 建台账行（只存 name + cmd + params，定义字段在 spec 里，不抄）
        return Command(name=spec.name, cmd=spec.cmd, params=p)

    # ---------- 发送：cmd + params → 走飞机层的 send_command_long ----------
    def _send_cmd(self, c):
        """发送 / 重发都走 drone.send_command_long，让飞机层统一记账（发什么、收什么）。"""
        p = c.params
        self.drone.send_command_long(c.cmd, p[1], p[2], p[3], p[4], p[5], p[6], p[7])

    # ---------- 写入口 1：_send（调用线程，记台账 + 发送 + 追踪） ----------
    def _send(self, c, spec):
        c.done_event = threading.Event()
        with self._lock:
            c.run_id = self._seq
            self._seq += 1
            c.state = SENT
            c.started_at = c.sent_at = time.time()
            self.current = c                # 快捷指针：在飞这条
            self.runs.append(c)             # 进"所有指令表"（每条带状态，原地更新）
        self._record(c, "发送")
        self._send_cmd(c)                      # 发送走飞机层 send_command_long（socket 放锁外）
        # 阻塞等到终态（on_ack / _tick 会 set done_event）
        c.done_event.wait(timeout=spec.timeout + config.cmd_first_ack_timeout + 5)
        if c.state == FAIL:
            raise CommandTimeout(c, c.detail or c.error)
        return c.result

    # ---------- 写入口 2：on_ack（接收线程） ----------
    def on_ack(self, msg):
        with self._lock:
            c = self.current
            if c is None or msg.command != c.cmd:
                return  # 残留 ack / 命令对不上
            spec = self.specs[c.name]   # 取定义（completion 在这里）
            result = msg.result
            if result == MAV_RESULT_IN_PROGRESS:        # 进度型，转 EXECUTING 等终态
                c.state = EXECUTING
                self._record(c, "执行中")
                return
            if result == MAV_RESULT_TEMPORARILY_REJECTED:  # 暂时拒绝，等 tick 重发（retry_count 由 tick 重发时统一 +1）
                c.state = SENT
                self._record(c, "暂时拒绝，待重试")
                return
            self._finish(c, spec, result, msg.result_param2)

    def _finish(self, c, spec, result, result_param2=0):
        c.result = result
        c.done_at = time.time()
        if spec.completion == ON_TELEMETRY and result == MAV_RESULT_ACCEPTED:
            c.state = EXECUTING        # 借 EXECUTING 表示"已受理，待遥测达成"
            self._record(c, "已受理，转遥测监控")
            return
        if result == MAV_RESULT_ACCEPTED:
            c.state = DONE
            self._move_to_completed(c, "完成")
            return
        # 飞控明确拒绝/失败（DENIED / UNSUPPORTED / FAILED / 其他非成功码）
        error, detail = _RESULT_FAILURE.get(result, (ERROR_FAILED, f"飞控返回 result={result}"))
        if result_param2:
            detail = f"{detail}(reason={result_param2})"
        c.error = error
        c.detail = detail
        c.state = FAIL
        self._move_to_completed(c, detail)

    # ---------- 写入口 3：_tick（扫描线程 0.5s） ----------
    def tick_loop(self):
        while self.drone.running:
            self._tick()
            time.sleep(config.cmd_tick_interval)

    def _tick(self):
        to_resend = None
        with self._lock:
            c = self.current
            if c is None:
                return
            spec = self.specs[c.name]   # 取定义（completion/idempotent/... 在这里）
            now = time.time()

            if c.state == SENT:   # 等第一个 ack 超时
                if now - c.sent_at >= config.cmd_first_ack_timeout:
                    if not spec.idempotent and spec.effect_check and spec.effect_check(self.drone):
                        c.state = DONE                     # 非幂等：读回已生效，无需重发
                        self._move_to_completed(c, "读回已生效")
                    elif c.retry_count >= spec.max_retry:
                        self._abort(c, ERROR_TIMEOUT, "重试耗尽")
                    else:
                        c.retry_count += 1
                        c.sent_at = now
                        to_resend = c
                        self._record(c, f"超时重发 #{c.retry_count}")

            elif c.state == EXECUTING and spec.completion == ON_TELEMETRY:
                if spec.complete_check and spec.complete_check(self.drone):
                    c.state = DONE                         # 遥测达成（如飞机 == HOVER）
                    self._move_to_completed(c, "遥测达成")
                elif now - c.sent_at >= spec.timeout:
                    self._abort(c, ERROR_TIMEOUT, "遥测达成超时")

            elif c.state == EXECUTING:   # ON_FINAL_ACK：等终态 ack 超时
                if now - (c.sent_at or now) >= spec.timeout:
                    self._abort(c, ERROR_TIMEOUT, "终态 ack 超时")

        if to_resend:
            self._send_cmd(to_resend)                       # 锁外重发：走飞机层 send_command_long

    def _abort(self, c, error, detail):
        c.error = error
        c.detail = detail
        c.state = FAIL
        c.done_at = time.time()
        self._move_to_completed(c, f"异常: {error}")

    def _move_to_completed(self, c, event):
        self.current = None                 # 清快捷指针（c 还在 runs 里，带终态状态）
        self._record(c, event)
        if c.done_event:
            c.done_event.set()              # 唤醒阻塞中的 _send()

    # ---------- 记台账（内存实时，JSON 终态追加全量） ----------
    def _record(self, c, event):
        """每次状态转换调用一次。

        内存表（runs / current）已经在调用处更新过了：
          - _send 里 runs.append(c) + 挂 current（创建即进"所有指令表"）
          - on_ack / _tick 里原地改 c.state（runs 里的对象状态就跟着变）
        这里做的是持久化：指令到终态（DONE/FAIL）时，追加一行到 JSON，
        全量保留，不随内存 50 条上限丢失。
        """
        log.info(f"[run_id={c.run_id}] {c.name} {c.state} <- {event} params={c.params}")
        if c.state in (DONE, FAIL):
            self._append(c)

    def _append(self, c):
        """终态指令追加一行到对应飞机的 JSON 文件。

        一次进程一个文件夹（按日期+时间命名），文件夹里每个飞机(sys_id)一个 .jsonl，
        有几个飞机就有几个文件。
        """
        sys_id = self.drone.sys_id or "unknown"
        path = os.path.join(_get_run_dir(), f"{sys_id}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(self._row(c), ensure_ascii=False) + "\n")

    def _row(self, cmd):
        """把 Command 台账行转成可序列化的 dict（丢掉 done_event 等运行时对象）。"""
        return {
            "name": cmd.name,
            "cmd": cmd.cmd,
            "params": cmd.params,
            "state": cmd.state,
            "result": cmd.result,
            "error": cmd.error,
            "retry_count": cmd.retry_count,
            "started_at": cmd.started_at,
            "sent_at": cmd.sent_at,
            "done_at": cmd.done_at,
        }
