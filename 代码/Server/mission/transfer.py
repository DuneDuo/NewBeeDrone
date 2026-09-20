"""Mission 协议事务；共享接收线程仅调用 on_message，不读取连接。

send(name, payload) 由装配层注入，负责目标地址、编码及可靠发送；失败必须抛异常。
on_message 输入须已按来源 system/component、目标和当前事务过滤。
仅处理普通飞行计划(mission_type=0)及 MISSION_ITEM_INT。支持坐标系 5/6/11
和非位置参数坐标系 2。每个 Upload/Download 对象只能运行一次。
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import math
import threading
import time
from typing import Callable, Iterator, Mapping, Sequence

from .models import MissionBusyError, MissionError, MissionItem, MissionProgress, MissionTimeoutError

SendMessage = Callable[[str, Mapping[str, object]], None]
SetCurrentCommand = Callable[[int, float], None]
_ACCEPTED = 0
_CANCELLED = 15
_GLOBAL_FRAMES = {5, 6, 11}
_INT32_MAX = 2**31 - 1


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} 必须为有限正数")
    return float(value)


def _integer(value: object, name: str, maximum: int = 65535, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} 必须为 {minimum}..{maximum} 的整数")
    return value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("任务参数必须为数值")
    result = float(value)
    if math.isinf(result) or (math.isfinite(result) and abs(result) > 3.402823466e38):
        raise ValueError("参数超出 float32 范围")
    return result  # NaN 可表示未指定参数，具体合法性由指令层校验。


def _encode_item(item: MissionItem) -> dict[str, object]:
    _integer(item.seq, "seq")
    _integer(item.command, "command")
    _integer(item.frame, "frame", 255)
    if item.frame not in _GLOBAL_FRAMES | {2}:
        raise ValueError("仅支持全球 INT 坐标系及 MAV_FRAME_MISSION")
    if len(item.params) != 7 or not isinstance(item.autocontinue, bool):
        raise ValueError("任务项需 7 个参数，autocontinue 需为 bool")
    p = tuple(_number(value) for value in item.params)
    xy = []
    for value, limit in zip(p[4:6], (90, 180)):
        if math.isnan(value):
            xy.append(_INT32_MAX)
        elif item.frame in _GLOBAL_FRAMES:
            if abs(value) > limit:
                raise ValueError("经纬度超出范围")
            xy.append(round(value * 1e7))
        else:
            if not value.is_integer() or not -(2**31) <= value < _INT32_MAX:
                raise ValueError("非位置 param5/6 必须是 int32；INT32_MAX 保留给未指定值")
            xy.append(int(value))
    return dict(seq=item.seq, command=item.command, frame=item.frame,
                current=0, autocontinue=int(item.autocontinue),
                param1=p[0], param2=p[1], param3=p[2], param4=p[3],
                x=xy[0], y=xy[1], z=p[6], mission_type=0)


def _decode_item(payload: Mapping[str, object]) -> MissionItem:
    frame = _integer(payload["frame"], "frame", 255)
    if frame not in _GLOBAL_FRAMES | {2}:
        raise ValueError(f"不支持的任务坐标系: {frame}")
    xy = [_integer(payload[key], key, _INT32_MAX, -(2**31)) for key in ("x", "y")]
    coords = [math.nan if value == _INT32_MAX else value / (1e7 if frame in _GLOBAL_FRAMES else 1) for value in xy]
    params = tuple(_number(payload[f"param{i}"]) for i in range(1, 5)) + tuple(coords) + (_number(payload["z"]),)
    item = MissionItem(
        seq=_integer(payload["seq"], "seq"), command=_integer(payload["command"], "command"),
        frame=frame, params=params,  # type: ignore[arg-type]
        autocontinue=bool(_integer(payload["autocontinue"], "autocontinue", 1)),
    )
    _encode_item(item)
    return item


class _PeerRejected(MissionError):
    """远端已经终止事务，无需再发送取消。"""


class _Session:
    """有界消息队列和响应计时；发送和处理消息都在 run 所在线程执行。"""

    def __init__(self, send: SendMessage, *, timeout_s: float, max_retries: int, retry_interval_s: float) -> None:
        if not callable(send):
            raise ValueError("send 必须可调用")
        self._send = send
        self._timeout = _positive(timeout_s, "timeout_s")
        self._retry_interval = _positive(retry_interval_s, "retry_interval_s")
        self._max_retries = _integer(max_retries, "max_retries")
        self._condition = threading.Condition()
        self._queue: deque[tuple[str, dict[str, object]]] = deque()
        self._active = False
        self._used = False
        self._error: MissionError | None = None
        self._progress = MissionProgress(0, None)
        self._last: tuple[str, dict[str, object]] | None = None
        self._deadline = self._next_retry = 0.0
        self._retries = 0

    @contextmanager
    def _running(self) -> Iterator[None]:
        with self._condition:
            if self._used:
                raise MissionBusyError("事务对象只允许 run 一次，请创建新事务")
            self._used = self._active = True
            self._deadline = time.monotonic() + self._timeout
        try:
            yield
        except Exception as exc:
            if not isinstance(exc, _PeerRejected):
                try:
                    self._send("MISSION_ACK", {"type": _CANCELLED, "mission_type": 0})
                except Exception:
                    pass  # 不覆盖首次失败原因。
            if isinstance(exc, MissionError):
                raise
            raise MissionError(f"任务协议操作失败: {exc}") from exc
        finally:
            with self._condition:
                self._active = False
                self._queue.clear()

    def on_message(self, name: str, payload: Mapping[str, object]) -> None:
        """仅投递已过滤来源的消息；不发送、不等待网络响应。"""
        if name not in {"MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_COUNT", "MISSION_ITEM_INT", "MISSION_ACK"}:
            return
        if payload.get("mission_type", 0) != 0:
            return
        with self._condition:
            if not self._active:
                return
            if len(self._queue) >= 128:
                self._error = MissionError("Mission 接收队列溢出")
            else:
                self._queue.append((name, dict(payload)))
            self._condition.notify()

    def progress(self) -> MissionProgress:
        """返回已传输项数；不表示飞行进度或远端确认成功。"""
        with self._condition:
            return self._progress

    def _set_progress(self, done: int, total: int | None) -> None:
        with self._condition:
            self._progress = MissionProgress(done, total)

    def _request(self, name: str, payload: Mapping[str, object]) -> None:
        self._last = (name, dict(payload, mission_type=0))
        self._retries = 0
        self._resend()

    def _resend(self) -> None:
        assert self._last is not None
        name, payload = self._last
        self._send(name, dict(payload))
        self._next_retry = time.monotonic() + self._retry_interval

    def _next(self) -> tuple[str, dict[str, object]]:
        while True:
            with self._condition:
                if self._error is not None:
                    raise self._error
                now = time.monotonic()
                if now >= self._deadline:
                    raise MissionTimeoutError("任务事务总超时，远端结果未知")
                if now < self._next_retry:
                    if self._queue:
                        return self._queue.popleft()
                    self._condition.wait(min(self._deadline, self._next_retry) - now)
                    continue
                if self._retries >= self._max_retries:
                    raise MissionTimeoutError("等待任务响应失败，已达到重试上限")
                self._retries += 1
            self._resend()

    @staticmethod
    def _ack(payload: Mapping[str, object]) -> None:
        result = _integer(payload["type"], "MISSION_ACK.type", 255)
        if result != _ACCEPTED:
            raise _PeerRejected(f"飞控拒绝任务操作，MISSION_ACK.type={result}")


class UploadTransfer(_Session):
    """按飞控请求上传；timeout_s 为总时限，max_retries 为每阶段超时重试次数。"""

    def __init__(self, send: SendMessage, items: Sequence[MissionItem], *, timeout_s: float, max_retries: int, retry_interval_s: float = 1.5) -> None:
        super().__init__(send, timeout_s=timeout_s, max_retries=max_retries, retry_interval_s=retry_interval_s)
        self._items = tuple(_encode_item(item) for item in items)
        _integer(len(self._items), "count")
        if any(item["seq"] != seq for seq, item in enumerate(self._items)):
            raise ValueError("任务序号必须从 0 连续递增")
        self._set_progress(0, len(self._items))

    def run(self) -> None:
        """成功返回 None；拒绝/坏消息抛 MissionError，超时抛 MissionTimeoutError。"""
        with self._running():
            self._request("MISSION_COUNT", {"count": len(self._items)})
            sent: set[int] = set()
            while True:
                name, payload = self._next()
                if name == "MISSION_ACK":
                    self._ack(payload)
                    if len(sent) != len(self._items):
                        raise MissionError("任务尚未传完却收到成功 ACK")
                    return
                if name not in {"MISSION_REQUEST_INT", "MISSION_REQUEST"}:
                    continue
                seq = _integer(payload["seq"], "seq")
                if seq >= len(self._items):
                    raise MissionError(f"请求序号越界: {seq}")
                if seq not in sent and seq != len(sent):
                    # 未按序请求时重新发送上一消息，不刷新阶段期限。
                    assert self._last is not None
                    self._send(self._last[0], dict(self._last[1]))
                    continue
                if seq in sent:
                    self._send("MISSION_ITEM_INT", dict(self._items[seq]))
                else:
                    self._request("MISSION_ITEM_INT", self._items[seq])
                    sent.add(seq)
                    self._set_progress(len(sent), len(self._items))


class DownloadTransfer(_Session):
    """按序下载；重复/乱序项触发重请求，不返回部分计划。

    最后 ACK 发送后保留有界应答窗口，处理 ACK 丢失导致的最后一项重发。
    窗口最多 (max_retries+1)*retry_interval_s，不超过事务总截止时间。
    """

    def __init__(self, send: SendMessage, *, timeout_s: float, max_retries: int, retry_interval_s: float = 1.5) -> None:
        super().__init__(send, timeout_s=timeout_s, max_retries=max_retries, retry_interval_s=retry_interval_s)

    def run(self) -> tuple[MissionItem, ...]:
        with self._running():
            self._request("MISSION_REQUEST_LIST", {})
            count: int | None = None
            items: list[MissionItem] = []
            while True:
                name, payload = self._next()
                if name == "MISSION_ACK":
                    self._ack(payload)
                    raise MissionError("下载未完成时收到意外成功 ACK")
                if name == "MISSION_COUNT":
                    received = _integer(payload["count"], "count")
                    if count is not None:
                        if count != received:
                            raise MissionError("下载过程中任务数量发生变化")
                        continue
                    count = received
                    self._set_progress(0, count)
                    if count == 0:
                        self._complete_download(None)
                        return ()
                    self._request("MISSION_REQUEST_INT", {"seq": 0})
                elif name == "MISSION_ITEM_INT" and count is not None:
                    seq = _integer(payload["seq"], "seq")
                    if seq != len(items):
                        self._send("MISSION_REQUEST_INT", {"seq": len(items), "mission_type": 0})
                        continue
                    items.append(_decode_item(payload))
                    self._set_progress(len(items), count)
                    if len(items) == count:
                        self._complete_download(count - 1)
                        return tuple(items)
                    self._request("MISSION_REQUEST_INT", {"seq": len(items)})

    def _complete_download(self, last_seq: int | None) -> None:
        ack = {"type": _ACCEPTED, "mission_type": 0}
        self._send("MISSION_ACK", dict(ack))
        end = min(self._deadline, time.monotonic() + (self._max_retries + 1) * self._retry_interval)
        while True:
            with self._condition:
                if self._error is not None:
                    raise self._error
                remaining = end - time.monotonic()
                if remaining <= 0:
                    return
                if not self._queue:
                    self._condition.wait(remaining)
                    continue
                name, payload = self._queue.popleft()
            if (last_seq is not None and name == "MISSION_ITEM_INT" and payload.get("seq") == last_seq
                    or last_seq is None and name == "MISSION_COUNT" and payload.get("count") == 0):
                self._send("MISSION_ACK", dict(ack))


class PlanOperations:
    """清空走 Mission 协议；设置当前项委托统一 Command 事务适配。

    set_current_command(seq, timeout_s) 必须等待适用确认，失败抛异常。
    不直接发送 COMMAND_LONG，不另建命令 ACK 处理器。各类计划操作间的
    全局互斥由 MissionManager 负责，本对象额外防止自身被并发调用。
    """

    def __init__(self, send: SendMessage, set_current_command: SetCurrentCommand | None = None, *, max_retries: int = 3, retry_interval_s: float = 1.5) -> None:
        if not callable(send):
            raise ValueError("send 必须可调用")
        if set_current_command is not None and not callable(set_current_command):
            raise ValueError("set_current_command 必须可调用")
        self._send = send
        self._set_current_command = set_current_command
        self._max_retries = _integer(max_retries, "max_retries")
        self._retry_interval = _positive(retry_interval_s, "retry_interval_s")
        self._operation_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._active: _Session | None = None

    def clear(self, *, timeout_s: float) -> None:
        session = _Session(self._send, timeout_s=timeout_s, max_retries=self._max_retries, retry_interval_s=self._retry_interval)
        if not self._operation_lock.acquire(blocking=False):
            raise MissionBusyError("已有计划管理操作")
        try:
            with self._state_lock:
                self._active = session
            with session._running():
                session._request("MISSION_CLEAR_ALL", {})
                while True:
                    name, payload = session._next()
                    if name == "MISSION_ACK":
                        session._ack(payload)
                        return
        finally:
            with self._state_lock:
                self._active = None
            self._operation_lock.release()

    def set_current(self, seq: int, *, timeout_s: float) -> None:
        _integer(seq, "seq")
        timeout_s = _positive(timeout_s, "timeout_s")
        if self._set_current_command is None:
            raise MissionError("尚未注入 Command 的 set_current 事务适配")
        if not self._operation_lock.acquire(blocking=False):
            raise MissionBusyError("已有计划管理操作")
        try:
            result = self._set_current_command(seq, timeout_s)
            if result is not None:
                raise MissionError("set_current 适配必须成功返回 None，失败抛异常")
        except MissionError:
            raise
        except Exception as exc:
            raise MissionError(f"设置当前项失败: {exc}") from exc
        finally:
            self._operation_lock.release()

    def on_message(self, name: str, payload: Mapping[str, object]) -> None:
        with self._state_lock:
            active = self._active
        if active is not None:
            active.on_message(name, payload)
