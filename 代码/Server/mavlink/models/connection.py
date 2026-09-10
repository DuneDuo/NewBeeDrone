import time
class Connection:
    def __init__(self):
        self.drop_rate = None # 丢包率
        self.errors = None # 通信错误数
        self.disconnected_at = None # 断开时间
        self.ping = None # 延迟ms
        self._time_sent_ping = None
    def update(self,msg):
        self.drop_rate = msg.drop_rate # 丢包率
        self.errors = msg.errors # 通信错误数
    def update_from_system_time(self,msg):
        if self._time_sent_ping == msg.time_unix_usec:
            self.ping = (time.time()*1e6 - msg.time_unix_usec)/1000