class Position:
    def __init__(self):
        self.vx = None
        self.vy = None
        self.vz = None
        self.hdg = None #航向角0
        self.lat = None
        self.lon = None
        self.alt_rel = None #相对起飞点高度
        self.alt_ter = None #相对地形高度(需要测距仪)
    def update_from_global_position(self, msg):
        self.lat = msg.lat / 1e7
        self.lon = msg.lon / 1e7
        self.vx = msg.vx / 100
        self.vy = msg.vy / 100
        self.vz = msg.vz / 100
        self.hdg = msg.hdg / 100
    def update_from_altitude(self, msg):
        self.alt_rel = msg.altitude_relative
        self.alt_ter = msg.altitude_terrain