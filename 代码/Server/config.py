from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

#连接设置#transport
    #服务器
host = "0.0.0.0" #监听地址
port = 57600 #监听端口
#心跳检测#heart
heartbeat_timeout = 3.0 #超时时间
watch_dog_interval = 1.0 #检查间隔
#连接目标
ser_target_system = 255 #服务器的sys_id
ser_target_component = 190 #服务器的com_id
#日志#status_collector
log_dir = "logs" #日志目录
debug_msg = True
#命令#command
cmd_spec_path = str(BASE_DIR / "command" / "commands.json")    # 命令定义表 JSON 路径
cmd_log_dir = str(BASE_DIR / "logs" / "commands_json")         # 台账日志根目录（按日期建子文件夹）
cmd_tick_interval = 0.5             # 超时扫描间隔（秒）
cmd_first_ack_timeout = 2.0         # 等第一个回执超时（秒）