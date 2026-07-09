import config
import os
import logging
from datetime import datetime
os.makedirs(config.dirs, exist_ok=True)
_formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
_file_name = f"{config.dirs}/mavlink_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)
_file_handler = logging.FileHandler(_file_name)
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(_formatter)
def logger(name:str):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.addHandler(_console_handler)
    log.addHandler(_file_handler)
    return log