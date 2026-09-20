"""Security 生命周期、巡检及处置调度；不直接收发 MAVLink。

检查与策略可通过构造参数替换，默认使用 checks.run_checks/policy.evaluate。
阻塞的 Command 在单独工作线程执行，巡检持续运行。安全动作串行提交；升级决策
在当前动作返回后按最新快照重新评估。因此 Command 必须提供有界等待和真实结果。
"""
from __future__ import annotations

from dataclasses import replace
import logging
import math
import threading
import time
from types import MappingProxyType
from typing import Callable, ContextManager, Protocol

from . import checks, policy
from .checks import CheckConfig
from .models import (
    SafetyAction, SafetyDecision, SafetyEvent, SafetyLevel,
    SecurityError, SecurityStatus, TelemetrySnapshot,
)
from .policy import PolicyRules

log = logging.getLogger(__name__)
CheckRunner = Callable[[TelemetrySnapshot, CheckConfig], tuple[SafetyEvent, ...]]
PolicyEvaluator = Callable[[tuple[SafetyEvent, ...], TelemetrySnapshot, PolicyRules], SafetyDecision | None]
_LEVEL_ORDER = {SafetyLevel.NORMAL: 0, SafetyLevel.UNKNOWN: 1, SafetyLevel.WARNING: 2,
                SafetyLevel.CRITICAL: 3, SafetyLevel.EMERGENCY: 4}


class CommandPort(Protocol):
    """安全控制适配契约，不能直接把当前仓库 CommandManager 当作已实现此接口。

    成功统一返回 None，失败抛异常。safety_control 必须与所有普通命令共享调度
    仲裁，覆盖 cancel 到安全动作完成；不能简单持有 Command 的 ACK 状态锁，
    否则等待动作会死锁。独立的 Security 私有锁不能代替这个仲裁。
    """

    def safety_control(self) -> ContextManager[None]:
        """取得安全控制权；有界获取，退出时释放，普通命令不能插队。"""
        ...

    def cancel(self, reason: str = "cancelled") -> None:
        """取消本地当前命令、唤醒等待者；不表示飞机停止。"""
        ...

    def hold(self) -> None:
        """请求保持，按 Command 完成判据返回；必须有界等待。"""
        ...

    def rtl(self) -> None:
        """请求返航，按 Command 完成判据返回；必须有界等待。"""
        ...

    def land(self) -> None:
        """请求降落，按 Command 完成判据返回；必须有界等待。"""
        ...


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} 必须为有限正数")
    return float(value)


class SecurityManager:
    def __init__(
        self, read_snapshot: Callable[[], TelemetrySnapshot], cmd: CommandPort, *,
        interval_s: float, checks_config: CheckConfig, policy_rules: PolicyRules,
        check_runner: CheckRunner | None = None,
        policy_evaluator: PolicyEvaluator | None = None,
        stop_timeout_s: float = 5.0, action_retry_s: float = 5.0,
    ) -> None:
        """注入统一状态、Command 和配置，不自动启动。

        stop_timeout_s 是一次 stop 的总等待上限；超时会报告仍存活的线程，
        不谎报停止，也不强杀线程。action_retry_s 仅限制失败动作再次尝试频率。
        """
        if not callable(read_snapshot):
            raise ValueError("read_snapshot 必须可调用")
        self._interval = _positive(interval_s, "interval_s")
        self._stop_timeout = _positive(stop_timeout_s, "stop_timeout_s")
        self._action_retry = _positive(action_retry_s, "action_retry_s")
        self._read_snapshot = read_snapshot
        self._cmd = cmd
        self._checks_config = MappingProxyType(dict(checks_config))
        self._policy_rules = MappingProxyType(dict(policy_rules))
        if any(not isinstance(action, SafetyAction) for action in self._policy_rules.values()):
            raise ValueError("policy_rules 的值必须是 SafetyAction")
        self._check_runner = check_runner if check_runner is not None else checks.run_checks
        self._evaluate = policy_evaluator if policy_evaluator is not None else policy.evaluate
        if not callable(self._check_runner) or not callable(self._evaluate):
            raise ValueError("检查和策略必须可调用")
        self._lock = threading.RLock()
        self._check_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._stopping = False
        self._thread: threading.Thread | None = None
        self._action_thread: threading.Thread | None = None
        self._handled_key: tuple[object, ...] | None = None
        self._attempted_at = 0.0
        self._last_attempt_succeeded: bool | None = None
        self._check_error: str | None = None
        self._action_error: str | None = None
        self._status = SecurityStatus(False, SafetyLevel.UNKNOWN, None, (), None, None, None)

    def start(self) -> None:
        """幂等启动；停止中的旧线程尚未退出时禁止重启。"""
        with self._lock:
            if self._stopping:
                raise SecurityError("Security 正在停止，请等待 stop 成功后重启")
            if self._thread is not None and self._thread.is_alive():
                return
            if self._action_thread is not None and self._action_thread.is_alive():
                raise SecurityError("上一次安全动作尚未结束")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, name="security-monitor", daemon=True)
            self._status = replace(self._status, running=True)
            try:
                self._thread.start()
            except Exception as exc:
                self._thread = None
                self._status = replace(self._status, running=False)
                raise SecurityError(f"无法启动监督线程: {exc}") from exc

    def stop(self) -> None:
        """停止接收新处置并有界等待线程结束；不取消飞控中的安全动作。"""
        with self._lock:
            self._stopping = True
            self._stop_event.set()
            threads = (self._thread, self._action_thread)
        deadline = time.monotonic() + self._stop_timeout
        for thread in threads:
            if thread is not None and thread is not threading.current_thread():
                thread.join(max(0.0, deadline - time.monotonic()))
        with self._lock:
            alive = [t.name for t in (self._thread, self._action_thread) if t is not None and t.is_alive()]
            if alive:
                message = "停止超时，线程仍运行: " + ", ".join(alive)
                self._action_error = message
                self._refresh_error()
                raise SecurityError(message)
            self._stopping = False
            self._status = replace(self._status, running=False)

    def status(self) -> SecurityStatus:
        """返回不可变状态；last_action_succeeded=None 表示未取得执行结果。"""
        with self._lock:
            return self._status

    def check_once(self) -> tuple[SafetyEvent, ...]:
        """只读一份快照并检测；不调用策略/Command，不改写后台状态。"""
        with self._check_lock:
            try:
                return self._check(self._snapshot())
            except SecurityError:
                raise
            except Exception as exc:
                raise SecurityError(f"单次检查失败: {exc}") from exc

    def _snapshot(self) -> TelemetrySnapshot:
        snapshot = self._read_snapshot()
        if not isinstance(snapshot, TelemetrySnapshot):
            raise SecurityError("状态提供者必须返回 TelemetrySnapshot")
        # 输入快照必须由状态层一致地构造，此处只防止字典后续被修改。
        return replace(snapshot, updated_at=MappingProxyType(dict(snapshot.updated_at)))

    def _check(self, snapshot: TelemetrySnapshot) -> tuple[SafetyEvent, ...]:
        events = tuple(self._check_runner(snapshot, self._checks_config))
        if any(not isinstance(event, SafetyEvent) or not isinstance(event.level, SafetyLevel) for event in events):
            raise SecurityError("检查函数必须返回 SafetyEvent 集合")
        return events

    def _refresh_error(self) -> None:
        errors = [error for error in (self._check_error, self._action_error) if error]
        self._status = replace(self._status, last_error="; ".join(errors) if errors else None)

    def _loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    # 手动检查与后台检查不并发进入状态提供者/检测器。
                    with self._check_lock:
                        if self._stop_event.is_set():
                            break
                        snapshot = self._snapshot()
                        events = self._check(snapshot)
                        decision = self._evaluate(events, snapshot, self._policy_rules)
                    if decision is not None and not isinstance(decision, SafetyDecision):
                        raise SecurityError("策略必须返回 SafetyDecision 或 None")
                    with self._lock:
                        self._check_error = None
                        self._status = replace(
                            self._status, last_check=time.monotonic(), active_events=events,
                            level=max((event.level for event in events), key=_LEVEL_ORDER.__getitem__, default=SafetyLevel.NORMAL),
                        )
                        self._refresh_error()
                        if not events and not (self._action_thread and self._action_thread.is_alive()):
                            self._handled_key = None
                    if decision is not None:
                        self._handle(decision)
                except Exception as exc:
                    # 不能把检测器未实现、坏遥测或策略异常当作正常状态。
                    with self._lock:
                        error = f"监督检查/策略失败: {exc}"
                        changed = error != self._check_error
                        self._check_error = error
                        self._status = replace(self._status, level=SafetyLevel.UNKNOWN, last_check=time.monotonic())
                        self._refresh_error()
                    if changed:
                        log.exception("监督检查/策略失败")
                self._stop_event.wait(self._interval)
        finally:
            with self._lock:
                self._status = replace(self._status, running=False)

    def _handle(self, decision: SafetyDecision) -> None:
        """同一动作/事件类型/级别去重；数值、原因时间变化不造成连续重发。"""
        if not isinstance(decision.action, SafetyAction):
            raise SecurityError("非法安全动作")
        key = (decision.action, tuple(sorted({(event.type, event.level.value) for event in decision.events})))
        with self._lock:
            if self._stop_event.is_set():
                return
            # 当前动作尚未返回时继续巡检，但不同时提交第二个动作。
            if self._action_thread is not None and self._action_thread.is_alive():
                return
            if key == self._handled_key:
                if self._last_attempt_succeeded is True or time.monotonic() - self._attempted_at < self._action_retry:
                    return
            self._handled_key = key
            self._attempted_at = time.monotonic()
            self._last_attempt_succeeded = None
            self._action_error = None
            self._status = replace(self._status, last_action=decision.action, last_action_succeeded=None)
            self._refresh_error()
            if decision.action == SafetyAction.WARN:
                log.warning("安全告警: %s", decision.reason)
                self._last_attempt_succeeded = True
                self._status = replace(self._status, last_action_succeeded=True)
                return
            self._action_thread = threading.Thread(
                target=self._execute_action, args=(decision,), name="security-action", daemon=True,
            )
            try:
                self._action_thread.start()
            except Exception as exc:
                self._action_thread = None
                self._last_attempt_succeeded = False
                self._action_error = f"安全动作线程启动失败: {exc}"
                self._status = replace(self._status, last_action_succeeded=False)
                self._refresh_error()
                raise SecurityError(self._action_error) from exc

    def _execute_action(self, decision: SafetyDecision) -> None:
        try:
            self._preempt(decision.action, decision.reason)
        except Exception as exc:
            with self._lock:
                self._last_attempt_succeeded = False
                self._action_error = f"安全动作失败: {exc}"
                self._status = replace(self._status, last_action_succeeded=False)
                self._refresh_error()
            log.exception("安全处置失败")
        else:
            with self._lock:
                self._last_attempt_succeeded = True
                self._action_error = None
                self._status = replace(self._status, last_action_succeeded=True)
                self._refresh_error()

    def _preempt(self, action: SafetyAction, reason: str) -> None:
        """取得共享安全控制权后先 cancel 再动作；缺少仲裁时在 cancel 前报错。"""
        if action not in {SafetyAction.HOLD, SafetyAction.RTL, SafetyAction.LAND}:
            raise SecurityError("只有 HOLD/RTL/LAND 可进入安全抢占")
        guard = getattr(self._cmd, "safety_control", None)
        cancel = getattr(self._cmd, "cancel", None)
        execute = getattr(self._cmd, action.value, None)
        if not all(callable(method) for method in (guard, cancel, execute)):
            raise SecurityError("Command 缺少 safety_control/cancel/动作适配，未执行抢占")
        try:
            with guard():
                if self._stop_event.is_set():
                    raise SecurityError("监督已停止，未提交新的安全动作")
                if cancel(reason) is not None:
                    raise SecurityError("cancel 适配需成功返回 None，失败抛异常")
                if execute() is not None:
                    raise SecurityError("动作适配需在真实完成后返回 None，失败抛异常")
        except SecurityError:
            raise
        except Exception as exc:
            raise SecurityError(f"{action.value} 抢占失败: {exc}") from exc
