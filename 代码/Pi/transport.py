import config
import time
from logger import logger
from pymavlink import mavutil
log = logger("transport")

def open_connection(target:str="fc"):
    if(target == "fc"):
        connection_type = config.fc_connection_type
        serial_port = config.fc_serial_port
        serial_baudrate = config.fc_serial_baudrate
        udp_address = config.fc_udp_address
        tcp_address = config.fc_tcp_address
    elif(target == "server"):
        connection_type = config.ser_connection_type
        udp_address = config.ser_udp_address
        tcp_address = config.ser_tcp_address
    else:
        log.error(f"不支持的目标:{target}")
        return None
    log.info(f"正在连接{target},连接方式:{connection_type}")
    try:
        if connection_type == "udp":
            conn = mavutil.mavlink_connection(f"udp:{udp_address}",
                                            source_system=config.ras_system_id,
                                            source_component=config.ras_component_id,
                                            dialect=config.dialect,
                                            autoreconnect=True,
                                            retries=3,udp_timeout=1.0)
            
        elif connection_type == "tcp":
            conn = mavutil.mavlink_connection(f"tcp:{tcp_address}",
                                            source_system=config.ras_system_id,
                                            source_component=config.ras_component_id,
                                            dialect=config.dialect,
                                            autoreconnect=True,
                                            retries=3)
        elif connection_type == "serial":
            conn = mavutil.mavlink_connection(serial_port,
                                            baud=serial_baudrate,
                                            source_system=config.ras_system_id,
                                            source_component=config.ras_component_id,
                                            dialect=config.dialect,
                                            autoreconnect=True,
                                            retries=3)
        else:
            log.error(f"不支持的连接方式:{connection_type}")
            return None
    except Exception as e:
        log.error(f"连接失败:{e}")
        return None
    log.info(f"等待心跳,超时时间:{config.heartbeat_timeout}")
    tstart = time.time()
    while True:
        if time.time() - tstart > config.heartbeat_timeout:
            log.error("心跳超时,无响应")
            conn.close()
            return None
        m = conn.recv_msg()
        if m is not None and m.get_type() == 'HEARTBEAT':
            conn.target_system = m.get_srcSystem()
            conn.target_component = m.get_srcComponent()
            break
    if(conn.target_system==config.fc_target_system and conn.target_component==config.fc_target_component):
        log.info("飞控已连接")
        return conn
    elif(conn.target_system==config.ser_target_system and conn.target_component==config.ser_target_component):
        log.info("服务器已连接")
        return conn
    else:
        log.error(f"未知连接{conn.target_system},{conn.target_component}")
        return None
