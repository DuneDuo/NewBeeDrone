import config
import socket
import time
import threading
from logger import logger
from dispatch import dispatch
from pymavlink.dialects.v20.ardupilotmega import MAVLink
log = logger("drone")
mav = MAVLink(None,srcSystem=config.ser_target_system,srcComponent=config.ser_target_component)

class Drone:
    registry:dict[int,'Drone'] = {}
    runnning = True
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
        self.sys_id = None
        self.conn:socket.socket = conn
        self.addr:tuple[str,int] = addr
        self.running = False
        self.last_heartbeat = None
    def receive_loop(self):
        self.running = True
        self.last_heartbeat = time.time()
        thread = threading.Thread(target=self.watch_dog,daemon=True)
        thread.start()
        #阶段一,获取心跳包
        while self.running and self.sys_id is None:
            try:
                data = self.conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if data:
                msg_set = mav.parse_buffer(data)
                for msg in msg_set:
                    if msg.get_type() == "HEARTBEAT":
                        self.sys_id = msg.get_srcSystem()
                        self.last_heartbeat = time.time()
                        Drone.registry[self.sys_id] = self
                        log.info(f"飞机注册:sys_id={self.sys_id},addr={self.addr}")
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
                msg_set = mav.parse_buffer(data)
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
    def close(self):
        log.info(f"关闭连接:drone_id={self.sys_id}")
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        Drone.registry.pop(self.sys_id, None)