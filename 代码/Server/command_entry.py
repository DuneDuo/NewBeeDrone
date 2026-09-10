# 指令入口：给飞控发指令（交互式控制台 + 可编程 send）
from core.drone import Drone


def _pick_drone():
    """取一台已注册的无人机（单机场景直接取第一个）"""
    if not Drone.registry:
        return None
    return next(iter(Drone.registry.values()))


def send(name, *args):
    """按名字给飞控发指令，例如 send('arm')、send('takeoff', 10)。
    指令名对应 commands.json 里的键：arm / disarm / takeoff / land / rtl。"""
    drone = _pick_drone()
    if drone is None:
        print("[指令入口] 暂无已注册无人机，等飞控连上再发")
        return None
    if name not in drone.cmd.specs:
        print(f"[指令入口] 未知指令:{name}（可选: {list(drone.cmd.specs.keys())}）")
        return None
    try:
        result = getattr(drone.cmd, name)(*args)
        print(f"[指令入口] {name}{args} -> {result!r}")
        return result
    except Exception as e:
        print(f"[指令入口] {name}{args} 失败: {e}")
        return None


def _parse_arg(s):
    try:
        return float(s) if ("." in s) else int(s)
    except ValueError:
        return s


def run_console():
    """交互式控制台：逐行输入「指令名 参数…」，输入 q/quit/exit 退出"""
    print("[指令入口] 控制台已启动。指令: arm / disarm / takeoff <米> / land / rtl；退出: q")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        parts = line.split()
        send(parts[0], *(_parse_arg(p) for p in parts[1:]))
