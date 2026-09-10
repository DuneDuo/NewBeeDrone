import time
import os
import config
_MAKE_DIR = None
_SEVERITY = {
    0:"EMERGENCY",
    1:"ALERT",
    2:"CRITICAL",
    3:"ERROR",
    4:"WARNING",
    5:"NOTICE",
    6:"INFO",
    7:"DEBUG"
}

class StatusText:
    def __init__(self,drone):
        self.severity = None
        self.buf = None
        self.buf_id = None
        self.buf_time = None
        self.drone = drone
    def update(self,msg):
        if msg.chunk_seq == 0:
            self.flush()
            self.severity = _SEVERITY.get(msg.severity,"UNKNOWN")
            self.buf = msg.text
            self.buf_id = msg.id
            self.buf_time = time.strftime("%Y-%m-%d %H:%M:%S")
        elif msg.id == self.buf_id and self.buf is not None:
            self.buf += msg.text
        else:
            self.flush()
            self.severity = _SEVERITY.get(msg.severity,"UNKNOWN")
            self.buf = msg.text
            self.buf_id = msg.id
            self.buf_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if len(msg.text) < 50:
            self.flush()
    def make_dir(self):
        global _MAKE_DIR
        if _MAKE_DIR is None:
            _MAKE_DIR = os.path.join(config.status_text_dir,time.strftime("%Y%m%d_%H%M%S"))
            os.makedirs(_MAKE_DIR,exist_ok=True)
        return _MAKE_DIR
    def flush(self):
        if self.buf is None:
            return
        path = os.path.join(self.make_dir(),f"{self.drone.sys_id}.txt")
        with open(path,"a",encoding="utf-8") as f:
            f.write(f"[{self.buf_time}][{self.buf_id}][{self.severity}]{self.buf}\n")
        self.buf = None
        self.severity = None
        self.buf_id = None
        self.buf_time = None
