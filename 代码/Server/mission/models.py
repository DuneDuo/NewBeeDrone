"""Mission 数据模型：不可变参数、传输进度和本地状态。

本模块仅校验表示范围与当前传输实现支持的格式；不推断飞控固件支持哪些 command，
不判断航线可飞性，不执行消息收发。Python 3.10+。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class TransferState(str, Enum):
    IDLE = "idle"
    UPLOADING = "uploading"
    DOWNLOADING = "downloading"
    CLEARING = "clearing"
    SETTING_CURRENT = "setting_current"
    SUCCESS = "success"
    FAILED = "failed"


def _uint16(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535:
        raise ValueError(f"{name} 必须是 0..65535 的整数")
    return value


@dataclass(frozen=True)
class MissionItem:
    """普通计划中的单项，seq 从 0 开始，params 是 param1..param7。

    当前传输支持全球 INT 坐标系 5/6/11，param5/6 为度，param7 为米，高度
    基准由 frame 决定；非位置项用 frame=2，param5/6 为未经缩放的整数。
    NaN 保留为未指定值，具体指令是否允许由上层校验；不能使用无穷大。
    构造时复制参数为 tuple，避免调用方随后修改原列表影响传输。
    """
    seq: int
    command: int
    frame: int
    params: tuple[float, float, float, float, float, float, float]
    autocontinue: bool = True

    def __post_init__(self) -> None:
        _uint16(self.seq, "seq")
        _uint16(self.command, "command")
        _uint16(self.frame, "frame")
        if self.frame not in {2, 5, 6, 11}:
            raise ValueError("frame 仅支持 2(MISSION)、5/6/11(全球 INT 坐标系)")
        if not isinstance(self.autocontinue, bool):
            raise ValueError("autocontinue 必须是 bool")
        if not isinstance(self.params, (tuple, list)) or len(self.params) != 7:
            raise ValueError("params 必须是含 7 个数值的 tuple/list")
        values = []
        for index, value in enumerate(self.params, 1):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"param{index} 必须是数值")
            try:
                number = float(value)
            except OverflowError as exc:
                raise ValueError(f"param{index} 超出浮点范围") from exc
            if math.isinf(number) or math.isfinite(number) and abs(number) > 3.402823466e38:
                raise ValueError(f"param{index} 超出 float32 范围")
            values.append(number)
        for index, limit in ((4, 90), (5, 180)):
            value = values[index]
            if math.isnan(value):
                continue
            if self.frame != 2:
                if abs(value) > limit:
                    raise ValueError(f"param{index + 1} 经纬度超出范围")
            elif not value.is_integer() or not -(2**31) <= value < 2**31 - 1:
                raise ValueError("非位置 param5/6 必须是 int32；INT32_MAX 保留给 NaN")
        object.__setattr__(self, "params", tuple(values))


@dataclass(frozen=True)
class MissionProgress:
    """单次传输计数；total=None 表示尚未取得计划数量，不能计算百分比。"""
    transferred: int
    total: int | None

    def __post_init__(self) -> None:
        _uint16(self.transferred, "transferred")
        if self.total is not None:
            _uint16(self.total, "total")
            if self.transferred > self.total:
                raise ValueError("transferred 不能超过 total")


@dataclass(frozen=True)
class MissionStatus:
    """本地只读快照；state 是操作状态，不是飞机/业务状态。

    valid 只说明 count 已确认且仍有效；不保证所有进度字段都有观测值，也不代表
    飞控在线或航线安全。未知/过期信息用 None。updated_at 是最近一次已接收的
    有效计划信息的单调时钟秒数，查询本身不会更新时间。
    """
    state: TransferState
    count: int | None
    current_seq: int | None
    last_reached: int | None
    updated_at: float | None
    valid: bool
    progress: MissionProgress | None
    last_error: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, TransferState):
            raise ValueError("state 必须是 TransferState")
        if not isinstance(self.valid, bool):
            raise ValueError("valid 必须是 bool")
        for name in ("count", "current_seq", "last_reached"):
            value = getattr(self, name)
            if value is not None:
                _uint16(value, name)
        if self.valid and self.count is None:
            raise ValueError("valid=True 时必须有已确认 count")
        if self.updated_at is not None:
            value = self.updated_at
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("updated_at 必须是有限单调时钟数值或 None")
        if self.progress is not None and not isinstance(self.progress, MissionProgress):
            raise ValueError("progress 必须是 MissionProgress 或 None")
        if self.last_error is not None and not isinstance(self.last_error, str):
            raise ValueError("last_error 必须是 str 或 None")


class MissionError(RuntimeError):
    """计划操作失败；异常文本保存协议拒绝或适配失败原因。"""


class MissionBusyError(MissionError):
    """同一 Manager 正在进行冲突操作；本次请求尚未发送。"""


class MissionTimeoutError(MissionError):
    """操作未在时限内完成；远端最终结果可能仍未知。"""
