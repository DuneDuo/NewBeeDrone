import config
import os
import logging
from datetime import datetime

_LAYER = {
    "drone":"drone",
    "dispatch":"drone",
    "command":"command"
}
_file_handlers = {}

_formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
_file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

def logger(name:str):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    if log.handlers:
        return log
    log.addHandler(_console_handler)
    sub = _LAYER.get(name,"misc")
    if sub not in _file_handlers:
        os.makedirs(os.path.join(config.log_dir,sub),exist_ok=True)
        fh = logging.FileHandler(os.path.join(config.log_dir,sub,_file_name))
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(_formatter)
        _file_handlers[sub] = fh
    log.addHandler(_file_handlers[sub])
    return log
