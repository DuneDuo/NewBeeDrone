from pymavlink.dialects.v20.common import MAVLink_message
SENSORS = {
    # name      bit
    'gyro':        1,          # bit0
    'accel':       2,          # bit1
    'mag':         4,          # bit2
    'baro':        8,          # bit3
    'gps':         32,         # bit5
    'flow':        64,         # bit6
    'vision':      128,        # bit7
    'motor':       32768,      # bit15
    'rc':          65536,      # bit16
    'geofence':    1048576,    # bit21
    'battery':     33554432,   # bit25
}
class Sensor:
    def __init__(self):
        for name in SENSORS:
            setattr(self, name, None)
    def update(self,msg:MAVLink_message):
        present = msg.onboard_control_sensors_present #传感器存在(位掩码)
        enabled = msg.onboard_control_sensors_enabled #传感器启用
        health = msg.onboard_control_sensors_health #传感器健康
        for name,bit in SENSORS.items():
            if not (present&bit):
                setattr(self,f'{name}',None)
            elif not (enabled&bit):
                setattr(self,f'{name}',False)
            else:
                setattr(self,f'{name}',bool(health&bit))
    def check(self):
        """返回 {传感器名: None不存在/False故障/True正常}"""
        return {name: getattr(self, name) for name in SENSORS}