import threading
class ParamOp:
    def __init__(self):
        self.param_id = None
        self.want = None
        self.result = None
        self.event = threading.Event()
    def update(self,msg):
        getid = msg.param_id
        if self.param_id is not None and self.param_id == getid:
            self.result = msg.param_value
            self.event.set()
