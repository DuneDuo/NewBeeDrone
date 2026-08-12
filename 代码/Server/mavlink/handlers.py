from . import config
from .drone import Drone
from .logger import logger
from .dispatch import register
from pymavlink.dialects.v20.common import MAVLink_message
log = logger("handlers")
@register("HEARTBEAT")
def HEARTBEAT_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.armed = bool(msg.base_mode & 128)
    drone.flight_mode = msg.custom_mode
    drone.sys_status = msg.system_status
@register("GLOBAL_POSITION_INT")
def POSITION_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.position.update_from_global_position(msg)
@register("ALTITUDE")
def ALTITUDE_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.position.update_from_altitude(msg)
@register("ATTITUDE")
def ATTITUDE_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.time_boot = msg.time_boot_ms / 1000
    drone.attitude.update(msg)
@register("SYS_STATUS")
def SYS_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.sensor.update(msg)
    drone.cpu_load = msg.load / 10
@register("GPS_RAW_INT")
def GPS_HANDLER(drone:Drone,msg:MAVLink_message):
    drone.gps.update(msg)
