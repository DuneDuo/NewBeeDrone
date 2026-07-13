#连接方式#transport open_connection(fc/server)
    #飞控
fc_connection_type = "udp" #连接方式serial/udp/tcp
fc_serial_port = "COM3" #串口
fc_serial_baudrate = 115200 #波特率
fc_udp_address = "127.0.0.1:14551"  #udp监听地址
fc_tcp_address = "8.152.207.82:5760" #tcp监听地址
    #服务器
ser_connection_type = "tcp" #连接方式tcp
ser_udp_address = "127.0.0.1:14552"  #暂时不用
ser_tcp_address = "8.152.207.82:57600" #mock服务器地址
#心跳检测#heart
heartbeat_timeout = 3.0 #超时时间
watch_dog_interval = 1.0 #检查间隔
#系统id
ras_system_id = 254 #树莓派sys_id
ras_component_id = 190 #树莓派com_id
#连接目标
dialect = "ardupilotmega" #飞控系统
fc_target_system = 1 #飞控的sys_id #相当于对频密码
fc_target_component = 1 #飞控的com_id #相当于对频密码
ser_target_system = 255 #服务器的sys_id
ser_target_component = 190 #服务器的com_id
#日志#status_collector
log_dir = "logs" #日志目录
log_interval = 3.0 #更新间隔
