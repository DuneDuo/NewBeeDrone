#连接设置#transport
    #服务器
host = "0.0.0.0"  #监听地址
port = 57600 #监听端口
#心跳检测#heart
heartbeat_timeout = 3.0 #超时时间
watch_dog_interval = 1.0 #检查间隔
#连接目标
ser_target_system = 255 #服务器的sys_id
ser_target_component = 190 #服务器的com_id
#日志#status_collector
log_dir = "logs" #日志目录