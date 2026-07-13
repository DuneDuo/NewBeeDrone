from . import config
from .drone import Drone
from .logger import logger
from .dispatch import register
log = logger("handlers")
@register("HEARTBEAT")
def HEARTBEAT_HANDLE(drone:Drone,msg):
    pass