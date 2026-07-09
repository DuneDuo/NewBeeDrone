#连接方式
connection_type = "udp" #连接方式serial/udp/tcp
serial_port = "COM3" #串口
serial_baudrate = 115200 #比特率
udp_address = "127.0.0.1:14551"
tcp_address = "127.0.0.1:5760"
#心跳检测
heartbeat_timeout = 3.0 #超时时间
watch_dog_interval = 1.0 #检查间隔
#日志
dirs = 'logs'
log_dir = "logs" #日志目录
log_interval = 3.0 #更新间隔
#连接状态
fc_connected = False
last_heartbeat_time = 0.0