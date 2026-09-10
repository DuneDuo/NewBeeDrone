import os
import config
import time
import threading
import json
from datetime import datetime
from collections import deque
from logger import logger
from .commandspec import (loadspec,ON_TELEMETRY)
from .commandrecord import (Command,SENT,EXECUTING,DONE,FAIL,ERROR_DENIED,ERROR_FAILED,ERROR_UNSPPORTED,ERROR_LINK_LOST,ERROR_TIMEOUT)
from pymavlink.dialects.v20.common import (
    MAV_RESULT_ACCEPTED,
    MAV_RESULT_IN_PROGRESS,
    MAV_RESULT_TEMPORARILY_REJECTED,
    MAV_RESULT_DENIED,
    MAV_RESULT_UNSUPPORTED,
    MAV_RESULT_FAILED,
)
_RESULT_FAILURE = {
    MAV_RESULT_DENIED: (ERROR_DENIED,"飞控拒绝该指令"),
    MAV_RESULT_UNSUPPORTED: (ERROR_UNSPPORTED,"飞控不支持该指令"),
    MAV_RESULT_FAILED: (ERROR_FAILED,"执行失败")
}
_RUN_DIR = None
log = logger("command")
def _get_run_dir():
    global _RUN_DIR # ?
    if _RUN_DIR is None:
        _RUN_DIR = os.path.join(config.cmd_log_dir,time.strftime("%Y-%m-%d_%H%M%S"))
        os.makedirs(_RUN_DIR,exist_ok = True)
    return _RUN_DIR
class CommandFailure(Exception):
    def __init__(self, command,reason):
        self.command = command
        self.reason = reason
        super().__init__(f"[命令 {command.name}][RunID {command.run_id}] 异常: {reason}")
class CommandManager:
    def  __init__(self,drone):
        self.drone = drone
        self.current = None
        self.runs = deque(maxlen=50)
        self.specs = loadspec()
        self._seq = 0
        self.lock = threading.Lock()
        self._bind()
    def _bind(self):
        for name,spec in self.specs.items():
            setattr(self,name,self._make(spec))
    def _make(self,spec):
        def command(*args):
            return self._run(spec,*args)
        command.__name__ = spec.name
        log.debug(f"创建命令:{spec.name}")
        return command
    def _run(self,spec,*args):
        self._check_spec(spec)
        c = self._build(spec,*args)
        return self._send(c,spec)
    def _check_spec(self,spec):
        if spec.completion == ON_TELEMETRY and spec.complete is None:
            raise ValueError(f"命令{spec.name}:completion=ON_TELEMETRY 但没写complete谓词")
        if not spec.idempotent and spec.effect is None:
            raise ValueError(f"命令 {spec.name}:idempotent=false 但没写 effect 谓词")
    def _build(self,spec,*args):
        kw = dict(zip(spec.signature,args))
        p = {i:0.0 for i in range(1,8)}
        for slot,src in spec.params.items():
            p[slot] = kw[src] if isinstance(src,str) else src
        return Command(name = spec.name,cmd = spec.cmd,params= p)
    def _send_cmd(self,c):
        p=c.params
        spec = self.specs[c.name]
        if spec.form == "long":
            self.drone.send_command_long(c.cmd,p[1],p[2],p[3],p[4],p[5],p[6],p[7])
        elif spec.form == "int":
            self.drone.send_command_int(c.cmd,p[1],p[2],p[3],p[4],p[5],p[6],p[7])
    def _send(self,c,spec):
        with self.lock:
            c.run_id = self._seq
            self._seq += 1
            c.state = SENT
            c.started_at = c.sent_at = time.time()
            self.current = c
            self.runs.append(c)
        self._send_cmd(c)
        self._record(c,"已发送")
        c.done_event.wait(timeout = spec.timeout + config.cmd_first_ack_timeout*(spec.max_retry+1))
        if c.state == FAIL:
            raise CommandFailure(c,c.detail or c.error)
        return c.result
    def on_ack(self,msg):
        with self.lock:
            c = self.current
            if c is None or c.cmd != msg.command:
                return
            spec = self.specs[c.name]
            result = msg.result
            if result == MAV_RESULT_IN_PROGRESS:        # 进度型，转 EXECUTING 等终态
                c.state = EXECUTING
                self._record(c, f"执行中 进度:{msg.progress}")
                return
            if result == MAV_RESULT_TEMPORARILY_REJECTED:
                c.state = SENT
                self._record(c, "暂时拒绝，待重试")
                return
            self._finish(c, spec, result, msg.result_param2)
    def _finish(self,c,spec,result,param2 = 0):
        c.result = result
        c.done_at = time.time()
        if spec.completion == ON_TELEMETRY and result == MAV_RESULT_ACCEPTED:
            c.state = EXECUTING
            self._record(c,"已受理,转遥控监测")
            return
        if result == MAV_RESULT_ACCEPTED:
            c.state = DONE
            self._move_to_complete(c,"完成")
            return
        error,detail = _RESULT_FAILURE.get(result,(ERROR_FAILED,f"执行失败,飞控返回 result = {result}"))
        if param2:
            detail = f"{detail}(code={param2})"
        c.state = FAIL
        c.error = error
        c.detail = detail
        self._move_to_complete(c,detail)
    def _move_to_complete(self,c,detail):
        self.current = None
        self._record(c,detail)
        if c.done_event:
            c.done_event.set()
    def _record(self,c,detail):
        spec = self.specs[c.name]
        used = {k: c.params.get(k) for k in spec.params}
        log.info(f"[drone_id={self.drone.sys_id}][run_id={c.run_id}] {c.name} {c.state} << {detail} params={used}")
        if c.state in (DONE,FAIL):
            self._append(c)
    def _append(self,c):
        try:
            drone_id = self.drone.sys_id or "unknown"
            path = os.path.join(_get_run_dir(),f"{drone_id}.jsonl")
            with open(path,"a",encoding="utf-8") as f:
                f.write(json.dumps(self._row(c),ensure_ascii=False) + "\n")
        except Exception:
            log.exception(f"[{drone_id}]台账写入失败[{c.run_id}]")
    def _row(self,c):
        return {
            "name": c.name,
            "cmd": c.cmd,
            "params": c.params,
            "run_id": c.run_id,
            "state": c.state,
            "result": c.result,
            "error": c.error,
            "retry_count": c.retry_count,
            "started_at": self._ts(c.started_at),
            "sent_at": self._ts(c.sent_at),
            "done_at": self._ts(c.done_at),
            "detail" : c.detail
        }
    def _ts(self,ts):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f") if ts else None
    def _abort(self,c,error,detail):
        c.error = error
        c.detail = detail
        c.state = FAIL
        c.done_at = time.time()
        self._move_to_complete(c,f"异常:{detail}")
    def abort_inflight(self):
        with self.lock:
            if self.current is not None:
                self._abort(self.current,ERROR_LINK_LOST,"连接中断")
    def _tick(self):
        to_resend = None
        with self.lock:
            c = self.current
            if c is None:
                return
            spec = self.specs[c.name]
            now = time.time()
            if now - c.sent_at >= config.cmd_first_ack_timeout:
                if c.state == SENT:
                    if not spec.idempotent and spec.effect and spec.effect(self.drone):
                        c.state = DONE
                        self._move_to_complete(c,"读回已生效")
                    elif c.retry_count >= spec.max_retry:
                        self._abort(c,ERROR_TIMEOUT,f"已重试{c.retry_count}次,无响应")
                    else:
                        c.retry_count += 1
                        c.sent_at = now
                        to_resend = c
                        self._record(c, f"超时重发 第{c.retry_count}次")
                elif c.state == EXECUTING and spec.completion == ON_TELEMETRY:
                    if spec.complete and spec.complete(self.drone):
                        c.state = DONE
                        self._move_to_complete(c,"遥测达成")
                    elif now - c.sent_at >= spec.timeout:
                        self._abort(c,ERROR_TIMEOUT,"遥测未达成")
                elif c.state == EXECUTING:
                    if now - c.sent_at >= spec.timeout:
                        self._abort(c,ERROR_TIMEOUT,"进度未达成")
        if to_resend:
            self._send_cmd(to_resend)
    def tick_loop(self):
        while self.drone.running:
            self._tick()
            time.sleep(config.cmd_tick_interval)
    