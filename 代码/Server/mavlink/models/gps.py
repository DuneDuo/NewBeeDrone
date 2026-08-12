class GPS:
    def __init__(self):
        self.fix_type = None
        self.satellites_visible = None
        self.eph = None
        self.epv = None
    def update(self,msg):
        self.fix_type = msg.fix_type # 定位类型
        self.satellites_visible = msg.satellites_visible # 可见卫星
        self.eph = msg.eph / 100 # 水平精度
        self.epv = msg.epv / 100 # 数值精度