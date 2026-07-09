from pymavlink import mavutil
master = mavutil.mavlink_connection('udp:127.0.0.1:14551')
master.wait_heartbeat(blocking=True)
print(f"收到心跳:sysid={master.target_system},compid={master.target_component}")
while True:
    msg = master.recv_match(blocking=False)
    if msg:
        msg_type = msg.get_type()
        if msg_type == 'HEARTBEAT':
            print(f"mode={msg.base_mode},status={msg.system_status}")
        elif msg_type == 'GLOBAL_POSITION_INT':
            print(f"lat={msg.lat/1e7:.6f},lon={msg.lon/1e7:.6f},alt={msg.alt/1e3:.1f}m")