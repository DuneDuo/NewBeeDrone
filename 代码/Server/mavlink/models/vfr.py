class VFR:
    def __init__(self):
        self.groundspeed = None
        self.throttle = None
        self.climb = None
    def update(self,msg):
        self.groundspeed = msg.groundspeed
        self.throttle = msg.throttle
        self.climb = msg.climb