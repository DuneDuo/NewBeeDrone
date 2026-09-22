"""纯检测函数，只输出事件，不调用 Command。

配置键（由 Server/config.py 在装配时传入；未提供的检查不启用）：
  battery_warning_percent / battery_critical_percent / battery_emergency_percent
  heartbeat_timeout_s, command_timeout_s
  position_required: bool, geofence_required: bool
  allowed_flight_modes: 非空字符串序列
  telemetry_timeout_s: 数据组新鲜度上限，单位秒
  required_telemetry: 额外必需的数据组名称序列
电量/位置/模式/围栏/命令检查必须同时提供 telemetry_timeout_s；对应组名分别为
battery/position/flight/geofence/command。阈值不内置，错拼键或无效组合会报错。
没有启用任何检查时返回 CHECKS_DISABLED(UNKNOWN)，不冒充正常监督。
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .models import SafetyEvent, SafetyLevel, TelemetrySnapshot, _finite

CheckConfig = Mapping[str, object]
_THRESHOLDS = ('battery_emergency_percent', 'battery_critical_percent', 'battery_warning_percent')
_TIMES = ('heartbeat_timeout_s', 'telemetry_timeout_s', 'command_timeout_s')
_FLAGS = ('position_required', 'geofence_required')
_SEQUENCES = ('allowed_flight_modes', 'required_telemetry')
_KEYS = frozenset(_THRESHOLDS + _TIMES + _FLAGS + _SEQUENCES)


def validate_config(config: CheckConfig) -> CheckConfig:
    """校验并复制配置；不补电量阈值、不隐式启用所有检查。"""
    if not isinstance(config, Mapping):
        raise ValueError('checks_config 必须是映射')
    values = dict(config)
    if any(not isinstance(key, str) for key in values):
        raise ValueError('检查配置键必须是字符串')
    unknown = set(values) - _KEYS
    if unknown:
        raise ValueError('未知检查配置键: ' + ', '.join(sorted(unknown)))
    for name in _THRESHOLDS:
        if name in values:
            values[name] = _finite(values[name], name)
            if not 0 <= values[name] <= 100:
                raise ValueError(f'{name} 必须在 0..100 之间')
    thresholds = [values[name] for name in _THRESHOLDS if name in values]
    if any(left >= right for left, right in zip(thresholds, thresholds[1:])):
        raise ValueError('电量阈值须满足 emergency < critical < warning（仅比较已配置项）')
    for name in _TIMES:
        if name in values:
            values[name] = _finite(values[name], name)
            if values[name] <= 0:
                raise ValueError(f'{name} 必须为正数')
    for name in _FLAGS:
        if name in values and not isinstance(values[name], bool):
            raise ValueError(f'{name} 必须是 bool')
    for name in _SEQUENCES:
        if name in values:
            sequence = values[name]
            if not isinstance(sequence, (list, tuple)) or any(not isinstance(x, str) or not x.strip() for x in sequence):
                raise ValueError(f'{name} 必须是非空字符串组成的 list/tuple')
            if name == 'allowed_flight_modes' and not sequence:
                raise ValueError('allowed_flight_modes 不能是空序列')
            values[name] = tuple(dict.fromkeys(sequence))
    if _required_fields(values) and 'telemetry_timeout_s' not in values:
        raise ValueError('启用遥测检查必须配置 telemetry_timeout_s')
    return MappingProxyType(values)


def _required_fields(config: CheckConfig) -> tuple[str, ...]:
    fields = set(config.get('required_telemetry', ()))
    if any(name in config for name in _THRESHOLDS):
        fields.add('battery')
    if config.get('position_required', False):
        fields.add('position')
    if config.get('geofence_required', False):
        fields.add('geofence')
    if 'allowed_flight_modes' in config:
        fields.add('flight')
    if 'command_timeout_s' in config:
        fields.add('command')
    return tuple(sorted(fields))


def _event(snapshot: TelemetrySnapshot, name: str, level: SafetyLevel, reason: str,
           value: float | str | bool | None = None) -> SafetyEvent:
    return SafetyEvent(name, level, reason, snapshot.captured_at, value)


def _freshness_issue(snapshot: TelemetrySnapshot, field: str, config: CheckConfig) -> str | None:
    stamp = snapshot.updated_at.get(field)
    if stamp is None:
        return f'{field} 缺少更新时间'
    age = snapshot.captured_at - stamp
    if age < 0:
        return f'{field} 更新时间晚于快照，时间基准或快照不一致'
    if age >= config['telemetry_timeout_s']:
        return f'{field} 遥测已过期'
    return None


def run_checks(snapshot: TelemetrySnapshot, config: CheckConfig) -> tuple[SafetyEvent, ...]:
    """执行配置启用的检查；缺失/过期数据产生 UNKNOWN 事件。"""
    config = validate_config(config)
    if not isinstance(snapshot, TelemetrySnapshot):
        raise ValueError('snapshot 必须是 TelemetrySnapshot')
    enabled = bool(_required_fields(config)) or 'heartbeat_timeout_s' in config
    if not enabled:
        return (_event(snapshot, 'CHECKS_DISABLED', SafetyLevel.UNKNOWN, '未启用任何安全检查'),)
    checks = (check_battery, check_heartbeat, check_position, check_flight_status,
              check_geofence, check_telemetry_freshness, check_command_stuck)
    return tuple(event for check in checks if (event := check(snapshot, config)) is not None)


def check_battery(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if not any(name in config for name in _THRESHOLDS):
        return None
    problem = _freshness_issue(snapshot, 'battery', config)
    if problem or snapshot.battery_percent is None:
        return _event(snapshot, 'BATTERY_UNKNOWN', SafetyLevel.UNKNOWN, problem or '没有有效电量读数')
    for key, name, level in (
        ('battery_emergency_percent', 'LOW_BATTERY_EMERGENCY', SafetyLevel.EMERGENCY),
        ('battery_critical_percent', 'LOW_BATTERY_CRITICAL', SafetyLevel.CRITICAL),
        ('battery_warning_percent', 'LOW_BATTERY_WARNING', SafetyLevel.WARNING),
    ):
        if key in config and snapshot.battery_percent <= config[key]:
            return _event(snapshot, name, level, f'电量不高于配置阈值 {config[key]}%', snapshot.battery_percent)
    return None


def check_heartbeat(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if 'heartbeat_timeout_s' not in config:
        return None
    if snapshot.link_connected is False:
        return _event(snapshot, 'LINK_LOST', SafetyLevel.CRITICAL, '连接状态明确为断开')
    if snapshot.heartbeat_at is None:
        return _event(snapshot, 'HEARTBEAT_UNKNOWN', SafetyLevel.UNKNOWN, '尚未观测到心跳')
    age = snapshot.captured_at - snapshot.heartbeat_at
    if age < 0:
        return _event(snapshot, 'HEARTBEAT_UNKNOWN', SafetyLevel.UNKNOWN, '心跳时间晚于快照')
    if age >= config['heartbeat_timeout_s']:
        return _event(snapshot, 'HEARTBEAT_TIMEOUT', SafetyLevel.CRITICAL, '心跳已超过配置等待时限', age)
    return None


def check_position(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if not config.get('position_required', False):
        return None
    problem = _freshness_issue(snapshot, 'position', config)
    if problem or snapshot.position_valid is None:
        return _event(snapshot, 'POSITION_UNKNOWN', SafetyLevel.UNKNOWN, problem or '定位有效性未知')
    if not snapshot.position_valid:
        return _event(snapshot, 'POSITION_INVALID', SafetyLevel.CRITICAL, '定位有效性检查未通过', False)
    return None


def check_flight_status(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if 'allowed_flight_modes' not in config:
        return None
    problem = _freshness_issue(snapshot, 'flight', config)
    if problem or snapshot.flight_mode is None or snapshot.armed is None:
        return _event(snapshot, 'FLIGHT_STATE_UNKNOWN', SafetyLevel.UNKNOWN, problem or '缺少模式或解锁状态')
    if snapshot.flight_mode not in config['allowed_flight_modes']:
        return _event(snapshot, 'FLIGHT_MODE_UNEXPECTED', SafetyLevel.WARNING,
                      '当前模式不在配置允许范围内', snapshot.flight_mode)
    return None


def check_geofence(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if not config.get('geofence_required', False):
        return None
    problem = _freshness_issue(snapshot, 'geofence', config)
    if problem or snapshot.inside_geofence is None:
        return _event(snapshot, 'GEOFENCE_UNKNOWN', SafetyLevel.UNKNOWN, problem or '没有可用围栏判断')
    if not snapshot.inside_geofence:
        return _event(snapshot, 'GEOFENCE_BREACH', SafetyLevel.CRITICAL, '围栏判断为越界', False)
    return None


def check_telemetry_freshness(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    problems = [problem for field in _required_fields(config)
                if (problem := _freshness_issue(snapshot, field, config)) is not None]
    if problems:
        return _event(snapshot, 'TELEMETRY_UNAVAILABLE', SafetyLevel.UNKNOWN, '; '.join(problems))
    return None


def check_command_stuck(snapshot: TelemetrySnapshot, config: CheckConfig) -> SafetyEvent | None:
    config = validate_config(config)
    if 'command_timeout_s' not in config:
        return None
    problem = _freshness_issue(snapshot, 'command', config)
    if problem or snapshot.command_active is None:
        return _event(snapshot, 'COMMAND_STATE_UNKNOWN', SafetyLevel.UNKNOWN, problem or '当前命令状态未知')
    if not snapshot.command_active:
        return None
    if snapshot.command_started_at is None:
        return _event(snapshot, 'COMMAND_STATE_UNKNOWN', SafetyLevel.UNKNOWN, '运行中命令缺少开始时间')
    duration = snapshot.captured_at - snapshot.command_started_at
    if duration < 0:
        return _event(snapshot, 'COMMAND_STATE_UNKNOWN', SafetyLevel.UNKNOWN, '命令开始时间晚于快照')
    if duration >= config['command_timeout_s']:
        return _event(snapshot, 'COMMAND_STUCK', SafetyLevel.CRITICAL,
                      '当前命令等待超过配置时限；这不等于飞机已经失控', duration)
    return None
