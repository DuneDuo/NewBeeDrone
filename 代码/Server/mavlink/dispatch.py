from logger import logger
import config
log = logger("dispatch")
_handlers = {}
_no_handler = set()
def register(msg_type):
    def wrapper(func):
        _handlers[msg_type] = func
        return func
    return wrapper
def dispatch(drone,msg):
    if msg.get_srcSystem() == config.ser_target_system:
        return
    msg_type = msg.get_type()
    if config.debug_msg:
        log.debug(f"[{msg.get_type()}]{msg.to_dict()}")
    handler = _handlers.get(msg_type)
    if handler:
        handler(drone,msg)
    elif msg_type not in _no_handler:
        _no_handler.add(msg_type)
        log.info(f"未注册的消息:{msg_type} drone_id={drone.sys_id}")