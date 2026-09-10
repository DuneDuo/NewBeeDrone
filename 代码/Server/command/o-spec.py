"""命令定义层：CommandSpec + load_specs。

回答"每条命令是什么"：
  1. completion 常量 —— 完成判据模式
  2. CommandSpec     —— 定义表：一行一种命令（静态）
  3. load_specs      —— commands.json → {命令名: CommandSpec}

注意：把字典转译成"完整命令函数"这一步在引擎层 command.py 的 _bind 里做，
     因为完整函数需要引擎能力（构造/发送/追踪），定义层是纯数据，不掺引擎。
"""
import json
from dataclasses import dataclass

import pymavlink.dialects.v20.common as common


# ============================================================
# 一、completion 模式常量：这条命令"算完成"靠什么判断
# ============================================================
ON_ACK = "on_ack"              # 收到终态 ack 即完成（arm / set_mode）
ON_FINAL_ACK = "on_final_ack"  # IN_PROGRESS 后等终态 ack（校准类）
ON_TELEMETRY = "on_telemetry"  # ACCEPTED 后等遥测谓词（takeoff / land / rtl）


# ============================================================
# 二、CommandSpec：定义表，一行一种命令（静态）
# ============================================================

# @dataclass 自动帮你写 __init__。没有它你得手写 10 行 self.xxx = xxx；
# 有了它，下面声明 10 个字段，__init__ 自动生成。
@dataclass
class CommandSpec:
    """一行命令定义。来自 commands.json 的一行，运行时不变。

    例：takeoff = CommandSpec(name="takeoff", cmd=22, signature=("alt",),
                             params={7: "alt"}, idempotent=False,
                             completion="on_telemetry", ...)
    """

    name: str                   # 语义名，如 "takeoff"。三合一：JSON 的 key = 方法名 = 台账外键
    cmd: int                    # MAV_CMD 号，如 22（加载时从字符串名 getattr 转来）
    signature: tuple            # 实参名顺序，如 ("alt",) / ("x","y","z")。决定 takeoff(10) 里 10 叫什么
    params: dict                # 参数模板，{槽位int: 实参名str 或 字面量}，如 {7: "alt"} / {1: 1}
    idempotent: bool            # 能否安全重发（True=重发无副作用，False=重发前先"读回"）
    completion: str             # 完成判据模式：on_ack / on_final_ack / on_telemetry

    # 下面 4 个有默认值（选填）
    effect_check: object = None     # 生效谓词：判断"命令有没有生效"（非幂等重发前读回用）
    complete_check: object = None   # 完成谓词：判断"目标状态达没达到"（查飞机状态）
    timeout: float = 5.0            # 完成超时（机动/进度型用）
    max_retry: int = 3              # 重试上限
    # 注意：必填的（前 6 个）必须排在选填的（后 4 个）前面，这是 dataclass 的规矩


# ============================================================
# 三、加载：commands.json → {命令名: CommandSpec}
# ============================================================

def _cmd_id(name):
    """把字符串 MAV_CMD 名转成数字，如 "MAV_CMD_NAV_TAKEOFF" -> 22。"""
    return getattr(common, name)
    # getattr(common, "MAV_CMD_NAV_TAKEOFF") 等价于 common.MAV_CMD_NAV_TAKEOFF
    # 区别：getattr 第二个参数可以是字符串变量，能动态查。JSON 里存的是字符串，必须用它。


def _param_value(v):
    """处理 params 里一个 value 的三种情况：
    - 字符串 "alt" -> 原样保留（实参名，引擎 build 时再取值）
    - 数字/布尔    -> 原样保留（字面量）
    - None(null)   -> float('nan') 表示"用默认"
    """
    return float("nan") if v is None else v


def _make_check(spec, checks):
    """把 JSON 里的 {"state":...} 或 {"check":...} 变成一个判断函数。"""
    if spec is None:          # JSON 里根本没写 effect/complete 字段
        return None           #   返回 None，表示"这条命令不用判完成"
    if "state" in spec:       # 写的是 {"state": "hover"} 这种
        s = spec["state"]     #   取出状态名，如 "hover"
        if isinstance(s, str):                       # s 是字符串（单状态）
            return lambda d: d.state.current == s    #   返回"飞机状态==hover"的判断函数
        return lambda d: d.state.current in s        # s 是列表（多状态），判"在其中"
    if "check" in spec:       # 写的是 {"check": "arrived"} 这种
        return checks[spec["check"]]   # 从 checks 注册表里按名字取现成的函数
    raise ValueError(f"谓词格式不认识: {spec}")


def load_specs(path, checks=None):
    """入口：读 JSON 文件，返回 {命令名: CommandSpec 对象}。"""
    checks = checks or {}     # checks 没传(是 None)就当成空字典 {}，防止 checks["x"] 报错
    with open(path, encoding="utf-8") as f:   # 打开文件，用完自动关闭
        raw = json.load(f)                    # json.load 把 JSON 文本解析成 Python 的 dict
    # 现在 raw 就是整个 commands.json，比如 {"arm": {...}, "takeoff": {...}}

    specs = {}                 # 空字典，装最终结果
    for name, d in raw.items():   # 遍历：name=命令名，d=它的定义 dict
        specs[name] = CommandSpec(    # 用 d 的数据 new 一个 CommandSpec，存进 specs
            name=name,
            cmd=_cmd_id(d["cmd"]),    # "MAV_CMD_NAV_TAKEOFF" -> 数字 22
            signature=tuple(d.get("signature", [])),   # ["alt"] -> ("alt",) 元组
            params={int(k): _param_value(v) for k, v in d.get("params", {}).items()},
            # ↑ 字典推导式：把 {"1": 1} 变成 {1: 1}（JSON 的 key 是字符串，转回整数槽位）
            idempotent=d.get("idempotent", False),
            completion=d.get("completion", "on_ack"),
            effect_check=_make_check(d.get("effect"), checks),
            complete_check=_make_check(d.get("complete"), checks),
            timeout=d.get("timeout", 5.0),
            max_retry=d.get("max_retry", 3),
        )
    return specs


if __name__ == "__main__":
    # 自测：直接 python models/cmd.py，验证 JSON 加载成功
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    specs = load_specs(os.path.join(here, "commands.json"))
    for name, s in specs.items():
        print(f"{name}: cmd={s.cmd} params={s.params} completion={s.completion}")
