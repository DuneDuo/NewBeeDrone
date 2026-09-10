import socket
import time
import threading
import math
import config
from logger import logger
from mavlink.dispatch import dispatch
from mavlink.models import Sensor,Attitude,Position,GPS,Mission,VFR,Connection,Battery,ParamOp,FlightState,StatusText
from pymavlink.dialects.v20.common import (
    MAVLink,
    MAV_TYPE_GCS,
    MAV_AUTOPILOT_GENERIC,
    MAV_STATE_ACTIVE,
)
from command import CommandManager
log = logger("drone")
class Drone:
    registry:dict[int,'Drone'] = {}
    @classmethod
    def serve(cls):
        conn = None
        try:
            conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            conn.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            conn.bind((config.host,config.port))
            conn.listen(5)
            log.info(f"服务器监听:{config.host}:{config.port}")
        except Exception as e:
            log.error(f"启动监听失败:{e}")
            if conn:
                conn.close()
            return
        
        while True:
            try:
                client,addr=conn.accept()
                client.settimeout(3)
                log.info(f"新连接:{addr}")
                drone = cls(client,addr)
                threading.Thread(target=drone.receive_loop,daemon=True).start()
            except Exception as e:
                log.error(f"accept失败:{e}")
                time.sleep(1)
    def __init__(self,conn,addr):
        self.mav = MAVLink(None,srcSystem=config.ser_target_system,srcComponent=config.ser_target_component)
        self.conn:socket.socket = conn
        self.addr:tuple[str,int] = addr
        self.sys_id = None
        self.running = False
        self.last_heartbeat = None
        # 飞行姿态
        self.attitude = Attitude()
        # 位置
        self.position = Position()
        # GPS
        self.gps = GPS()
        # 电池
        self.battery = Battery()
        # 传感器
        self.sensor = Sensor()
        # 航点任务
        self.mission = Mission() 
        # 仪表盘
        self.vfr = VFR()
        # 数传质量
        self.connection = Connection()
        # 飞行状态
        self.state = FlightState()
        # 指令对象
        self.cmd = CommandManager(self)
        # 参数读写对象
        self.param = ParamOp()
        # 业务状态 换电/飞行 
        self.biz_state = None
        # 换电阻塞
        self.swap_done = threading.Event()
        # 发送锁
        self.send_lock = threading.Lock()
        # 飞控日志
        self.status_text = StatusText(self)


    def receive_loop(self):
        self.running = True
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        #阶段一,获取心跳包
        while self.running and self.sys_id is None:
            try:
                data = self.conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if data:
                try:
                    msg_set = self.mav.parse_buffer(data)
                except Exception:
                    continue
                if msg_set is None:
                    continue
                for msg in msg_set:
                    if msg.get_type() == "HEARTBEAT":
                        self.sys_id = msg.get_srcSystem()
                        # 检查是否是断连恢复
                        old = Drone.registry.get(self.sys_id)
                        Drone.registry[self.sys_id] = self
                        if old and old is not self:
                            self._reconnect(old)
                        self.last_heartbeat = time.time()
                        log.info(f"无人机注册:drone_id={self.sys_id},addr={self.addr}")
                        break
            else:
                log.error(f"客户端主动断开, {self.addr}")
                break
        if not self.running or self.sys_id is None:
            return
        threading.Thread(target=self.watch_dog,daemon=True).start()

        threading.Thread(target=self.cmd.tick_loop, daemon=True).start()
        threading.Thread(target=self.ping_loop, daemon=True).start()
        #阶段二,处理信息
        while self.running:
            try:
                data = self.conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if data:
                try:
                    msg_set = self.mav.parse_buffer(data)
                except Exception:
                    continue
                if msg_set is None:
                    continue
                for msg in msg_set:
                    if msg.get_type() == "HEARTBEAT":
                        self.last_heartbeat = time.time()
                    dispatch(self,msg)
            else:
                log.error(f"客户端主动断开, drone_id={self.sys_id}")
                break
        self.close()

    def watch_dog(self):
        while self.running:
            now_time = time.time()
            if self.last_heartbeat is not None and now_time-self.last_heartbeat > config.heartbeat_timeout:
                log.error(f"心跳超时 {config.heartbeat_timeout}s, drone_id={self.sys_id}")
                self.close()
            time.sleep(config.watch_dog_interval)

    def _send(self, msg):
        with self.send_lock:
            try:
                buf = msg.pack(self.mav)
                self.conn.send(buf)
            except OSError:
                log.error(f"发送失败，连接中断 drone_id={self.sys_id}")
                self.close()
            except Exception:
                log.exception(f"意外错误 drone_id={self.sys_id}")

    def send_heartbeat(self):
        msg = self.mav.heartbeat_encode(
            MAV_TYPE_GCS,
            MAV_AUTOPILOT_GENERIC,
            0,
            0,
            MAV_STATE_ACTIVE,
            3
        )
        self._send(msg)
    def heartbeat_loop(self):
        while self.running:
            self.send_heartbeat()
            time.sleep(1)
    def _send_ping(self):
        self.connection._time_sent_ping = int(time.time()*1e6)
        msg = self.mav.system_time_encode(self.connection._time_sent_ping,0)
        self._send(msg)
    def ping_loop(self):
        while self.running:
            self._send_ping()
            time.sleep(1)
    def send_command_long(self,command_id,param1=0,param2=0,param3=0,param4=0,param5=0,param6=0,param7=0):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法发送指令:{command_id} drone_id={self.sys_id}")
            return
        msg = self.mav.command_long_encode(
            self.sys_id,
            1,
            command_id,
            0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7
            )
        self._send(msg)
        log.info(f"发送指令: command={command_id} drone_id={self.sys_id}")
    def send_command_int(self,command_id,param1=0,param2=0,param3=0,param4=0,param5=0,param6=0,param7=0):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法发送指令:{command_id} drone_id={self.sys_id}")
            return
        msg = self.mav.command_int_encode(
            self.sys_id,
            1,
            6,
            command_id,
            0,
            0,
            param1,
            param2,
            param3,
            param4,
            param5, # 纬度用 int32 存「×1e7 缩放后的整数」
            param6, # 经度
            param7, # 相对起飞点高度,float
            )
        self._send(msg)
        log.info(f"发送指令: command={command_id} drone_id={self.sys_id}")

    def _param_request_read(self,param_id):
        b=bytes(param_id,"utf-8")
        msg = self.mav.param_request_read_encode(
            self.sys_id,
            1,
            b,
            -1
        )
        self._send(msg)
        
    def _param_set(self, param_id, param_value, param_type=9):
        b=bytes(param_id,"utf-8")
        msg = self.mav.param_set_encode(
            self.sys_id,
            1,
            b,
            param_value,
            param_type
        )
        self._send(msg)
    def param_read(self,param_id,timeout = 3.0):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法读取参数:{param_id} drone_id={self.sys_id}")
            return None
        if self.param.param_id is not None:
            log.error(f"参数操作忙: {self.param.param_id} drone_id={self.sys_id}")
            return None
        self.param.event.clear()
        self.param.param_id = param_id
        self._param_request_read(param_id)
        read = self.param.event.wait(timeout)
        if not read:
            log.error(f"ParamOp未收到返回参数 drone_id={self.sys_id}")
            self.param.param_id = None
            return None
        self.param.param_id = None
        return self.param.result
    @staticmethod
    def _eq(a, b):
        return math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-8)
    def param_set(self,param_id,param_value,param_type = 9,timeout = 3.0):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法设置参数:{param_id} drone_id={self.sys_id}")
            return False
        if self.param.param_id is not None:
            log.error(f"参数操作忙: {self.param.param_id} drone_id={self.sys_id}")
            return False
        self.param.event.clear()
        self.param.param_id = param_id
        self.param.want = param_value
        self._param_set(param_id,param_value,param_type)
        read = self.param.event.wait(timeout)
        if not read:
            log.error(f"ParamOp未收到返回参数 drone_id={self.sys_id}")
            self.param.param_id = None
            self.param.want = None
            return False
        if self._eq(self.param.want,self.param.result):
            self.param.param_id = None
            self.param.want = None
            if self._eq(self.param_read(param_id,timeout),param_value):
                self.param.param_id = None
                return True
        log.error(f"参数设置失败:{param_id} drone_id={self.sys_id}")
        self.param.param_id = None
        self.param.want = None
        self.param.result = None
        return False
    def close(self):
        if not self.running:
            return
        log.info(f"关闭连接:drone_id={self.sys_id}")
        self.running = False
        self.connection.disconnected_at = time.time()
        self.status_text.flush()
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
    def _reconnect(self,old): #  业务层换电后：Drone.registry[sys_id] 重查拿新实例（旧引用已失效）
        self.biz_state = old.biz_state
        self.running = True
        self.swap_done = old.swap_done
        if old.biz_state == "swapping":
            self._reconnect_swapping()
        elif old.state.armed:
            self._reconnect_flying(old)
        else:
            self._reconnect_ground(old)
        old.close()
    def _reconnect_swapping(self):
        self.swap_done.set()
        log.info(f"换电后重连成功 drone_id={self.sys_id}")
    def _reconnect_flying(self,old):
        self._inherit_telemetry(old)
        log.warning(f"飞行中重连,等待人工决策 drone_id={self.sys_id}")
    def _reconnect_ground(self,old):
        self._inherit_telemetry(old)
        log.info(f"重连成功 drone_id={self.sys_id}")
    def _inherit_telemetry(self, old):
        for name in ("state", "attitude", "position", "gps", "battery",
                     "sensor", "mission", "vfr"):
            setattr(self, name, getattr(old, name))