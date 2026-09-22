"""Security 不可变数据模型。只保存状态投影、事件、规则与结果，不采集遥测。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from types import MappingProxyType
from typing import Mapping


class SafetyLevel(str, Enum):
    UNKNOWN = "unknown"
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SafetyAction(str, Enum):
    WARN = "warn"
    HOLD = "hold"
    RTL = "rtl"
    LAND = "land"


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是有限数值")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} 超出数值范围") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} 必须是有限数值")
    return number


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 必须是非空字符串")


def _events(values: object) -> tuple[SafetyEvent, ...]:
    if not isinstance(values, (tuple, list)) or any(not isinstance(event, SafetyEvent) for event in values):
        raise ValueError("events 必须是 SafetyEvent 的 tuple/list")
    return tuple(values)


@dataclass(frozen=True)
class TelemetrySnapshot:
    """本轮一致的只读快照；所有时间须使用同一个单调时钟。

    updated_at 保存各数据组的实际接收时间：battery/position/flight/geofence/
    command/action_ready 等。captured_at 是读取时间，不能冒充各字段更新时间。
    缺失能力使用 None。action_ready 是适配层依据当前固件、定位、返航点等条件
    对每个动作给出的明确可用结论，不是 Manager 自行猜测的能力。
    command_active=False 表示明确没有正在运行的 Command，None 表示未知。
    """
    captured_at: float
    updated_at: Mapping[str, float]
    battery_percent: float | None = None
    heartbeat_at: float | None = None
    position_valid: bool | None = None
    flight_mode: str | None = None
    armed: bool | None = None
    inside_geofence: bool | None = None
    command_started_at: float | None = None
    command_active: bool | None = None
    link_connected: bool | None = None
    action_ready: Mapping[SafetyAction, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _finite(self.captured_at, 'captured_at')
        if not isinstance(self.updated_at, Mapping) or not isinstance(self.action_ready, Mapping):
            raise ValueError("updated_at/action_ready 必须是映射")
        times = dict(self.updated_at)
        for name, stamp in times.items():
            _text(name, 'updated_at 的键')
            _finite(stamp, f'updated_at[{name}]')
        for name in ('heartbeat_at', 'command_started_at'):
            value = getattr(self, name)
            if value is not None:
                _finite(value, name)
        for name in ('position_valid', 'armed', 'inside_geofence', 'command_active', 'link_connected'):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} 必须是 bool 或 None")
        if self.battery_percent is not None:
            value = _finite(self.battery_percent, 'battery_percent')
            if not 0 <= value <= 100:
                raise ValueError("battery_percent 必须在 0..100 之间")
        if self.flight_mode is not None:
            _text(self.flight_mode, 'flight_mode')
        if self.command_active is False and self.command_started_at is not None:
            raise ValueError("command_active=False 时 command_started_at 必须为 None")
        readiness = dict(self.action_ready)
        for action, ready in readiness.items():
            if not isinstance(action, SafetyAction) or not isinstance(ready, bool):
                raise ValueError("action_ready 必须映射 SafetyAction 到 bool")
        object.__setattr__(self, 'updated_at', MappingProxyType(times))
        object.__setattr__(self, 'action_ready', MappingProxyType(readiness))


@dataclass(frozen=True)
class SafetyEvent:
    """检测事件；UNKNOWN 表示没有足够有效数据，不能当作正常或确认的危险。"""
    type: str
    level: SafetyLevel
    reason: str
    observed_at: float
    value: float | str | bool | None = None

    def __post_init__(self) -> None:
        _text(self.type, 'type')
        _text(self.reason, 'reason')
        if not isinstance(self.level, SafetyLevel):
            raise ValueError("level 必须是 SafetyLevel")
        _finite(self.observed_at, 'observed_at')
        if self.value is not None and not isinstance(self.value, (float, int, str, bool)):
            raise ValueError("value 必须是数值、字符串、bool 或 None")
        if isinstance(self.value, (float, int)) and not isinstance(self.value, bool):
            _finite(self.value, 'value')


@dataclass(frozen=True)
class SafetyRule:
    """显式策略规则；priority 越大越优先，不以动作名推断哪个更安全。

    控制动作必须显式提供 max_age_s，用于事件、心跳、flight/action_ready 的
    新鲜度校验。未提供时只允许告警。阈值和映射由公共配置装配，不在此设定。
    """
    action: SafetyAction
    priority: int = 0
    max_age_s: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, SafetyAction):
            raise ValueError("action 必须是 SafetyAction")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValueError("priority 必须是整数")
        if self.max_age_s is not None and _finite(self.max_age_s, 'max_age_s') <= 0:
            raise ValueError("max_age_s 必须为正数")


@dataclass(frozen=True)
class SafetyDecision:
    """选定的处置；这是请求意图，不表示动作已执行。"""
    action: SafetyAction
    reason: str
    events: tuple[SafetyEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.action, SafetyAction):
            raise ValueError("action 必须是 SafetyAction")
        _text(self.reason, 'reason')
        object.__setattr__(self, 'events', _events(self.events))


@dataclass(frozen=True)
class SecurityStatus:
    """不可变监督状态；last_action 与实际结果分开记录。"""
    running: bool
    level: SafetyLevel
    last_check: float | None
    active_events: tuple[SafetyEvent, ...]
    last_action: SafetyAction | None
    last_action_succeeded: bool | None
    last_error: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.running, bool) or not isinstance(self.level, SafetyLevel):
            raise ValueError("running/level 类型不正确")
        if self.last_check is not None:
            _finite(self.last_check, 'last_check')
        if self.last_action is not None and not isinstance(self.last_action, SafetyAction):
            raise ValueError("last_action 必须是 SafetyAction 或 None")
        if self.last_action_succeeded is not None:
            if not isinstance(self.last_action_succeeded, bool) or self.last_action is None:
                raise ValueError("动作结果必须是 bool，且必须有对应的 last_action")
        if self.last_error is not None and not isinstance(self.last_error, str):
            raise ValueError("last_error 必须是 str 或 None")
        object.__setattr__(self, 'active_events', _events(self.active_events))


class SecurityError(RuntimeError):
    """生命周期、状态读取、检查、策略或处置执行失败。"""
