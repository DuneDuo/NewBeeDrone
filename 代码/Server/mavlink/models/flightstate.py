class FlightState:
    MAIN_MODE = {1:"manual",2:"altctl",3:"posctl",4:"auto",5:"acro",
                 6:"offboard",7:"stabilized",8:"rattitude_legacy",9:"simple",
                 10:"termination",11:"altitude_cruise"}
    AUTO_SUB_MODE = {1:"ready",2:"takeoff",3:"loiter",4:"mission",5:"rtl",
                     6:"land",8:"follow_target",9:"precland",10:"vtol_takeoff",
                     11:"external1",12:"external2",13:"external3",14:"external4",
                     15:"external5",16:"external6",17:"external7",18:"external8"}
    LANDED_STATE = {0:"undefined",1:"on_ground",2:"in_air",3:"takeoff",4:"landing"}
    SYSTEM_STATUS = {0:"uninit",1:"boot",2:"calibrating",3:"standby",4:"active",
                     5:"critical",6:"emergency",7:"poweroff",8:"flight_termination"}

    def __init__(self):
        self.mode = None            # 轴① 飞行模式
        self.armed = None           # 轴③ 武装
        self.landed_state = None    # 轴② 着地
        self.system_status = None   # 轴④ 生命周期/异常
        self.custom_mode = None     # 调试

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