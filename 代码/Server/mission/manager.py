"""Mission 对外入口：串行计划操作、协议分发和只读状态。

每个目标飞机创建一个 Manager，并通过它调用所有计划操作；不要直接并发使用
Transfer/PlanOperations。send 和 on_message 的来源/目标过滤由应用装配层负责。
本模块不注册全局 handler、不建立连接、不创建业务线程、不改变飞行模式。
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import logging
import math
import threading
import time
from typing import Iterator, Mapping, Sequence

from .models import (
    MissionBusyError, MissionError, MissionItem, MissionProgress, MissionStatus,
    TransferState,
)
from .transfer import DownloadTransfer, PlanOperations, SendMessage, UploadTransfer

log = logging.getLogger(__name__)


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} 必须为有限正数")
    return float(value)


def _uint(value: object, name: str, maximum: int = 65535) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"{name} 必须为 0..{maximum} 的整数")
    return value


class MissionManager:
    def __init__(
        self, send: SendMessage, operations: PlanOperations, *, timeout_s: float,
        max_retries: int, retry_interval_s: float = 1.5, status_timeout_s: float = 5.0,
    ) -> None:
        """注入通信、计划操作适配和公共配置，不自动运行。

        timeout_s 是操作总等待上限；retry_interval_s 用于上传/下载，清空的
        重试配置由传入的 PlanOperations 管理。status_timeout_s 是本地观测
        有效期，影响查询结果，不触发飞行动作。各数值可由 Server/config.py 注入。
        """
        if not callable(send):
            raise ValueError("send 必须可调用")
        if not all(callable(getattr(operations, method, None)) for method in ('clear', 'set_current', 'on_message')):
            raise ValueError("operations 必须提供 clear/set_current/on_message")
        self._send = send
        self._operations = operations
        self._timeout = _positive(timeout_s, 'timeout_s')
        self._max_retries = _uint(max_retries, 'max_retries')
        self._retry_interval = _positive(retry_interval_s, 'retry_interval_s')
        self._status_timeout = _positive(status_timeout_s, 'status_timeout_s')
        self._operation_lock = threading.Lock()
        self._lock = threading.RLock()
        self._active: UploadTransfer | DownloadTransfer | PlanOperations | None = None
        self._count_at: float | None = None
        self._current_at: float | None = None
        self._reached_at: float | None = None
        self._current_revision = 0
        self._plan_id: int | None = None
        self._download_count_seen = False
        self._download_changed = False
        self._download_plan_id: int | None = None
        self._download_reported_id: int | None = None
        self._download_reported_count: int | None = None
        self._status = MissionStatus(TransferState.IDLE, None, None, None, None, False, None, None)

    def upload(self, items: Sequence[MissionItem]) -> None:
        """阻塞上传有序计划，空计划等同清空；仅协议确认后记录成功。

        非法参数抛 ValueError；冲突抛 MissionBusyError；协议/适配失败抛
        MissionError（超时为 MissionTimeoutError）。成功返回 None，不启动飞行。
        """
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise ValueError("items 必须是 MissionItem 的有序集合")
        plan = tuple(items)
        if any(not isinstance(item, MissionItem) for item in plan):
            raise ValueError("items 中只能包含 MissionItem")
        transfer = UploadTransfer(self._send, plan, timeout_s=self._timeout,
                                  max_retries=self._max_retries, retry_interval_s=self._retry_interval)
        with self._operation(TransferState.UPLOADING, transfer):
            transfer.run()
            with self._lock:
                self._confirm_count(len(plan), reset_execution=True)

    def download(self) -> tuple[MissionItem, ...]:
        """返回完整有序计划，空元组表示确认的空计划；不会返回半份结果。"""
        transfer = DownloadTransfer(self._send, timeout_s=self._timeout,
                                    max_retries=self._max_retries, retry_interval_s=self._retry_interval)
        with self._operation(TransferState.DOWNLOADING, transfer):
            items = transfer.run()
            with self._lock:
                if (self._download_changed
                        or self._download_reported_count is not None and self._download_reported_count != len(items)
                        or self._download_plan_id is not None and self._download_reported_id is not None
                        and self._download_plan_id != self._download_reported_id):
                    raise MissionError("下载期间观测到远端计划已变化，请重新下载")
                self._confirm_count(len(items), reset_execution=False)
            return items

    def clear(self) -> None:
        """通过 PlanOperations 清空普通计划，确认后数量为 0；不停止飞行。"""
        with self._operation(TransferState.CLEARING, self._operations):
            result = self._operations.clear(timeout_s=self._timeout)
            if result is not None:
                raise MissionError("clear 适配必须成功返回 None，失败抛异常")
            with self._lock:
                self._plan_id = None
                self._confirm_count(0, reset_execution=True)

    def set_current(self, seq: int) -> None:
        """请求切换非负序号；仅依据仍有效的 count 做本地上界检查。

        实际确认由 Command 事务适配负责。若等待期间收到更新的 CURRENT，则保留
        最新观测，不在函数返回时用请求序号覆盖它。成功不意味着任务已开始执行。
        """
        _uint(seq, 'seq')
        # 范围判断在同一把操作锁内完成，防止检查后另一个线程上传新计划。
        if not self._operation_lock.acquire(blocking=False):
            raise MissionBusyError("当前已有 Mission 操作")
        try:
            with self._lock:
                observed = self._snapshot_locked()
                if observed.valid and observed.count is not None and seq >= observed.count:
                    raise ValueError(f"seq={seq} 超出已知计划数量 {observed.count}")
                revision = self._current_revision
            with self._operation(TransferState.SETTING_CURRENT, self._operations, lock_held=True):
                result = self._operations.set_current(seq, timeout_s=self._timeout)
                if result is not None:
                    raise MissionError("set_current 适配必须成功返回 None，失败抛异常")
                with self._lock:
                    if revision == self._current_revision:
                        self._current_at = time.monotonic()
                        self._status = replace(self._status, current_seq=seq, updated_at=self._current_at)
        finally:
            self._operation_lock.release()

    def status(self) -> MissionStatus:
        """返回不可变快照，不发送查询。count/current/reached 分别按各自时间过期。

        valid 表示 count 已确认且未过期，不保证飞机在线或所有字段都有值。
        state 表示最近/当前操作状态，不是业务完成状态。
        """
        with self._lock:
            return self._snapshot_locked()

    def _snapshot_locked(self) -> MissionStatus:
        now = time.monotonic()
        def fresh(timestamp: float | None) -> bool:
            return timestamp is not None and 0 <= now - timestamp < self._status_timeout
        progress = self._status.progress
        if isinstance(self._active, (UploadTransfer, DownloadTransfer)):
            progress = self._active.progress()
        count = self._status.count if fresh(self._count_at) else None
        return replace(
            self._status, count=count,
            current_seq=self._status.current_seq if fresh(self._current_at) else None,
            last_reached=self._status.last_reached if fresh(self._reached_at) else None,
            valid=self._status.valid and count is not None, progress=progress,
        )

    @contextmanager
    def _operation(
        self, state: TransferState, active: UploadTransfer | DownloadTransfer | PlanOperations,
        *, lock_held: bool = False,
    ) -> Iterator[None]:
        if not lock_held and not self._operation_lock.acquire(blocking=False):
            raise MissionBusyError("当前已有 Mission 操作")
        try:
            with self._lock:
                self._active = active
                self._download_count_seen = False
                self._download_changed = False
                self._download_plan_id = self._download_reported_id = self._download_reported_count = None
                if state in (TransferState.UPLOADING, TransferState.CLEARING):
                    self._forget_execution()
                    self._count_at = None
                    self._plan_id = None
                    self._status = replace(self._status, count=None, valid=False)
                self._status = replace(self._status, state=state, progress=None, last_error=None)
            try:
                yield
            except BaseException as exc:
                with self._lock:
                    self._count_at = self._current_at = self._reached_at = None
                    self._status = replace(self._status, state=TransferState.FAILED, valid=False,
                                           count=None, current_seq=None, last_reached=None,
                                           last_error=str(exc) or type(exc).__name__)
                if isinstance(exc, Exception) and not isinstance(exc, MissionError):
                    raise MissionError(f"Mission 操作失败: {exc}") from exc
                raise
            else:
                with self._lock:
                    self._status = replace(self._status, state=TransferState.SUCCESS, last_error=None)
            finally:
                with self._lock:
                    if isinstance(active, (UploadTransfer, DownloadTransfer)):
                        self._status = replace(self._status, progress=active.progress())
                    self._active = None
        finally:
            if not lock_held:
                self._operation_lock.release()

    def _forget_execution(self) -> None:
        self._current_at = self._reached_at = None
        self._status = replace(self._status, current_seq=None, last_reached=None)

    def _confirm_count(self, count: int, *, reset_execution: bool) -> None:
        if reset_execution or count == 0:
            self._forget_execution()
        else:
            if self._status.current_seq is not None and self._status.current_seq >= count:
                self._current_at = None
                self._status = replace(self._status, current_seq=None)
            if self._status.last_reached is not None and self._status.last_reached >= count:
                self._reached_at = None
                self._status = replace(self._status, last_reached=None)
        now = time.monotonic()
        self._count_at = now
        self._status = replace(self._status, count=count, valid=True, updated_at=now)

    def _observe_plan_id(self, value: object) -> None:
        identity = _uint(value, 'mission_id/opaque_id', 2**32 - 1)
        if identity == 0:
            return  # 协议的未提供 ID 标志，不能据此认定两个计划相同。
        if self._plan_id is not None and self._plan_id != identity:
            self._forget_execution()
            self._count_at = None
            self._status = replace(self._status, count=None, valid=False, progress=None)
        self._plan_id = identity

    def on_message(self, name: str, payload: Mapping[str, object]) -> None:
        """接收装配层已过滤来源/目标的消息，更新观测并转交当前事务。

        已结束事务的 ACK 不会改变状态。报文没有通用事务 ID，来源正确的延迟旧包
        仍需装配层隔离；本方法不能证明旧消息属于新事务。坏进度报文会被忽略，
        坏协议响应仍交给 Transfer，使等待者收到协议异常，而不是接收线程崩溃。
        """
        if not isinstance(payload, Mapping):
            log.warning("忽略非法 Mission 消息: payload 不是 Mapping")
            return
        body = dict(payload)
        mission_type = body.get('mission_type', 0)
        if isinstance(mission_type, bool) or not isinstance(mission_type, int) or mission_type != 0:
            return
        with self._lock:
            try:
                if name in ('MISSION_CURRENT', 'MISSION_ITEM_REACHED'):
                    self._observe_progress(name, body)
                elif name == 'MISSION_COUNT' and isinstance(self._active, DownloadTransfer):
                    _uint(body.get('count'), 'count')
                    self._download_count_seen = True
                    if 'opaque_id' in body:
                        identity = _uint(body['opaque_id'], 'opaque_id', 2**32 - 1)
                        if self._download_plan_id is None and identity != 0:
                            self._download_plan_id = identity
                        elif identity != 0 and identity != self._download_plan_id:
                            self._download_changed = True
                        self._observe_plan_id(body['opaque_id'])
                elif name == 'MISSION_ACK' and isinstance(self._active, UploadTransfer) and body.get('type') == 0:
                    if 'opaque_id' in body:
                        self._observe_plan_id(body['opaque_id'])
            except (ValueError, TypeError) as exc:
                log.warning("忽略非法 Mission 观测: %s", exc)
            # on_message 只投递队列；持锁避免刚取到的 active 被后续操作替换。
            # 不持锁调用 send/run，故不会阻塞接收线程等待协议完成。
            if self._active is not None:
                self._active.on_message(name, body)

    def _observe_progress(self, name: str, body: Mapping[str, object]) -> None:
        # 先完成校验，坏消息不应先清掉已有有效状态。
        seq = _uint(body.get('seq'), 'seq')
        total = _uint(body['total'], 'total') if name == 'MISSION_CURRENT' and 'total' in body else None
        identity = _uint(body['mission_id'], 'mission_id', 2**32 - 1) if name == 'MISSION_CURRENT' and 'mission_id' in body else None
        current = None if seq == 65535 else seq
        known_total = None if total == 65535 else total
        if known_total is not None and current is not None and current >= known_total:
            # 空计划固件可能广播 seq=0；这不是可执行的任务项。
            if known_total == 0 and current == 0:
                current = None
            else:
                raise ValueError('CURRENT.seq 超出 CURRENT.total')
        now = time.monotonic()
        if name == 'MISSION_CURRENT' and isinstance(self._active, DownloadTransfer) and self._download_count_seen:
            if identity:
                self._download_reported_id = identity
            if known_total is not None:
                self._download_reported_count = known_total
        if identity is not None:
            self._observe_plan_id(identity)
        if name == 'MISSION_CURRENT':
            self._current_revision += 1
            if total is not None:
                previous_count = self._status.count
                if previous_count is not None and previous_count != known_total:
                    self._reached_at = None
                    self._status = replace(self._status, last_reached=None)
                self._count_at = now if known_total is not None else None
                self._status = replace(self._status, count=known_total, valid=known_total is not None)
                if known_total == 0:
                    self._forget_execution()
            self._current_at = now if current is not None else None
            self._status = replace(self._status, current_seq=current, updated_at=now)
        else:
            self._reached_at = now if current is not None else None
            self._status = replace(self._status, last_reached=current, updated_at=now)
        if current is not None and self._status.count is not None and current >= self._status.count:
            # 来源有效但与旧 count 冲突，保留最新观测，旧数量置未知。
            self._count_at = None
            self._status = replace(self._status, count=None, valid=False)
        if self._status.state in (TransferState.UPLOADING, TransferState.CLEARING) and self._active is not None:
            self._status = replace(self._status, valid=False)
