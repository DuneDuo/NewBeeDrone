class Battery:
    def __init__(self):
        self.voltage = None
        self.current = None
        self.consumed = None
        self.remaining = None
        self.time_remaining = None
        self.time_boot = None
    def update_from_battery_status(self,msg):
        self.current = msg.current_battery / 100 # 电池电流
        self.consumed = msg.current_consumed # 消耗电量(mah)
        self.remaining = msg.battery_remaining # 剩余电量百分比(%)
        self.time_remaining = msg.time_remaining # 预估剩余飞行时间(s)
    def update_from_sys_status(self,msg):
        self.voltage = msg.voltage_battery / 1000 # 电池电压
    def update_from_attitude(self,msg):
        self.time_boot = msg.time_boot_ms / 1000