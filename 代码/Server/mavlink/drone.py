import socket
import time
import threading
from . import config
from .logger import logger
from .dispatch import dispatch
from pymavlink.dialects.v20.ardupilotmega import (
    MAVLink,
    MAV_TYPE_GCS,
    MAV_AUTOPILOT_GENERIC,
    MAV_STATE_ACTIVE,
)
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
        self.sys_id = None
        self.conn:socket.socket = conn
        self.addr:tuple[str,int] = addr
        self.running = False
        self.last_heartbeat = None
    def receive_loop(self):
        self.running = True
        self.last_heartbeat = time.time()
        threading.Thread(target=self.watch_dog,daemon=True).start()
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
                        self.last_heartbeat = time.time()
                        Drone.registry[self.sys_id] = self
                        log.info(f"无人机注册:sys_id={self.sys_id},addr={self.addr}")
                        break
            else:
                log.error(f"客户端主动断开, {self.addr}")
                break
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
            if now_time-self.last_heartbeat > config.heartbeat_timeout:
                log.error(f"心跳超时 {config.heartbeat_timeout}s, drone_id={self.sys_id}")
                self.close()
            time.sleep(config.watch_dog_interval)

    def _send(self, buf):
        try:
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
        buf = msg.pack(self.mav)
        self._send(buf)
    def heartbeat_loop(self):
        while self.running:
            self.send_heartbeat()
            time.sleep(1)

    def send_command_long(self,command_id,param1=0,param2=0,param3=0,param4=0,param5=0,param6=0,param7=0):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法发送指令:{command_id}")
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
        buf = msg.pack(self.mav)
        self._send(buf)
    def param_request_read(self,param_id:bytes):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法读取参数:{param_id}")
            return
        msg = self.mav.param_request_read_encode(
            self.sys_id,
            1,
            param_id,
            -1
        )
        buf = msg.pack(self.mav)
        self._send(buf)

    def param_set(self, param_id:bytes, param_value, param_type=9):
        if self.sys_id is None:
            log.error(f"无人机未注册,无法设置参数:{param_id}")
            return
        msg = self.mav.param_set_encode(
            self.sys_id,
            1,
            param_id,
            param_value,
            param_type
        )
        buf = msg.pack(self.mav)
        self._send(buf)
        
    def close(self):
        if not self.running:
            return
        log.info(f"关闭连接:drone_id={self.sys_id}")
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        Drone.registry.pop(self.sys_id, None)