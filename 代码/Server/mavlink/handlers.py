from __future__ import annotations
from .dispatch import register
from pymavlink.dialects.v20.common import MAVLink_message
@register("HEARTBEAT")
def HEARTBEAT_HANDLER(drone,msg:MAVLink_message):
    drone.state.update_from_heartbeat(msg)
@register("GLOBAL_POSITION_INT")
def POSITION_HANDLER(drone,msg:MAVLink_message):
    drone.position.update_from_global_position(msg)
@register("ALTITUDE")
def ALTITUDE_HANDLER(drone,msg:MAVLink_message):
    drone.position.update_from_altitude(msg)
@register("ATTITUDE")
def ATTITUDE_HANDLER(drone,msg:MAVLink_message):
    drone.battery.update_from_attitude(msg)
    drone.attitude.update(msg)
@register("SYS_STATUS")
def SYS_HANDLER(drone,msg:MAVLink_message):
    drone.sensor.update(msg)
    drone.connection.update(msg)
    drone.battery.update_from_sys_status(msg)
@register("GPS_RAW_INT")
def GPS_HANDLER(drone,msg:MAVLink_message):
    drone.gps.update(msg)
@register("MISSION_CURRENT")
def MISSION_CURRENT_HANDLER(drone,msg:MAVLink_message):
    drone.mission.update_from_current(msg)
@register("MISSION_ITEM_REACHED")
def MISSION_ITEM_REACHED_HANDLER(drone,msg:MAVLink_message):
    drone.mission.update_from_reached(msg)
@register("NAV_CONTROLLER_OUTPUT")
def NAV_CONTROLLER_OUTPUT_HANDLER(drone,msg:MAVLink_message):
    drone.mission.update_from_nav(msg)
@register("VFR_HUD")
def VFR_HUD_HANDLER(drone,msg:MAVLink_message):
    drone.vfr.update(msg)
@register("BATTERY_STATUS")
def BATTERY_STATUS_HANDLER(drone,msg:MAVLink_message):
    drone.battery.update_from_battery_status(msg)
@register("PARAM_VALUE")
def PARAM_VALUE_HANDLER(drone,msg:MAVLink_message):
    drone.param.update(msg)
@register("COMMAND_ACK")
def COMMAND_ACK_HANDLER(drone,msg:MAVLink_message):
    drone.cmd.on_ack(msg)
@register("SYSTEM_TIME")
def SYSTEM_TIME_HANDLER(drone,msg:MAVLink_message):
    drone.connection.update_from_system_time(msg)
@register("EXTENDED_SYS_STATE")
def EXTENDED_SYS_STATE_HANDLER(drone, msg:MAVLink_message):
    drone.state.update_from_extended_sys_state(msg)
@register("STATUSTEXT")
def STATUSTEXT_HANDLER(drone,msg:MAVLink_message):
    drone.status_text.update(msg)