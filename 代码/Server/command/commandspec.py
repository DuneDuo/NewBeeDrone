import json
from dataclasses import dataclass
from pymavlink.dialects.v20 import common
import command.checks as checks
import config
ON_ACK = "on_ack"
ON_TELEMETRY = "on_telemetry"
ON_FINAL_ACK = "on_final_ack"
@dataclass
class Commandspec:
    name:str
    cmd:int
    signature:tuple
    params:dict
    form: str
    idempotent:bool
    completion:str
    effect:object = None
    complete:object = None
    timeout:float = 5.0
    max_retry:int = 3

def _cmd_id(cmd):
    return getattr(common,cmd)
def _param_value(v):
    return float("nan") if v is None else v
_STATE_FIELDS = {"mode", "armed", "landed_state", "system_status"}
def _make_check(obj):
    if obj is None:
        return None 
    if not isinstance(obj,dict):
        raise ValueError(f"谓词格式错误{obj!r}")
    if "check" in obj:                     # 具名谓词：{"check": "arrived"}
        return getattr(checks, obj["check"])
    if "and" in obj:                       # {"and": [p1, p2, ...]}
        subs = [_make_check(x) for x in obj["and"]]
        return lambda d: all(p(d) for p in subs)
    if "or" in obj:                        # {"or": [p1, p2, ...]}
        subs = [_make_check(x) for x in obj["or"]]
        return lambda d: any(p(d) for p in subs)
    for field in obj:
        if field not in _STATE_FIELDS:
            raise ValueError(f"未知状态字段:{field!r}（可选: {sorted(_STATE_FIELDS)}）")
    def pred(d):
        for field, want in obj.items():
            got = getattr(d.state, field)
            if isinstance(want, list):
                if got not in want:
                    return False
            elif got != want:
                return False
        return True
    return pred
def loadspec():
    with open(config.cmd_spec_path,encoding="UTF-8") as f:
        raw = json.load(f)
        specs = {}
        for name,dic in raw.items():
            specs[name] = Commandspec(
                name = name,
                cmd = _cmd_id(dic["cmd"]),
                signature = tuple(dic.get("signature",[])),
                params = {int(k): _param_value(v) for k,v in dic.get("params",{}).items()},
                form = dic.get("form","long"),
                idempotent = dic.get("idempotent", False),
                completion = dic.get("completion", "on_ack"),
                effect = _make_check(dic.get("effect")),
                complete = _make_check(dic.get("complete")),
                timeout = dic.get("timeout",5.0),
                max_retry = dic.get("max_retry",3)
                )
        return specs

        
