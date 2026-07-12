#连接设置#transport
    #服务器
host = "0.0.0.0"  #监听地址
port = 57600 #监听端口
#心跳检测#heart
heartbeat_timeout = 3.0 #超时时间
watch_dog_interval = 1.0 #检查间隔
#系统id
ras_system_id = 255 #树莓派sys_id
ras_component_id = 190 #树莓派com_id
#连接目标
dialect = "ardupilotmega" #飞控系统
fc_target_system = 1 #飞控的sys_id #相当于对频密码
fc_target_component = 0 #飞控的com_id #相当于对频密码
ser_target_system = 254 #服务器的sys_id
ser_target_component = 190 #服务器的com_id
#日志#status_collector
log_dir = "logs" #日志目录
log_interval = 3.0 #更新间隔
#连接状态