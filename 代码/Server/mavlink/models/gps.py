class GPS:
    def __init__(self):
        self.fix_type = None
        self.satellites_visible = None
        self.h_acc = None
        self.v_acc = None
        self.vel_acc = None
    def update(self,msg):
        self.fix_type = msg.fix_type # 定位类型
        self.satellites_visible = msg.satellites_visible # 可见卫星
        self.h_acc = msg.h_acc / 1000 # 水平精度
        self.v_acc = msg.v_acc / 1000 # 竖直精度
        self.vel_acc = msg.vel_acc / 1000 # 速度精度