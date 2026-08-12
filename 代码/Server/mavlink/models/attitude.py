from pymavlink.dialects.v20.common import MAVLink_message
import math
class Attitude:
    def __init__(self):
        self.roll = None
        self.pitch = None
        self.yaw = None
    def update(self,msg:MAVLink_message):
        self.roll = math.degrees(msg.roll)
        self.pitch = math.degrees(msg.pitch)
        self.yaw = math.degrees(msg.yaw)