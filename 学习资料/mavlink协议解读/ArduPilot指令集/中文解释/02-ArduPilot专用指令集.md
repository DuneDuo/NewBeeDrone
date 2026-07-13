# 02 — ArduPilot 专用指令集 (ardupilotmega.xml)

> 来源：`ardupilotmega.xml` (2070行) — ArduPilot 特有扩展
> 注意：ArduPilot 专用消息使用命令 ID 范围 150-250

---

## 1. ArduPilot 专用 MAV_CMD 命令

### 1.1 磁力计校准

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 42424 | `MAV_CMD_DO_START_MAG_CAL` | **开始磁力计校准** | 磁力计位掩码(0=全部)、失败重试(0=否/1=是)、自动保存(0=需确认/1=自动)、延迟(秒)、自动重启(0=手动/1=自动) |
| 42425 | `MAV_CMD_DO_ACCEPT_MAG_CAL` | **接受磁力计校准结果** | 磁力计位掩码(0=全部) |
| 42426 | `MAV_CMD_DO_CANCEL_MAG_CAL` | **取消正在进行的磁力计校准** | 磁力计位掩码(0=全部) |
| 42004 | `MAV_CMD_FIXED_MAG_CAL` | **基于固定位置的地磁校准** | 磁偏角(deg)、磁倾角(deg)、磁场强度(mgauss)、偏航角(deg) |
| 42005 | `MAV_CMD_FIXED_MAG_CAL_FIELD` | **基于固定磁场值校准** | 磁场X、Y、Z分量(mgauss) |

### 1.2 加速度计校准

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 42429 | `MAV_CMD_ACCELCAL_VEHICLE_POS` | **加速度计校准姿态指令**（告知地面站/飞行器应处于什么姿态） | 姿态位置(见ACCELCAL_VEHICLE_POS枚举) |

### 1.3 任务和脚本

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 215 | `MAV_CMD_DO_SET_RESUME_REPEAT_DIST` | **设置任务恢复重复距离** | 距离(m) |
| 216 | `MAV_CMD_DO_SPRAYER` | **控制喷洒器** | 0=禁用喷洒/1=启用喷洒 |
| 217 | `MAV_CMD_DO_SEND_SCRIPT_MESSAGE` | **向脚本传递指令** | ID(0-65535)、参数1/2/3(float) |
| 42701 | `MAV_CMD_SCRIPTING` | **控制板载脚本** | 脚本命令(见SCRIPTING_CMD枚举) |
| 42702 | `MAV_CMD_NAV_SCRIPT_TIME` | **脚本导航命令（等待完成）** | 命令号(0-255)、超时(秒,0=无限)、参数1-4 |
| 42703 | `MAV_CMD_NAV_ATTITUDE_TIME` | **保持姿态指定时长** | 时间(秒)、横滚角(deg,正=右倾)、俯仰角(deg,正=后仰)、偏航角(deg)、爬升率(m/s) |

### 1.4 辅助功能

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 218 | `MAV_CMD_DO_AUX_FUNCTION` | **执行辅助功能** | 辅助功能ID、开关档位(0=低/1=中/2=高) |
| 83 | `MAV_CMD_NAV_ALTITUDE_WAIT` | **等待高度条件**（高空气球发射） | 目标高度(m)、下降速度(m/s)、舵面摆动时间(s) |
| 42000 | `MAV_CMD_POWER_OFF_INITIATED` | **系统级断电事件已启动** | 无参数 |

### 1.5 Solo/3DR 专用

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 42001 | `MAV_CMD_SOLO_BTN_FLY_CLICK` | **FLY按钮被点击** | - |
| 42002 | `MAV_CMD_SOLO_BTN_FLY_HOLD` | **FLY按钮被按住1.5秒** | 起飞高度(m) |
| 42003 | `MAV_CMD_SOLO_BTN_PAUSE_CLICK` | **PAUSE按钮被点击** | 1=Shot模式中/0=不在 |

### 1.6 系统操作

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 42428 | `MAV_CMD_DO_SEND_BANNER` | **回复版本横幅信息** | - |
| 42427 | `MAV_CMD_SET_FACTORY_TEST_MODE` | **进入/退出工厂测试诊断模式** | 0=激活测试/1=退出测试 |
| 42007 | `MAV_CMD_SET_EKF_SOURCE_SET` | **设置EKF传感器源组** | 源组ID(1-3) |
| 42650 | `MAV_CMD_FLASH_BOOTLOADER` | **更新Bootloader** | 魔数(填入290876以实际刷写) |
| 42651 | `MAV_CMD_BATTERY_RESET` | **重置电池容量**（适用累积积分型电池） | 电池位掩码、剩余百分比(0-100) |
| 42700 | `MAV_CMD_DEBUG_TRAP` | **发送陷阱信号到飞控进程**（进入调试器） | 魔数(填入32451以实际触发) |

### 1.7 云台操作

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 42501 | `MAV_CMD_GIMBAL_RESET` | **云台复位重启**（模拟重新上电） | - |
| 42502 | `MAV_CMD_GIMBAL_AXIS_CALIBRATION_STATUS` | **报告云台轴校准进度和结果** | 轴类型、进度百分比(0-100)、状态 |
| 42503 | `MAV_CMD_GIMBAL_REQUEST_AXIS_CALIBRATION` | **启动云台换向校准** | - |
| 42505 | `MAV_CMD_GIMBAL_FULL_RESET` | **擦除云台应用程序和参数** | 魔数×7(安全保护) |

### 1.8 高度和位置辅助

| ID | 指令名 | 中文说明 | 参数 |
|:--:|--------|----------|------|
| 43005 | `MAV_CMD_SET_HAGL` | **提供离地高度值**（供固定翼和VTOL降落使用） | 离地高度(m)、测量精度(1σ,m)、超时(秒) |

---

## 2. ArduPilot 专用枚举

### SCRIPTING_CMD — 脚本命令

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `SCRIPTING_CMD_REPL_START` | 启动REPL交互会话 |
| 1 | `SCRIPTING_CMD_REPL_STOP` | 结束REPL会话 |
| 2 | `SCRIPTING_CMD_STOP` | 停止脚本执行 |
| 3 | `SCRIPTING_CMD_STOP_AND_RESTART` | 停止脚本并重启 |

### ACCELCAL_VEHICLE_POS — 加速度计校准姿态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `ACCELCAL_VEHICLE_POS_LEVEL` | 水平 |
| 2 | `ACCELCAL_VEHICLE_POS_LEFT` | 左侧朝下 |
| 3 | `ACCELCAL_VEHICLE_POS_RIGHT` | 右侧朝下 |
| 4 | `ACCELCAL_VEHICLE_POS_NOSEDOWN` | 机头朝下 |
| 5 | `ACCELCAL_VEHICLE_POS_NOSEUP` | 机头朝上 |
| 6 | `ACCELCAL_VEHICLE_POS_BACK` | 机背朝下 |
| 16777215 | `ACCELCAL_VEHICLE_POS_SUCCESS` | 校准成功 |
| 16777216 | `ACCELCAL_VEHICLE_POS_FAILED` | 校准失败 |

### MAV_CMD_DO_AUX_FUNCTION_SWITCH_LEVEL — 辅助功能开关档位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `MAV_CMD_DO_AUX_FUNCTION_SWITCH_LEVEL_LOW` | 低档位 |
| 1 | `MAV_CMD_DO_AUX_FUNCTION_SWITCH_LEVEL_MIDDLE` | 中档位 |
| 2 | `MAV_CMD_DO_AUX_FUNCTION_SWITCH_LEVEL_HIGH` | 高档位 |

---

## 3. EKF 状态 (扩展卡尔曼滤波器)

### EKF_STATUS_FLAGS — EKF状态标志位（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `EKF_ATTITUDE` | EKF姿态估计良好 |
| 2 | `EKF_VELOCITY_HORIZ` | EKF水平速度估计良好 |
| 4 | `EKF_VELOCITY_VERT` | EKF垂直速度估计良好 |
| 8 | `EKF_POS_HORIZ_REL` | EKF水平位置(相对)估计良好 |
| 16 | `EKF_POS_HORIZ_ABS` | EKF水平位置(绝对)估计良好 |
| 32 | `EKF_POS_VERT_ABS` | EKF垂直位置(绝对)估计良好 |
| 64 | `EKF_POS_VERT_AGL` | EKF离地高度估计良好 |
| 128 | `EKF_CONST_POS_MODE` | EKF处于固定位置模式，不知绝对/相对位置 |
| 256 | `EKF_PRED_POS_HORIZ_REL` | EKF预测水平位置(相对)良好 |
| 512 | `EKF_PRED_POS_HORIZ_ABS` | EKF预测水平位置(绝对)良好 |
| 1024 | `EKF_UNINITIALIZED` | EKF从未健康过 |
| 32768 | `EKF_GPS_GLITCHING` | EKF认为GPS输入数据有误 |

### 速度/位置方差判断参考
- `< 0.5` — 良好
- `0.5 ~ 0.79` — 警告
- `≥ 0.8` — 差

---

## 4. PID 调参

### PID_TUNING_AXIS — PID调参轴

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `PID_TUNING_ROLL` | 横滚轴 |
| 2 | `PID_TUNING_PITCH` | 俯仰轴 |
| 3 | `PID_TUNING_YAW` | 偏航轴 |
| 4 | `PID_TUNING_ACCZ` | Z轴加速度 |
| 5 | `PID_TUNING_STEER` | 转向轴 |
| 6 | `PID_TUNING_LANDING` | 降落轴 |
| 7 | `PID_TUNING_WHEEL_LEFT` | 左轮速率 |
| 8 | `PID_TUNING_WHEEL_RIGHT` | 右轮速率 |
| 9 | `PID_TUNING_SAIL_HEEL` | 帆船倾斜角 |
| 10 | `PID_TUNING_VEL_NORTH` | 北向速度 |
| 11 | `PID_TUNING_VEL_EAST` | 东向速度 |
| 12 | `PID_TUNING_VEL_DOWN` | 下降速度 |
| 13 | `PID_TUNING_POS_NORTH` | 北向位置 |
| 14 | `PID_TUNING_POS_EAST` | 东向位置 |
| 15 | `PID_TUNING_POS_DOWN` | 下降位置 |
| 16 | `PID_TUNING_YAW_ANGLE` | 偏航角度 |

---

## 5. 限位模块 (AP_Limits)

### LIMITS_STATE — 限位状态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `LIMITS_INIT` | 预初始化 |
| 1 | `LIMITS_DISABLED` | 已禁用 |
| 2 | `LIMITS_ENABLED` | 正在检查限位 |
| 3 | `LIMITS_TRIGGERED` | 已触发限位 |
| 4 | `LIMITS_RECOVERING` | 正在执行恢复动作(RTL等) |
| 5 | `LIMITS_RECOVERED` | 已恢复正常(不再违规) |

### LIMIT_MODULE — 限位模块（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `LIMIT_GPSLOCK` | GPS锁定限位 |
| 2 | `LIMIT_GEOFENCE` | 电子围栏限位 |
| 4 | `LIMIT_ALTITUDE` | 高度限位 |

---

## 6. 集结点标志位 (Rally Points)

### RALLY_FLAGS — 集结点标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `FAVORABLE_WIND` | 需要有利风向才能降落 |
| 2 | `LAND_IMMEDIATELY` | 立即下降到脱离高度并降落（不等GCS指令） |
| 4 | `ALT_FRAME_VALID` | 高度坐标系值有效 |
| 24 | `ALT_FRAME` | 2bit高度坐标系: 0=绝对, 1=相对home, 2=相对原点, 3=相对地面 |

---

## 7. 飞行模式 — 全机型

### 7.1 多旋翼 COPTER_MODE

| 值 | 标识符 | 模式名 | 中文说明 |
|:--:|--------|--------|----------|
| 0 | `COPTER_MODE_STABILIZE` | **STABILIZE** | 增稳模式（手动控制，自动水平） |
| 1 | `COPTER_MODE_ACRO` | **ACRO** | 特技模式（角速率控制，无自动水平） |
| 2 | `COPTER_MODE_ALT_HOLD` | **ALT HOLD** | 定高模式（手动水平+自动高度保持） |
| 3 | `COPTER_MODE_AUTO` | **AUTO** | 全自动任务模式 |
| 4 | `COPTER_MODE_GUIDED` | **GUIDED** | 引导模式（地面站/机载计算机遥控） |
| 5 | `COPTER_MODE_LOITER` | **LOITER** | 悬停模式（GPS锁定位置） |
| 6 | `COPTER_MODE_RTL` | **RTL** | 返航降落 |
| 7 | `COPTER_MODE_CIRCLE` | **CIRCLE** | 绕圈飞行 |
| 9 | `COPTER_MODE_LAND` | **LAND** | 原地降落 |
| 11 | `COPTER_MODE_DRIFT` | **DRIFT** | 漂移模式（定高+协调转弯） |
| 13 | `COPTER_MODE_SPORT` | **SPORT** | 运动模式（姿态角控制，更像传统航模） |
| 14 | `COPTER_MODE_FLIP` | **FLIP** | 翻转模式 |
| 15 | `COPTER_MODE_AUTOTUNE` | **AUTOTUNE** | 自动调参模式 |
| 16 | `COPTER_MODE_POSHOLD` | **POSHOLD** | 位置保持（摇杆映射为速度控制） |
| 17 | `COPTER_MODE_BRAKE` | **BRAKE** | 刹车模式 |
| 18 | `COPTER_MODE_THROW` | **THROW** | 抛飞模式 |
| 19 | `COPTER_MODE_AVOID_ADSB` | **AVOID ADSB** | ADS-B避障 |
| 20 | `COPTER_MODE_GUIDED_NOGPS` | **GUIDED NOGPS** | 无GPS引导模式 |
| 21 | `COPTER_MODE_SMART_RTL` | **SMART RTL** | 智能返航（沿原路返回） |
| 22 | `COPTER_MODE_FLOWHOLD` | **FLOWHOLD** | 光流位置保持 |
| 23 | `COPTER_MODE_FOLLOW` | **FOLLOW** | 跟随模式 |
| 24 | `COPTER_MODE_ZIGZAG` | **ZIGZAG** | Z字形扫描模式 |
| 25 | `COPTER_MODE_SYSTEMID` | **SYSTEMID** | 系统辨识模式 |
| 26 | `COPTER_MODE_AUTOROTATE` | **AUTOROTATE** | 自旋降落 |
| 27 | `COPTER_MODE_AUTO_RTL` | **AUTO RTL** | 自动触发RTL |
| 28 | `COPTER_MODE_TURTLE` | **TURTLE** | 翻正模式（翻转后恢复） |
| 29 | `COPTER_MODE_RATE_ACRO` | **RATE_ACRO** | 角速率特技模式 |

### 7.2 固定翼 PLANE_MODE

| 值 | 标识符 | 模式名 | 中文说明 |
|:--:|--------|--------|----------|
| 0 | `PLANE_MODE_MANUAL` | **MANUAL** | 纯手动（无任何增稳） |
| 1 | `PLANE_MODE_CIRCLE` | **CIRCLE** | 绕圈 |
| 2 | `PLANE_MODE_STABILIZE` | **STABILIZE** | 增稳（自动水平） |
| 3 | `PLANE_MODE_TRAINING` | **TRAINING** | 教练模式 |
| 4 | `PLANE_MODE_ACRO` | **ACRO** | 特技 |
| 5 | `PLANE_MODE_FLY_BY_WIRE_A` | **FBWA** | 线传A（限制横滚/俯仰角） |
| 6 | `PLANE_MODE_FLY_BY_WIRE_B` | **FBWB** | 线传B（定高+FBWA） |
| 7 | `PLANE_MODE_CRUISE` | **CRUISE** | 巡航模式（定高+地速控制） |
| 8 | `PLANE_MODE_AUTOTUNE` | **AUTOTUNE** | 自动调参 |
| 10 | `PLANE_MODE_AUTO` | **AUTO** | 全自动任务 |
| 11 | `PLANE_MODE_RTL` | **RTL** | 返航 |
| 12 | `PLANE_MODE_LOITER` | **LOITER** | 盘旋 |
| 13 | `PLANE_MODE_TAKEOFF` | **TAKEOFF** | 起飞 |
| 14 | `PLANE_MODE_AVOID_ADSB` | **AVOID ADSB** | ADS-B避障 |
| 15 | `PLANE_MODE_GUIDED` | **GUIDED** | 引导模式 |
| 16 | `PLANE_MODE_INITIALIZING` | **INITIALISING** | 初始化中 |
| 17 | `PLANE_MODE_QSTABILIZE` | **QSTABILIZE** | 四旋翼增稳(VTOL) |
| 18 | `PLANE_MODE_QHOVER` | **QHOVER** | 四旋翼悬停(VTOL) |
| 19 | `PLANE_MODE_QLOITER` | **QLOITER** | 四旋翼位置保持(VTOL) |
| 20 | `PLANE_MODE_QLAND` | **QLAND** | 四旋翼降落(VTOL) |
| 21 | `PLANE_MODE_QRTL` | **QRTL** | 四旋翼返航(VTOL) |
| 22 | `PLANE_MODE_QAUTOTUNE` | **QAUTOTUNE** | 四旋翼自动调参(VTOL) |
| 23 | `PLANE_MODE_QACRO` | **QACRO** | 四旋翼特技模式(VTOL) |
| 24 | `PLANE_MODE_THERMAL` | **THERMAL** | 热气流滑翔模式 |
| 25 | `PLANE_MODE_LOITER_ALT_QLAND` | **LOITER2QLAND** | 盘旋转四旋翼降落 |
| 26 | `PLANE_MODE_AUTOLAND` | **AUTOLAND** | 自动着陆 |

### 7.3 潜艇 SUB_MODE

| 值 | 标识符 | 模式名 | 中文说明 |
|:--:|--------|--------|----------|
| 0 | `SUB_MODE_STABILIZE` | **STABILIZE** | 增稳 |
| 1 | `SUB_MODE_ACRO` | **ACRO** | 特技 |
| 2 | `SUB_MODE_ALT_HOLD` | **ALT HOLD** | 定深 |
| 3 | `SUB_MODE_AUTO` | **AUTO** | 全自动任务 |
| 4 | `SUB_MODE_GUIDED` | **GUIDED** | 引导模式 |
| 7 | `SUB_MODE_CIRCLE` | **CIRCLE** | 绕圈 |
| 9 | `SUB_MODE_SURFACE` | **SURFACE** | 上浮 |
| 16 | `SUB_MODE_POSHOLD` | **POSHOLD** | 位置保持 |
| 19 | `SUB_MODE_MANUAL` | **MANUAL** | 手动 |
| 20 | `SUB_MODE_MOTORDETECT` | **MOTORDETECT** | 电机检测 |
| 21 | `SUB_MODE_SURFTRAK` | **SURFTRAK** | 水面追踪 |

### 7.4 无人车 ROVER_MODE

| 值 | 标识符 | 模式名 | 中文说明 |
|:--:|--------|--------|----------|
| 0 | `ROVER_MODE_MANUAL` | **MANUAL** | 手动 |
| 1 | `ROVER_MODE_ACRO` | **ACRO** | 特技 |
| 3 | `ROVER_MODE_STEERING` | **STEERING** | 转向控制 |
| 4 | `ROVER_MODE_HOLD` | **HOLD** | 保持 |
| 5 | `ROVER_MODE_LOITER` | **LOITER** | 盘旋 |
| 6 | `ROVER_MODE_FOLLOW` | **FOLLOW** | 跟随 |
| 7 | `ROVER_MODE_SIMPLE` | **SIMPLE** | 简单模式 |
| 8 | `ROVER_MODE_DOCK` | **DOCK** | 靠泊 |
| 9 | `ROVER_MODE_CIRCLE` | **CIRCLE** | 绕圈 |
| 10 | `ROVER_MODE_AUTO` | **AUTO** | 自动 |
| 11 | `ROVER_MODE_RTL` | **RTL** | 返航 |
| 12 | `ROVER_MODE_SMART_RTL` | **SMART RTL** | 智能返航 |
| 15 | `ROVER_MODE_GUIDED` | **GUIDED** | 引导模式 |
| 16 | `ROVER_MODE_INITIALIZING` | **INITIALISING** | 初始化中 |

### 7.5 天线追踪 TRACKER_MODE

| 值 | 标识符 | 模式名 | 中文说明 |
|:--:|--------|--------|----------|
| 0 | `TRACKER_MODE_MANUAL` | **MANUAL** | 手动 |
| 1 | `TRACKER_MODE_STOP` | **STOP** | 停止 |
| 2 | `TRACKER_MODE_SCAN` | **SCAN** | 扫描 |
| 3 | `TRACKER_MODE_SERVO_TEST` | **SERVO TEST** | 舵机测试 |
| 4 | `TRACKER_MODE_GUIDED` | **GUIDED** | 引导模式 |
| 10 | `TRACKER_MODE_AUTO` | **AUTO** | 自动追踪 |
| 16 | `TRACKER_MODE_INITIALIZING` | **INITIALISING** | 初始化中 |

---

## 8. 安全命令 (SECURE_COMMAND)

### SECURE_COMMAND_OP — 安全命令操作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `SECURE_COMMAND_GET_SESSION_KEY` | **获取8字节会话密钥**（用于飞控数据远程安全更新，如Bootloader公钥） |
| 1 | `SECURE_COMMAND_GET_REMOTEID_SESSION_KEY` | **获取RemoteID模块会话密钥** |
| 2 | `SECURE_COMMAND_REMOVE_PUBLIC_KEYS` | **移除指定范围的公钥**（若全部移除则禁用安全启动，可刷入未签名固件） |
| 3 | `SECURE_COMMAND_GET_PUBLIC_KEYS` | **获取当前公钥**（最多一次6个32字节密钥） |
| 4 | `SECURE_COMMAND_SET_PUBLIC_KEYS` | **设置公钥**（最多一次6个） |
| 5 | `SECURE_COMMAND_GET_REMOTEID_CONFIG` | **获取RemoteID模块配置** |
| 6 | `SECURE_COMMAND_SET_REMOTEID_CONFIG` | **设置RemoteID模块配置** |
| 7 | `SECURE_COMMAND_FLASH_BOOTLOADER` | **从本地存储刷写Bootloader**（使用MAVFtp上传的文件名） |

---

## 9. 远程日志

### MAV_REMOTE_LOG_DATA_BLOCK_COMMANDS — 远程日志控制命令

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 2147483645 | `MAV_REMOTE_LOG_DATA_BLOCK_STOP` | 停止发送DataFlash数据块 |
| 2147483646 | `MAV_REMOTE_LOG_DATA_BLOCK_START` | 开始发送DataFlash数据块 |

### MAV_REMOTE_LOG_DATA_BLOCK_STATUSES — 远程日志接收状态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `MAV_REMOTE_LOG_DATA_BLOCK_NACK` | 此数据块尚未收到 |
| 1 | `MAV_REMOTE_LOG_DATA_BLOCK_ACK` | 此数据块已收到 |

---

## 10. LED 控制

### LED_CONTROL_PATTERN — LED控制模式

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `LED_CONTROL_PATTERN_OFF` | LED关闭（控制权还给飞行器常规控制） |
| 1 | `LED_CONTROL_PATTERN_FIRMWAREUPDATE` | 固件更新模式LED指示 |
| 255 | `LED_CONTROL_PATTERN_CUSTOM` | 自定义模式（使用custom bytes字段） |

---

## 11. 设备总线操作

### DEVICE_OP_BUSTYPE — 设备操作总线类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `DEVICE_OP_BUSTYPE_I2C` | I2C设备操作 |
| 1 | `DEVICE_OP_BUSTYPE_SPI` | SPI设备操作 |

---

## 12. 深失速降落 (DeepStall)

### DEEPSTALL_STAGE — 深失速阶段

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `DEEPSTALL_STAGE_FLY_TO_LANDING` | 飞向着陆点 |
| 1 | `DEEPSTALL_STAGE_ESTIMATE_WIND` | 估算风速风向 |
| 2 | `DEEPSTALL_STAGE_WAIT_FOR_BREAKOUT` | 等待脱离盘旋进入进场 |
| 3 | `DEEPSTALL_STAGE_FLY_TO_ARC` | 飞向弧形路径的第一个点 |
| 4 | `DEEPSTALL_STAGE_ARC` | 沿弧形路径转弯回深失速着陆点 |
| 5 | `DEEPSTALL_STAGE_APPROACH` | 进场中 |
| 6 | `DEEPSTALL_STAGE_LAND` | 失速并转向着陆点 |

---

## 13. OSD参数编辑器

### OSD_PARAM_CONFIG_TYPE — OSD参数配置类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `OSD_PARAM_NONE` | 无 |
| 1 | `OSD_PARAM_SERIAL_PROTOCOL` | 串口协议 |
| 2 | `OSD_PARAM_SERVO_FUNCTION` | 舵机功能 |
| 3 | `OSD_PARAM_AUX_FUNCTION` | 辅助功能 |
| 4 | `OSD_PARAM_FLIGHT_MODE` | 飞行模式 |
| 5 | `OSD_PARAM_FAILSAFE_ACTION` | 失控保护动作 |
| 6 | `OSD_PARAM_FAILSAFE_ACTION_1` | 失控保护动作1 |
| 7 | `OSD_PARAM_FAILSAFE_ACTION_2` | 失控保护动作2 |
| 8 | `OSD_PARAM_NUM_TYPES` | 类型总数 |

### OSD_PARAM_CONFIG_ERROR — OSD参数配置错误

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `OSD_PARAM_SUCCESS` | 成功 |
| 1 | `OSD_PARAM_INVALID_SCREEN` | 无效画面 |
| 2 | `OSD_PARAM_INVALID_PARAMETER_INDEX` | 无效参数索引 |
| 3 | `OSD_PARAM_INVALID_PARAMETER` | 无效参数 |

---

## 14. GoPro 相机控制

### GOPRO_HEARTBEAT_STATUS — GoPro连接状态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GOPRO_HEARTBEAT_STATUS_DISCONNECTED` | 未连接GoPro |
| 1 | `GOPRO_HEARTBEAT_STATUS_INCOMPATIBLE` | 检测到的GoPro不兼容HeroBus |
| 2 | `GOPRO_HEARTBEAT_STATUS_CONNECTED` | HeroBus兼容的GoPro已连接 |
| 3 | `GOPRO_HEARTBEAT_STATUS_ERROR` | 遇到不可恢复错误（可能需要重新上电） |

### GOPRO_CAPTURE_MODE — GoPro拍摄模式

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GOPRO_CAPTURE_MODE_VIDEO` | 录像模式 |
| 1 | `GOPRO_CAPTURE_MODE_PHOTO` | 拍照模式 |
| 2 | `GOPRO_CAPTURE_MODE_BURST` | 连拍模式(Hero 3+) |
| 3 | `GOPRO_CAPTURE_MODE_TIME_LAPSE` | 延时摄影(Hero 3+) |
| 4 | `GOPRO_CAPTURE_MODE_MULTI_SHOT` | 连拍合成(Hero 4) |
| 5 | `GOPRO_CAPTURE_MODE_PLAYBACK` | 回放(Hero 4 Silver, 或Black连接LCD/HDMI) |
| 6 | `GOPRO_CAPTURE_MODE_SETUP` | 设置(Hero 4) |
| 255 | `GOPRO_CAPTURE_MODE_UNKNOWN` | 未知模式 |

### GOPRO_HEARTBEAT_FLAGS — GoPro心跳标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `GOPRO_FLAG_RECORDING` | GoPro正在录制 |

### GOPRO_COMMAND — GoPro命令

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GOPRO_COMMAND_POWER` | 电源(可读/可写) |
| 1 | `GOPRO_COMMAND_CAPTURE_MODE` | 拍摄模式(可读/可写) |
| 2 | `GOPRO_COMMAND_SHUTTER` | 快门(仅可写) |
| 3 | `GOPRO_COMMAND_BATTERY` | 电池(仅可读) |
| 4 | `GOPRO_COMMAND_MODEL` | 型号(仅可读) |
| 5 | `GOPRO_COMMAND_VIDEO_SETTINGS` | 视频设置(可读/可写) |
| 6 | `GOPRO_COMMAND_LOW_LIGHT` | 低光模式(可读/可写) |
| 7 | `GOPRO_COMMAND_PHOTO_RESOLUTION` | 照片分辨率(可读/可写) |
| 8 | `GOPRO_COMMAND_PHOTO_BURST_RATE` | 连拍速率(可读/可写) |
| 9 | `GOPRO_COMMAND_PROTUNE` | ProTune开关(可读/可写) |
| 10 | `GOPRO_COMMAND_PROTUNE_WHITE_BALANCE` | ProTune白平衡(可读/可写, Hero 3+) |
| 11 | `GOPRO_COMMAND_PROTUNE_COLOUR` | ProTune色彩(可读/可写, Hero 3+) |
| 12 | `GOPRO_COMMAND_PROTUNE_GAIN` | ProTune增益(可读/可写, Hero 3+) |
| 13 | `GOPRO_COMMAND_PROTUNE_SHARPNESS` | ProTune锐度(可读/可写, Hero 3+) |
| 14 | `GOPRO_COMMAND_PROTUNE_EXPOSURE` | ProTune曝光(可读/可写, Hero 3+) |
| 15 | `GOPRO_COMMAND_TIME` | 时间(可读/可写) |
| 16 | `GOPRO_COMMAND_CHARGING` | 充电(可读/可写) |

### GOPRO_RESOLUTION — GoPro分辨率

| 值 | 标识符 | 分辨率 |
|:--:|--------|--------|
| 0 | `GOPRO_RESOLUTION_480p` | 848×480 |
| 1 | `GOPRO_RESOLUTION_720p` | 1280×720 |
| 2 | `GOPRO_RESOLUTION_960p` | 1280×960 |
| 3 | `GOPRO_RESOLUTION_1080p` | 1920×1080 |
| 4 | `GOPRO_RESOLUTION_1440p` | 1920×1440 |
| 5 | `GOPRO_RESOLUTION_2_7k_17_9` | 2704×1440 (2.7K-17:9) |
| 6 | `GOPRO_RESOLUTION_2_7k_16_9` | 2704×1524 (2.7K-16:9) |
| 7 | `GOPRO_RESOLUTION_2_7k_4_3` | 2704×2028 (2.7K-4:3) |
| 8 | `GOPRO_RESOLUTION_4k_16_9` | 3840×2160 (4K-16:9) |
| 9 | `GOPRO_RESOLUTION_4k_17_9` | 4096×2160 (4K-17:9) |
| 10 | `GOPRO_RESOLUTION_720p_SUPERVIEW` | 1280×720 (SuperView) |
| 11 | `GOPRO_RESOLUTION_1080p_SUPERVIEW` | 1920×1080 (SuperView) |
| 12 | `GOPRO_RESOLUTION_2_7k_SUPERVIEW` | 2704×1520 (SuperView) |
| 13 | `GOPRO_RESOLUTION_4k_SUPERVIEW` | 3840×2160 (SuperView) |

### GOPRO_FRAME_RATE — GoPro帧率

| 值 | 标识符 | 帧率 |
|:--:|--------|:----:|
| 0 | `GOPRO_FRAME_RATE_12` | 12 fps |
| 1 | `GOPRO_FRAME_RATE_15` | 15 fps |
| 2 | `GOPRO_FRAME_RATE_24` | 24 fps |
| 3 | `GOPRO_FRAME_RATE_25` | 25 fps |
| 4 | `GOPRO_FRAME_RATE_30` | 30 fps |
| 5 | `GOPRO_FRAME_RATE_48` | 48 fps |
| 6 | `GOPRO_FRAME_RATE_50` | 50 fps |
| 7 | `GOPRO_FRAME_RATE_60` | 60 fps |
| 8 | `GOPRO_FRAME_RATE_80` | 80 fps |
| 9 | `GOPRO_FRAME_RATE_90` | 90 fps |
| 10 | `GOPRO_FRAME_RATE_100` | 100 fps |
| 11 | `GOPRO_FRAME_RATE_120` | 120 fps |
| 12 | `GOPRO_FRAME_RATE_240` | 240 fps |

### GOPRO_FIELD_OF_VIEW — GoPro视野

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GOPRO_FIELD_OF_VIEW_WIDE` | 广角 |
| 1 | `GOPRO_FIELD_OF_VIEW_MEDIUM` | 中等 |
| 2 | `GOPRO_FIELD_OF_VIEW_NARROW` | 窄角 |

### GOPRO_MODEL — GoPro型号

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GOPRO_MODEL_UNKNOWN` | 未知型号 |
| 1 | `GOPRO_MODEL_HERO_3_PLUS_SILVER` | Hero 3+ Silver (不支持HeroBus) |
| 2 | `GOPRO_MODEL_HERO_3_PLUS_BLACK` | Hero 3+ Black |
| 3 | `GOPRO_MODEL_HERO_4_SILVER` | Hero 4 Silver |
| 4 | `GOPRO_MODEL_HERO_4_BLACK` | Hero 4 Black |

---

## 15. ArduPilot 专用消息一览

| ID | 消息名 | 中文说明 |
|:--:|--------|----------|
| 150 | `SENSOR_OFFSETS` | 传感器偏移和校准值（已废弃→MAG_CAL_REPORT） |
| 152 | `MEMINFO` | 飞控RAM状态（堆顶、空闲内存） |
| 153 | `AP_ADC` | 原始ADC输出 |
| 160 | `FENCE_POINT` | 围栏点 |
| 161 | `FENCE_FETCH_POINT` | 请求围栏点 |
| 163 | `AHRS` | DCM姿态估计器状态 |
| 164 | `SIMSTATE` | 仿真环境状态 |
| 165 | `HWSTATUS` | 关键硬件状态（已废弃→POWER_STATUS） |
| 166 | `RADIO` | 数传电台状态（RSSI、噪声、错误计数） |
| 167 | `LIMITS_STATUS` | AP_Limits限位状态 |
| 168 | `WIND` | 风速风向估计 |
| 174 | `AIRSPEED_AUTOCAL` | 空速自动校准 |
| 175 | `RALLY_POINT` | 集结点 |
| 176 | `RALLY_FETCH_POINT` | 请求集结点 |
| 177 | `COMPASSMOT_STATUS` | 罗盘电机干扰校准状态 |
| 178 | `AHRS2` | 第二AHRS滤波器状态 |
| 179 | `CAMERA_STATUS` | 相机事件（拍照触发、心跳、错误等） |
| 180 | `CAMERA_FEEDBACK` | 相机拍照反馈 |
| 181 | `BATTERY2` | 第2块电池状态（已废弃→BATTERY_STATUS） |
| 182 | `AHRS3` | 第三AHRS滤波器状态 |
| 183 | `AUTOPILOT_VERSION_REQUEST` | 请求飞控版本 |
| 184 | `REMOTE_LOG_DATA_BLOCK` | 发送远程日志数据块 |
| 185 | `REMOTE_LOG_BLOCK_STATUS` | 远程日志数据块状态 |
| 186 | `LED_CONTROL` | 控制LED |
| 191 | `MAG_CAL_PROGRESS` | 罗盘校准进度报告 |
| 193 | `EKF_STATUS_REPORT` | **EKF状态报告**（标志位+各通道方差） |
| 194 | `PID_TUNING` | **PID调参信息**（期望/实际/FF/P/I/D） |
| 195 | `DEEPSTALL` | 深失速路径规划 |
| 200 | `GIMBAL_REPORT` | 3轴云台测量数据 |
| 201 | `GIMBAL_CONTROL` | 云台角速率控制 |
| 214 | `GIMBAL_TORQUE_CMD_REPORT` | 100Hz云台扭矩指令遥测 |
| 215 | `GOPRO_HEARTBEAT` | GoPro心跳 |
| 216 | `GOPRO_GET_REQUEST` | GoPro读取请求 |
| 217 | `GOPRO_GET_RESPONSE` | GoPro读取响应 |
| 218 | `GOPRO_SET_REQUEST` | GoPro设置请求 |
| 219 | `GOPRO_SET_RESPONSE` | GoPro设置响应 |
| 226 | `RPM` | 转速传感器输出 |
| 11000 | `DEVICE_OP_READ` | 设备寄存器读取 |
| 11001 | `DEVICE_OP_READ_REPLY` | 设备寄存器读取回复 |
| 11002 | `DEVICE_OP_WRITE` | 设备寄存器写入 |
| 11003 | `DEVICE_OP_WRITE_REPLY` | 设备寄存器写入回复 |
| 11004 | `SECURE_COMMAND` | 安全命令（需签名验证） |
| 11005 | `SECURE_COMMAND_REPLY` | 安全命令回复 |
| 11010 | `ADAP_TUNING` | 自适应控制器调参 |
| 11011 | `VISION_POSITION_DELTA` | 视觉姿态和位置增量 |
| 11020 | `AOA_SSA` | 攻角和侧滑角 |
| 11030-11032 | `ESC_TELEMETRY_1_TO_4` ~ `9_TO_12` | BLHeli电调遥测数据（温度/电压/电流/转速） |
| 11033 | `OSD_PARAM_CONFIG` | 配置OSD参数槽位 |
| 11034 | `OSD_PARAM_CONFIG_REPLY` | OSD参数配置回复 |
| 11035 | `OSD_PARAM_SHOW_CONFIG` | 读取OSD参数配置 |
| 11036 | `OSD_PARAM_SHOW_CONFIG_REPLY` | OSD参数读取回复 |
| 11037 | `OBSTACLE_DISTANCE_3D` | 3D障碍物位置 |
| 11038 | `WATER_DEPTH` | 水深数据 |
| 11039 | `MCU_STATUS` | MCU状态（温度和电压） |
| 11040-11044 | `ESC_TELEMETRY_13_TO_16` ~ `29_TO_32` | BLHeli电调遥测 13-32号 |
| 11060 | `NAMED_VALUE_STRING` | 键值对字符串（调试输出用） |

---

> 📌 **上一篇**：[01 — 通用指令集 (common)](01-通用指令集-common.md)
> 📌 **下一篇**：[03 — 厂商扩展指令集](03-厂商扩展指令集.md)
