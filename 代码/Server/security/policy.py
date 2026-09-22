"""纯策略：事件 → 一个决策，不执行 Command。

规则由公共配置提供，不内置低电量返航映射。使用 SafetyRule(action, priority,
max_age_s) 明确控制动作优先级和数据有效期。保留 SafetyAction 的简写格式，但
简写控制动作没有 max_age_s，只产生配置不完整告警；WARN 简写可直接使用。
仲裁顺序是配置 priority、事件严重程度；同级不同动作冲突时告警，绝不按字典
顺序或假设 LAND 总比 RTL 更安全来挑选。动作去重和失败重试由 Manager 管理。

装配示例（变量值来自项目公共配置，不是本模块的默认规则）：
    rules = {
        "LOW_BATTERY_CRITICAL": SafetyRule(
            SafetyAction.RTL, priority=rtl_priority, max_age_s=telemetry_timeout_s,
        ),
    }
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Sequence

from .models import SafetyAction, SafetyDecision, SafetyEvent, SafetyLevel, SafetyRule, TelemetrySnapshot

PolicyRules = Mapping[str, SafetyAction | SafetyRule]
_SEVERITY = {SafetyLevel.NORMAL: 0, SafetyLevel.UNKNOWN: 1, SafetyLevel.WARNING: 2,
             SafetyLevel.CRITICAL: 3, SafetyLevel.EMERGENCY: 4}


def validate_rules(rules: PolicyRules) -> Mapping[str, SafetyRule]:
    """复制为不可变规则映射，保留显式优先级和有效期；不补控制阈值。"""
    if not isinstance(rules, Mapping):
        raise ValueError('policy_rules 必须是映射')
    normalized = {}
    for name, value in rules.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError('策略事件名称必须为非空字符串')
        if isinstance(value, SafetyAction):
            value = SafetyRule(value)
        if not isinstance(value, SafetyRule):
            raise ValueError('策略值必须是 SafetyAction 或 SafetyRule')
        normalized[name] = value
    return MappingProxyType(normalized)


def _fresh(stamp: float | None, now: float, limit: float) -> bool:
    return stamp is not None and 0 <= now - stamp < limit


def _blocked(event: SafetyEvent, rule: SafetyRule, snapshot: TelemetrySnapshot) -> str | None:
    if event.level == SafetyLevel.UNKNOWN:
        return '异常依据未知，不自动执行飞行动作'
    if rule.max_age_s is None:
        return '控制规则缺少 max_age_s，未授权使用无有效期的数据执行动作'
    now = snapshot.captured_at
    if not _fresh(event.observed_at, now, rule.max_age_s):
        return '事件已过期或来自未来时间'
    if snapshot.link_connected is not True or not _fresh(snapshot.heartbeat_at, now, rule.max_age_s):
        return '链路或心跳不可确认，不能把发送尝试视为有效控制'
    if snapshot.armed is not True:
        return '飞行器未解锁或解锁状态未知，不自动发送飞行动作'
    if snapshot.flight_mode is None:
        return '飞行模式未知'
    if not _fresh(snapshot.updated_at.get('flight'), now, rule.max_age_s):
        return '飞行状态已过期或缺失'
    if rule.action in (SafetyAction.HOLD, SafetyAction.RTL):
        if snapshot.position_valid is not True or not _fresh(snapshot.updated_at.get('position'), now, rule.max_age_s):
            return '保持/返航所需定位未确认或已过期'
    if snapshot.action_ready.get(rule.action) is not True:
        return f'{rule.action.value} 动作条件尚未由适配层确认'
    if not _fresh(snapshot.updated_at.get('action_ready'), now, rule.max_age_s):
        return '动作条件判断已过期或缺失'
    return None


def evaluate(events: Sequence[SafetyEvent], snapshot: TelemetrySnapshot, rules: PolicyRules) -> SafetyDecision | None:
    """返回最高优先级事件对应决策，无异常返回 None。

    未映射事件保留为 WARN；同级动作冲突、控制条件不足、UNKNOWN 事件均转为 WARN，
    不擅自降级成另一个飞行动作。优先级最高的决策不可执行时，不悄悄选择低优先级
    控制动作。恢复只表示事件消失，不自动恢复业务或改变已生效的飞行模式。
    """
    if not isinstance(snapshot, TelemetrySnapshot):
        raise ValueError('snapshot 必须是 TelemetrySnapshot')
    if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
        raise ValueError('events 必须是 SafetyEvent 序列')
    normalized = validate_rules(rules)
    candidates = []
    for event in events:
        if not isinstance(event, SafetyEvent):
            raise ValueError('events 必须只包含 SafetyEvent')
        if event.level != SafetyLevel.NORMAL:
            rule = normalized.get(event.type, SafetyRule(SafetyAction.WARN))
            candidates.append((event, rule))
    if not candidates:
        return None
    highest = max((rule.priority, _SEVERITY[event.level]) for event, rule in candidates)
    selected = sorted(
        [(event, rule) for event, rule in candidates if (rule.priority, _SEVERITY[event.level]) == highest],
        key=lambda pair: (pair[0].type, pair[0].reason, pair[0].observed_at),
    )
    chosen_events = tuple(event for event, _ in selected)
    names = ', '.join(sorted({event.type for event in chosen_events}))
    actions = {rule.action for _, rule in selected}
    if len(actions) != 1:
        return SafetyDecision(SafetyAction.WARN, f'同级策略动作冲突，需明确优先级: {names}', chosen_events)
    action = next(iter(actions))
    if action == SafetyAction.WARN:
        missing = sorted({event.type for event in chosen_events if event.type not in normalized})
        reason = ('事件未配置处置规则，仅告警: ' + ', '.join(missing)) if missing else ('策略要求告警: ' + names)
        return SafetyDecision(action, reason, chosen_events)
    problems = sorted({problem for event, rule in selected if (problem := _blocked(event, rule, snapshot))})
    if problems:
        return SafetyDecision(SafetyAction.WARN, f'{names}: ' + '; '.join(problems), chosen_events)
    return SafetyDecision(action, f'按已配置策略执行 {action.value}: {names}', chosen_events)
