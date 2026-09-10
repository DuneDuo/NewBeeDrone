class Mission:
    def __init__(self):
        self.seq = None # 当前正在飞向的航点序号
        self.total = None # 航点总数
        self.mission_state = None # 任务状态,查表
        self.mission_mode = None # 是否任务模式（0=未知, 1=任务中, 2=暂停）
        self.mission_reached = None # 刚刚到达的航点
        self.target_bearing = None # 飞机到航点的相对角度
        self.wp_dist = None # 飞机到航点的距离
        self.alt_error = None # 高度误差
        self.xtrack_error = None # 横向偏航距
    def update_from_current(self,msg):
        self.seq = msg.seq
        self.total = None if msg.total == 65535 else msg.total
        self.mission_state = msg.mission_state
        self.mission_mode = msg.mission_mode
    def update_from_reached(self,msg):
        self.mission_reached = msg.seq
    def update_from_nav(self,msg):
        self.target_bearing = msg.target_bearing # 飞机到航点的相对角度
        self.wp_dist = msg.wp_dist # 飞机到航点的距离
        self.alt_error = msg.alt_error # 高度误差
        self.xtrack_error = msg.xtrack_error # 横向偏航距