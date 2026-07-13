from .logger import logger
log = logger("dispatch")
_handlers = {}
def register(msg_type):
    def wrapper(func):
        _handlers[msg_type] = func
        return func
    return wrapper
def dispatch(drone,msg):
    msg_type = msg.get_type()
    handler = _handlers.get(msg_type)
    if handler:
        handler(drone,msg)
    else:
        log.info(f"未注册的消息:{msg_type}")