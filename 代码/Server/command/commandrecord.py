import threading
# state
PENDING = "pending"
SENT = "sent"
EXECUTING = "executing"
DONE = "done"
FAIL = "fail"
# error
ERROR_DENIED = "denied"
ERROR_UNSPPORTED = "unsupported"
ERROR_FAILED = "failed"
ERROR_TIMEOUT = "timeout"
ERROR_LINK_LOST = "link_lost"

class Command:
    def __init__(self,name,cmd,params = None):
        # 与spec相同部分
        self.name = name
        self.cmd = cmd
        self.params = params or {}
        # 台账部分
        self.run_id = None
        self.state = PENDING
        self.result = None
        self.error = None
        self.retry_count = 0
        self.started_at = None
        self.sent_at = None
        self.done_at = None
        self.detail = None
        self.done_event = threading.Event()
