# FlightState —— 飞机的语义状态四轴，命令谓词（commands.json 的 effect/complete）就读这里。
# 各字段取值详解见 command/command格式说明.md 的附录。
# 对应 command/commandspec.py 的 _STATE_FIELDS 白名单。

class FlightState:
    # 飞行模式 · 主模式表（custom_mode bits 16-23，非 AUTO 直接查）
    MAIN_MODE = {
        1: "manual", 2: "altctl", 3: "posctl", 4: "auto", 5: "acro",
        6: "offboard", 7: "stabilized", 8: "rattitude_legacy", 9: "simple",
        10: "termination", 11: "altitude_cruise",
    }
    # 飞行模式 · AUTO 子模式表（main_mode==4 时才看 bits 24-31）
    AUTO_SUB_MODE = {
        1: "ready", 2: "takeoff", 3: "loiter", 4: "mission", 5: "rtl", 6: "land",
        8: "follow_target", 9: "precland", 10: "vtol_takeoff",
        11: "external1", 12: "external2", 13: "external3", 14: "external4",
        15: "external5", 16: "external6", 17: "external7", 18: "external8",
    }
    # 着地状态（MAV_LANDED_STATE）
    LANDED_STATE = {0: "undefined", 1: "on_ground", 2: "in_air", 3: "takeoff", 4: "landing"}
    # 系统状态（MAV_STATE）
    SYSTEM_STATUS = {
        0: "uninit", 1: "boot", 2: "calibrating", 3: "standby", 4: "active",
        5: "critical", 6: "emergency", 7: "poweroff", 8: "flight_termination",
    }

    def __init__(self):
        self.mode = None            # 飞行模式（custom_mode 解码）
        self.armed = None           # 是否解锁（base_mode bit7）
        self.landed_state = None    # 着地状态（EXTENDED_SYS_STATE）
        self.system_status = None   # 系统状态（MAV_STATE）
        self.custom_mode = None     # 原始 custom_mode，仅调试

    def update_from_heartbeat(self, msg):
        self.custom_mode = msg.custom_mode
        self.armed = bool(msg.base_mode & 128)
        self.system_status = self.SYSTEM_STATUS.get(msg.system_status, f"unknown_{msg.system_status}")
        main = (msg.custom_mode >> 16) & 0xFF
        sub = (msg.custom_mode >> 24) & 0xFF
        self.mode = self.AUTO_SUB_MODE.get(sub, "auto") if main == 4 \
                    else self.MAIN_MODE.get(main, f"unknown_{main}")

    def update_from_extended_sys_state(self, msg):
        self.landed_state = self.LANDED_STATE.get(msg.landed_state, "undefined")
