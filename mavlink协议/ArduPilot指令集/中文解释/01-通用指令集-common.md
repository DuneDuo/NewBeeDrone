# 01 — 通用指令集 (common.xml)

> 来源：`common.xml` (8409行) — MAVLink 通用父集，所有无人机/无人车/潜艇通用
> 包含：`standard.xml` → `minimal.xml`（核心消息定义）

---

## 1. 系统故障标志位

### HL_FAILURE_FLAG — 高延迟遥测故障标志位（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `HL_FAILURE_FLAG_GPS` | GPS 故障 |
| 2 | `HL_FAILURE_FLAG_DIFFERENTIAL_PRESSURE` | 差压传感器故障 |
| 4 | `HL_FAILURE_FLAG_ABSOLUTE_PRESSURE` | 绝压传感器故障 |
| 8 | `HL_FAILURE_FLAG_3D_ACCEL` | 加速度计故障 |
| 16 | `HL_FAILURE_FLAG_3D_GYRO` | 陀螺仪故障 |
| 32 | `HL_FAILURE_FLAG_3D_MAG` | 磁力计故障 |
| 64 | `HL_FAILURE_FLAG_TERRAIN` | 地形子系统故障 |
| 128 | `HL_FAILURE_FLAG_BATTERY` | 电池故障/电量严重不足 |
| 256 | `HL_FAILURE_FLAG_RC_RECEIVER` | RC接收机故障/无RC连接 |
| 512 | `HL_FAILURE_FLAG_OFFBOARD_LINK` | 机载链路故障（4G/数传断连） |
| 1024 | `HL_FAILURE_FLAG_ENGINE` | 发动机故障 |
| 2048 | `HL_FAILURE_FLAG_GEOFENCE` | 电子围栏违规 |
| 4096 | `HL_FAILURE_FLAG_ESTIMATOR` | 状态估计器故障（如测量值被拒绝或方差过大） |
| 8192 | `HL_FAILURE_FLAG_MISSION` | 任务故障 |

---

## 2. 飞行模式和系统状态

### MAV_MODE — 预定义飞行模式（已废弃）

> ⚠️ 已于 2025-02 废弃，改用 `MAV_STANDARD_MODE` 或自定义模式

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `MAV_MODE_PREFLIGHT` | 系统未准备好飞行（启动中、校准中等） |
| 80 | `MAV_MODE_STABILIZE_DISARMED` | 允许激活，辅助RC控制，未解锁 |
| 208 | `MAV_MODE_STABILIZE_ARMED` | 允许激活，辅助RC控制，已解锁 |
| 64 | `MAV_MODE_MANUAL_DISARMED` | 允许激活，纯手动RC，无增稳，未解锁 |
| 192 | `MAV_MODE_MANUAL_ARMED` | 允许激活，纯手动RC，无增稳，已解锁 |
| 88 | `MAV_MODE_GUIDED_DISARMED` | 自主控制，手动设定点，未解锁 |
| 216 | `MAV_MODE_GUIDED_ARMED` | 自主控制，手动设定点，已解锁 |
| 92 | `MAV_MODE_AUTO_DISARMED` | 自主控制和导航，未解锁 |
| 220 | `MAV_MODE_AUTO_ARMED` | 自主控制和导航，已解锁 |
| 66 | `MAV_MODE_TEST_DISARMED` | 测试模式（仅开发者使用），未解锁 |
| 194 | `MAV_MODE_TEST_ARMED` | 测试模式（仅开发者使用），已解锁 |

### MAV_GOTO — 任务覆盖动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `MAV_GOTO_DO_HOLD` | 在当前位置悬停/保持 |
| 1 | `MAV_GOTO_DO_CONTINUE` | 继续执行任务中的下一项 |
| 2 | `MAV_GOTO_HOLD_AT_CURRENT_POSITION` | 在系统当前位置保持 |
| 3 | `MAV_GOTO_HOLD_AT_SPECIFIED_POSITION` | 在 DO_HOLD 参数指定的位置保持 |

---

## 3. 传感器状态

### MAV_SYS_STATUS_SENSOR — 传感器状态位掩码

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `MAV_SYS_STATUS_SENSOR_3D_GYRO` | 3D陀螺仪 |
| 2 | `MAV_SYS_STATUS_SENSOR_3D_ACCEL` | 3D加速度计 |
| 4 | `MAV_SYS_STATUS_SENSOR_3D_MAG` | 3D磁力计 |
| 8 | `MAV_SYS_STATUS_SENSOR_ABSOLUTE_PRESSURE` | 绝压传感器 |
| 16 | `MAV_SYS_STATUS_SENSOR_DIFFERENTIAL_PRESSURE` | 差压传感器 |
| 32 | `MAV_SYS_STATUS_SENSOR_GPS` | GPS |
| 64 | `MAV_SYS_STATUS_SENSOR_OPTICAL_FLOW` | 光流传感器 |
| 128 | `MAV_SYS_STATUS_SENSOR_VISION_POSITION` | 计算机视觉定位 |
| 256 | `MAV_SYS_STATUS_SENSOR_LASER_POSITION` | 激光定位 |
| 512 | `MAV_SYS_STATUS_SENSOR_EXTERNAL_GROUND_TRUTH` | 外部地面真值（Vicon/Leica） |
| 1024 | `MAV_SYS_STATUS_SENSOR_ANGULAR_RATE_CONTROL` | 3D角速度控制 |
| 2048 | `MAV_SYS_STATUS_SENSOR_ATTITUDE_STABILIZATION` | 姿态增稳 |
| 4096 | `MAV_SYS_STATUS_SENSOR_YAW_POSITION` | 偏航位置 |
| 8192 | `MAV_SYS_STATUS_SENSOR_Z_ALTITUDE_CONTROL` | Z轴/高度控制 |
| 16384 | `MAV_SYS_STATUS_SENSOR_XY_POSITION_CONTROL` | XY位置控制 |
| 32768 | `MAV_SYS_STATUS_SENSOR_MOTOR_OUTPUTS` | 电机输出/控制 |
| 65536 | `MAV_SYS_STATUS_SENSOR_RC_RECEIVER` | RC接收机 |
| 1048576 | `MAV_SYS_STATUS_GEOFENCE` | 电子围栏 |
| 2097152 | `MAV_SYS_STATUS_AHRS` | AHRS子系统健康 |
| 4194304 | `MAV_SYS_STATUS_TERRAIN` | 地形子系统健康 |
| 16777216 | `MAV_SYS_STATUS_LOGGING` | 日志记录 |
| 33554432 | `MAV_SYS_STATUS_SENSOR_BATTERY` | 电池 |
| 67108864 | `MAV_SYS_STATUS_SENSOR_PROXIMITY` | 避障/接近传感器 |
| 134217728 | `MAV_SYS_STATUS_SENSOR_SATCOM` | 卫星通信 |
| 268435456 | `MAV_SYS_STATUS_PREARM_CHECK` | 预解锁检查状态（解锁后始终为健康） |
| 536870912 | `MAV_SYS_STATUS_OBSTACLE_AVOIDANCE` | 避障/防撞 |
| 1073741824 | `MAV_SYS_STATUS_SENSOR_PROPULSION` | 推进系统（舵机/电调/电机/螺旋桨） |
| 2147483648 | `MAV_SYS_STATUS_EXTENSION_USED` | 扩展位域已启用 |

### MAV_SYS_STATUS_SENSOR_EXTENDED — 传感器扩展状态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `MAV_SYS_STATUS_RECOVERY_SYSTEM` | 回收系统（降落伞/气球/缩回装置等） |
| 2 | `MAV_SYS_STATUS_SENSOR_LEAK` | 泄漏检测 |

---

## 4. 坐标系定义 (MAV_FRAME)

> 坐标命名规则：
> - **GLOBAL**: WGS84经纬度，高度默认相对于平均海平面(MSL)
>   - `RELATIVE_ALT`: 高度相对于home点
>   - `TERRAIN_ALT`: 高度相对于地面
>   - `INT`: 经纬度乘以1E7的整数形式
> - **LOCAL**: 原点相对于地球固定
> - **BODY**: 原点随飞行器移动
> - **FRD**: Forward-Right-Down (前-右-下)
> - **FLU**: Forward-Left-Up (前-左-上)
> - **NED**: North-East-Down (北-东-下)
> - **ENU**: East-North-Up (东-北-上)

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `MAV_FRAME_GLOBAL` | WGS84坐标系 + 海拔高度(MSL) |
| 1 | `MAV_FRAME_LOCAL_NED` | NED本地切面坐标系（原点固定） |
| 2 | `MAV_FRAME_MISSION` | 非坐标系，表示任务指令 |
| 3 | `MAV_FRAME_GLOBAL_RELATIVE_ALT` | WGS84坐标系 + 相对home点高度 |
| 4 | `MAV_FRAME_LOCAL_ENU` | ENU本地切面坐标系（原点固定） |
| 5 | `MAV_FRAME_GLOBAL_INT` | WGS84坐标系(整数) + 海拔高度（已废弃，用MAV_FRAME_GLOBAL代替） |
| 6 | `MAV_FRAME_GLOBAL_RELATIVE_ALT_INT` | WGS84坐标系(整数) + 相对home高度（已废弃） |
| 7 | `MAV_FRAME_LOCAL_OFFSET_NED` | NED本地坐标系（原点随飞行器移动） |
| 8 | `MAV_FRAME_BODY_NED` | 机身NED（已废弃，用MAV_FRAME_BODY_FRD代替） |
| 10 | `MAV_FRAME_GLOBAL_TERRAIN_ALT` | WGS84坐标系 + 相对地面高度(AGL) |
| 12 | `MAV_FRAME_BODY_FRD` | **机身FRD坐标系（前-右-下）** — 最常用 |
| 20 | `MAV_FRAME_LOCAL_FRD` | 本地FRD切面（原点固定，前轴对齐飞行器前方水平面） |
| 21 | `MAV_FRAME_LOCAL_FLU` | 本地FLU切面（原点固定，前轴对齐飞行器前方水平面） |

---

## 5. 电子围栏 (FENCE)

### FENCE_BREACH — 围栏违规类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `FENCE_BREACH_NONE` | 无围栏违规 |
| 1 | `FENCE_BREACH_MINALT` | 低于最低高度限制 |
| 2 | `FENCE_BREACH_MAXALT` | 超过最高高度限制 |
| 3 | `FENCE_BREACH_BOUNDARY` | 越过围栏边界 |

### FENCE_MITIGATE — 围栏响应措施

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `FENCE_MITIGATE_UNKNOWN` | 未知 |
| 1 | `FENCE_MITIGATE_NONE` | 未采取措施 |
| 2 | `FENCE_MITIGATE_VEL_LIMIT` | 激活速度限制以防止违规 |

### FENCE_TYPE — 围栏类型（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `FENCE_TYPE_ALT_MAX` | 最大高度围栏 |
| 2 | `FENCE_TYPE_CIRCLE` | 圆形围栏 |
| 4 | `FENCE_TYPE_POLYGON` | 多边形围栏 |
| 8 | `FENCE_TYPE_ALT_MIN` | 最小高度围栏 |

---

## 6. 云台控制 (Gimbal)

### GIMBAL_DEVICE_CAP_FLAGS — 云台设备能力标志位（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_RETRACT` | 支持收回位置 |
| 2 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_NEUTRAL` | 支持水平前视中立位置（增稳） |
| 4 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_ROLL_AXIS` | 支持横滚轴旋转 |
| 8 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_ROLL_FOLLOW` | 支持横滚跟随飞行器 |
| 16 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_ROLL_LOCK` | 支持横滚锁定 |
| 32 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_PITCH_AXIS` | 支持俯仰轴旋转 |
| 64 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_PITCH_FOLLOW` | 支持俯仰跟随飞行器 |
| 128 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_PITCH_LOCK` | 支持俯仰锁定 |
| 256 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_YAW_AXIS` | 支持偏航轴旋转 |
| 512 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_YAW_FOLLOW` | 支持偏航跟随飞行器 |
| 1024 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_YAW_LOCK` | 支持偏航锁定到绝对方向（相对于北） |
| 2048 | `GIMBAL_DEVICE_CAP_FLAGS_SUPPORTS_INFINITE_YAW` | 支持无限偏航旋转（如使用滑环） |
| 4096 | `GIMBAL_DEVICE_CAP_FLAGS_SUPPORTS_YAW_IN_EARTH_FRAME` | 支持地球坐标系下的偏航角度 |
| 8192 | `GIMBAL_DEVICE_CAP_FLAGS_HAS_RC_INPUTS` | 支持通过RC输入控制云台 |
| 65536 | `GIMBAL_DEVICE_CAP_FLAGS_CAN_POINT_LOCATION_LOCAL` | 支持指向本地位置 |
| 131072 | `GIMBAL_DEVICE_CAP_FLAGS_CAN_POINT_LOCATION_GLOBAL` | 支持指向全球经纬度位置 |

### GIMBAL_DEVICE_FLAGS — 云台设备控制标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `GIMBAL_DEVICE_FLAGS_RETRACT` | 收回到安全位置（无增稳），优先级最高 |
| 2 | `GIMBAL_DEVICE_FLAGS_NEUTRAL` | 回到中立位置（通常为前视水平），优先级仅次于RETRACT |
| 4 | `GIMBAL_DEVICE_FLAGS_ROLL_LOCK` | 锁定横滚角（相对于地平线的绝对角度） |
| 8 | `GIMBAL_DEVICE_FLAGS_PITCH_LOCK` | 锁定俯仰角（相对于地平线的绝对角度） |
| 16 | `GIMBAL_DEVICE_FLAGS_YAW_LOCK` | 锁定偏航角（相对于北的绝对角度） |
| 32 | `GIMBAL_DEVICE_FLAGS_YAW_IN_VEHICLE_FRAME` | 偏航角相对于飞行器朝向 |
| 64 | `GIMBAL_DEVICE_FLAGS_YAW_IN_EARTH_FRAME` | 偏航角相对于北（地球坐标系） |
| 128 | `GIMBAL_DEVICE_FLAGS_ACCEPTS_YAW_IN_EARTH_FRAME` | 可接受地球坐标系偏航角输入（仅用于报告） |
| 256 | `GIMBAL_DEVICE_FLAGS_RC_EXCLUSIVE` | 云台仅由RC控制，MAVLink指令被忽略 |
| 512 | `GIMBAL_DEVICE_FLAGS_RC_MIXED` | 云台由RC和MAVLink混合控制 |

### GIMBAL_DEVICE_ERROR_FLAGS — 云台错误标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `GIMBAL_DEVICE_ERROR_FLAGS_AT_ROLL_LIMIT` | 达到横滚硬件限位 |
| 2 | `GIMBAL_DEVICE_ERROR_FLAGS_AT_PITCH_LIMIT` | 达到俯仰硬件限位 |
| 4 | `GIMBAL_DEVICE_ERROR_FLAGS_AT_YAW_LIMIT` | 达到偏航硬件限位 |
| 8 | `GIMBAL_DEVICE_ERROR_FLAGS_ENCODER_ERROR` | 编码器故障 |
| 16 | `GIMBAL_DEVICE_ERROR_FLAGS_POWER_ERROR` | 电源故障 |
| 32 | `GIMBAL_DEVICE_ERROR_FLAGS_MOTOR_ERROR` | 电机故障 |
| 64 | `GIMBAL_DEVICE_ERROR_FLAGS_SOFTWARE_ERROR` | 软件故障 |
| 128 | `GIMBAL_DEVICE_ERROR_FLAGS_COMMS_ERROR` | 通信故障 |
| 256 | `GIMBAL_DEVICE_ERROR_FLAGS_CALIBRATION_RUNNING` | 校准进行中 |
| 512 | `GIMBAL_DEVICE_ERROR_FLAGS_NO_MANAGER` | 未分配给云台管理器 |

---

## 7. 相机和存储

### CAMERA_STATUS_TYPES — 相机事件类型（ArduPilot）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `CAMERA_STATUS_TYPE_HEARTBEAT` | 相机心跳（1Hz，宣告相机组件ID） |
| 1 | `CAMERA_STATUS_TYPE_TRIGGER` | 相机拍照触发 |
| 2 | `CAMERA_STATUS_TYPE_DISCONNECT` | 相机连接丢失 |
| 3 | `CAMERA_STATUS_TYPE_ERROR` | 相机未知错误 |
| 4 | `CAMERA_STATUS_TYPE_LOWBATT` | 相机电池电量低（参数p1为电压值） |
| 5 | `CAMERA_STATUS_TYPE_LOWSTORE` | 相机存储空间低（参数p1为剩余拍摄张数） |
| 6 | `CAMERA_STATUS_TYPE_LOWSTOREV` | 相机存储空间低（参数p1为剩余录像分钟数） |

### CAMERA_FEEDBACK_FLAGS — 相机反馈标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `CAMERA_FEEDBACK_PHOTO` | 拍摄照片模式 |
| 1 | `CAMERA_FEEDBACK_VIDEO` | 拍摄视频模式 |
| 2 | `CAMERA_FEEDBACK_BADEXPOSURE` | 无法达到请求的曝光（如快门速度太低） |
| 3 | `CAMERA_FEEDBACK_CLOSEDLOOP` | 闭环反馈，确定拍照成功 |
| 4 | `CAMERA_FEEDBACK_OPENLOOP` | 开环触发，已请求拍照但不确定是否成功 |

### STORAGE_STATUS — 存储状态

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `STORAGE_STATUS_EMPTY` | 存储缺失（如未插入microSD卡） |
| 1 | `STORAGE_STATUS_UNFORMATTED` | 存储存在但未格式化 |
| 2 | `STORAGE_STATUS_READY` | 存储就绪可用 |
| 3 | `STORAGE_STATUS_NOT_SUPPORTED` | 相机不支持存储状态信息 |

### STORAGE_TYPE — 存储类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `STORAGE_TYPE_UNKNOWN` | 未知类型 |
| 1 | `STORAGE_TYPE_USB_STICK` | USB存储设备 |
| 2 | `STORAGE_TYPE_SD` | SD卡 |
| 3 | `STORAGE_TYPE_MICROSD` | microSD卡 |
| 4 | `STORAGE_TYPE_CF` | CFast卡 |
| 5 | `STORAGE_TYPE_CFE` | CFexpress卡 |
| 6 | `STORAGE_TYPE_XQD` | XQD卡 |
| 7 | `STORAGE_TYPE_HD` | 大容量硬盘 |
| 254 | `STORAGE_TYPE_OTHER` | 其他类型 |

---

## 8. MAV_CMD — 完整指令表

> 这是最核心的指令集。MAV_CMD 命令用于任务脚本、地面站控制和自主飞行。
> 命令参数映射方式：Param1-Param4 + X=Param5, Y=Param6, Z=Param7

### 8.1 导航指令 (NAV)

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 16 | `MAV_CMD_NAV_WAYPOINT` | **飞往航点** | 悬停时间、接受半径、经过半径、偏航角、经纬度、高度 |
| 17 | `MAV_CMD_NAV_LOITER_UNLIM` | **无限盘旋** | 盘旋半径（正=顺时针）、偏航角、经纬度、高度 |
| 18 | `MAV_CMD_NAV_LOITER_TURNS` | **盘旋N圈** | 圈数、到达航向才离开、盘旋半径、经纬度、高度 |
| 19 | `MAV_CMD_NAV_LOITER_TIME` | **盘旋N秒** | 时间(秒)、到达航向才离开、盘旋半径、经纬度、高度 |
| 20 | `MAV_CMD_NAV_RETURN_TO_LAUNCH` | **返航 (RTL)** | 无参数 |
| 21 | `MAV_CMD_NAV_LAND` | **降落** | 中止高度、精确降落模式、偏航角、经纬度、着陆高度 |
| 22 | `MAV_CMD_NAV_TAKEOFF` | **起飞** | 最小俯仰角、选项标志位、偏航角、经纬度、高度 |
| 23 | `MAV_CMD_NAV_LAND_LOCAL` | **在本地坐标降落** | 降落目标编号、最大偏移、下降速率、偏航、XYZ位置 |
| 24 | `MAV_CMD_NAV_TAKEOFF_LOCAL` | **从本地坐标起飞** | 最小俯仰、上升速率、偏航、XYZ位置 |
| 25 | `MAV_CMD_NAV_FOLLOW` | **跟随移动目标** | 跟随逻辑、目标地速、盘旋半径、偏航角、经纬度、高度 |
| 30 | `MAV_CMD_NAV_CONTINUE_AND_CHANGE_ALT` | **继续当前航线并改变高度** | 爬升/下降(0=中立/1=爬升/2=下降)、目标高度 |
| 31 | `MAV_CMD_NAV_LOITER_TO_ALT` | **盘旋直到达到高度** | 到达航向才离开、盘旋半径、经纬度、目标高度 |
| 82 | `MAV_CMD_NAV_SPLINE_WAYPOINT` | **样条曲线航点** | 悬停时间、经纬度、高度 |
| 83 | `MAV_CMD_NAV_ALTITUDE_WAIT` | **等待高度/下降速度条件**（高空气球等） | 目标高度、下降速度、舵面摆动时间 |
| 84 | `MAV_CMD_NAV_VTOL_TAKEOFF` | **VTOL起飞** | 过渡高度、经纬度、高度 |
| 85 | `MAV_CMD_NAV_VTOL_LAND` | **VTOL降落** | 经纬度、高度 |
| 189 | `MAV_CMD_NAV_DELAY` | **延时** | 延时秒数、小时、分钟、秒 |
| 4000 | `MAV_CMD_NAV_FENCE_RETURN_POINT` | **设置围栏返航点** | 经纬度、高度 |
| 5000 | `MAV_CMD_NAV_FENCE_POLYGON_VERTEX_INCLUSION` | **围栏多边形包含顶点** | 围栏编号、顶点编号、经纬度 |
| 5001 | `MAV_CMD_NAV_FENCE_POLYGON_VERTEX_EXCLUSION` | **围栏多边形排除顶点** | 围栏编号、顶点编号、经纬度 |
| 5002 | `MAV_CMD_NAV_FENCE_CIRCLE_INCLUSION` | **围栏圆形包含区域** | 半径、经纬度 |
| 5003 | `MAV_CMD_NAV_FENCE_CIRCLE_EXCLUSION` | **围栏圆形排除区域** | 半径、经纬度 |
| 5100 | `MAV_CMD_NAV_RALLY_POINT` | **集结点** | 经纬度、高度 |

### 8.2 条件指令 (CONDITION)

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 112 | `MAV_CMD_CONDITION_DELAY` | **条件延时** | 延时秒数 |
| 113 | `MAV_CMD_CONDITION_CHANGE_ALT` | **条件改变高度** | 爬升/下降速率、目标高度 |
| 114 | `MAV_CMD_CONDITION_DISTANCE` | **条件距离** | 距离(米) |
| 115 | `MAV_CMD_CONDITION_YAW` | **条件偏航** | 目标偏航角、角速度、方向(1=CW/-1=CCW) |

### 8.3 立即执行指令 (DO)

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 32 | `MAV_CMD_DO_FOLLOW` | **跟随目标** | 目标系统ID、高度模式、高度、返航时间 |
| 33 | `MAV_CMD_DO_FOLLOW_REPOSITION` | **调整跟随位置** | 相机四元数、高度偏置、XY偏置 |
| 34 | `MAV_CMD_DO_ORBIT` | **绕圈飞行** | 半径(正=CW)、切向速度、偏航模式、弧度数、中心点经纬度 |
| 35 | `MAV_CMD_DO_FIGURE_EIGHT` | **8字飞行** | 长轴半径、短轴半径、8字朝向、中心点经纬度 |
| 176 | `MAV_CMD_DO_SET_MODE` | **设置飞行模式** | 模式类型(1=自定义,2=标准)、自定义模式ID或标准模式 |
| 177 | `MAV_CMD_DO_JUMP` | **跳转到任务项** | 跳转序号、重复次数 |
| 178 | `MAV_CMD_DO_CHANGE_SPEED` | **改变速度** | 类型(0=空速/1=地速)、速度、油门值 |
| 179 | `MAV_CMD_DO_SET_HOME` | **设置Home点** | 使用方式(0=用当前位置/1=用参数位置)、经纬度、高度 |
| 180 | `MAV_CMD_DO_SET_PARAMETER` | **设置参数** | 参数编号、值 |
| 181 | `MAV_CMD_DO_SET_RELAY` | **设置继电器** | 继电器编号、开关(0=关/1=开) |
| 182 | `MAV_CMD_DO_REPEAT_RELAY` | **重复开关继电器** | 继电器编号、次数、周期(秒) |
| 183 | `MAV_CMD_DO_REPEAT_SERVO` | **重复驱动舵机** | 舵机编号、PWM值、次数、周期 |
| 184 | `MAV_CMD_DO_FLIGHTTERMINATION` | **终止飞行** | 终止确认(1=确认) |
| 185 | `MAV_CMD_DO_RALLY_LAND` | **集结点降落** | 目标高度、速度 |
| 189 | `MAV_CMD_DO_GO_AROUND` | **复飞** | 复飞高度、着陆中止高度 |
| 190 | `MAV_CMD_DO_SET_MISSION_CURRENT` | **设置当前任务序号** | 任务序号 |
| 192 | `MAV_CMD_DO_REPOSITION` | **重定位（引导模式）** | 地速、位掩码选项、偏航模式、偏航角、经纬度、高度 |
| 200 | `MAV_CMD_DO_MOTOR_TEST` | **电机测试** | 电机编号、油门值%、超时秒数、测试电机数量 |
| 201 | `MAV_CMD_DO_INVERTED_FLIGHT` | **倒飞切换** | 倒飞(0=正常/1=倒飞) |
| 203 | `MAV_CMD_DO_SET_ROI_LOCATION` | **设置兴趣点（位置）** | 经纬度、高度 |
| 212 | `MAV_CMD_DO_AUTOTUNE_ENABLE` | **启用自动调参** | 启用(1=启用/0=禁用)、要调参的轴 |
| 213 | `MAV_CMD_NAV_SET_YAW_SPEED` | **设置偏航速度** | 偏航角、速度(m/s)、角度偏移 |
| 214 | `MAV_CMD_DO_LAND_START` | **设置降落起始点** | 经纬度 |
| 215 | `MAV_CMD_DO_SET_RESUME_REPEAT_DIST` | **设置任务恢复重复距离** | 距离(m) |
| 216 | `MAV_CMD_DO_SPRAYER` | **控制喷洒器** | 0=关闭/1=开启 |
| 217 | `MAV_CMD_DO_SEND_SCRIPT_MESSAGE` | **发送脚本消息** | ID、参数1/2/3 |
| 218 | `MAV_CMD_DO_AUX_FUNCTION` | **执行辅助功能** | 辅助功能、开关位置 |
| 220 | `MAV_CMD_DO_MOUNT_CONFIGURE` | **配置相机云台/天线座** | 模式、增稳设置(roll/pitch/yaw) |
| 221 | `MAV_CMD_DO_MOUNT_CONTROL` | **控制相机云台/天线座** | 俯仰/横滚/偏航 |
| 222 | `MAV_CMD_DO_SET_CAM_TRIGG_DIST` | **设置按距离拍照** | 距离间隔(米)、快门积分时间、立即触发 |
| 224 | `MAV_CMD_DO_SET_CAM_TRIGG_INTERVAL` | **设置定时拍照** | 时间间隔(毫秒) |
| 240 | `MAV_CMD_DO_SET_ROI` | **设置兴趣区域(ROI)** | ROI类型、系统ID |
| 242 | `MAV_CMD_DO_SET_ROI_SYSID` | **按系统ID设置ROI** | 目标系统ID |
| 250 | `MAV_CMD_DO_VIDEO_START_CAPTURE` | **开始录像** | 相机ID、状态频率 |
| 251 | `MAV_CMD_DO_VIDEO_STOP_CAPTURE` | **停止录像** | 相机ID |
| 252 | `MAV_CMD_DO_CONTROL_VIDEO` | **控制视频/拍照** | 相机ID、动作(-1=停止/0=拍照/1=开始录像/2=复位/3=关闭) |
| 260 | `MAV_CMD_DO_SET_SERVO` | **设置舵机PWM** | 舵机编号、PWM脉宽(μs) |
| 280 | `MAV_CMD_DO_PARACHUTE` | **部署降落伞** | 动作(0=禁用/1=启用/2=释放) |
| 300 | `MAV_CMD_DO_GIMBAL_MANAGER_PITCHYAW` | **云台管理器俯仰偏航控制** | 俯仰角(deg)、偏航角(deg)、俯仰速率、偏航速率、标志位、GCS系统ID |
| 310 | `MAV_CMD_DO_GIMBAL_MANAGER_CONFIGURE` | **配置云台管理器** | 系统ID、管理器能力、主要/次要系统ID |
| 410 | `MAV_CMD_DO_SEND_BANNER` | **回复版本横幅** | 无参数 |
| 420 | `MAV_CMD_DO_START_RX_PAIRS` | **启动接收机对频** | 接收机类型、对频模式/时长 |
| 424 | `MAV_CMD_DO_GRIPPER` | **控制机械爪** | 实例编号、动作(0=释放/1=抓取/2=保持) |
| 426 | `MAV_CMD_DO_WINCH` | **控制绞盘** | 实例编号、动作、长度(m)、速率(m/s) |
| 430 | `MAV_CMD_DO_SET_STORAGE_USAGE` | **设置存储用途** | 存储ID、用途标志位 |
| 3000 | `MAV_CMD_DO_GIMBAL_MANAGER_ATTITUDE` | **云台管理器姿态控制** | 标志位、俯仰/横滚/偏航角、角速度 |
| 3001 | `MAV_CMD_DO_GIMBAL_MANAGER_POINT` | **云台管理器指向位置** | x,y,z经纬度、系统ID |

### 8.4 飞行前检查和校准指令 (PREFLIGHT)

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 241 | `MAV_CMD_PREFLIGHT_CALIBRATION` | **飞行前校准** | 陀螺仪(0=不校准/1=校准)、磁力计、空速、加速度计、地平线 |
| 242 | `MAV_CMD_PREFLIGHT_SET_SENSOR_OFFSETS` | **设置传感器偏移量** | 传感器类型、X/Y/Z偏移、温度 |
| 243 | `MAV_CMD_PREFLIGHT_UAVCAN` | **UAVCAN总线配置** | 是否需要节点ID/固件更新 |
| 245 | `MAV_CMD_PREFLIGHT_STORAGE` | **飞行前存储操作** | 参数读/写/重置、任务读/写/擦除 |
| 246 | `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN` | **重启/关机** | 动作(1=重启/2=关机/3=进入Bootloader)、组件ID |

### 8.5 消息请求指令

| ID | 指令名 | 中文说明 |
|:--:|--------|----------|
| 512 | `MAV_CMD_REQUEST_MESSAGE` | **请求特定消息**（指定消息ID，地面站会收到响应） |
| 519 | `MAV_CMD_REQUEST_PROTOCOL_VERSION` | **请求协议版本** |
| 520 | `MAV_CMD_REQUEST_AUTOPILOT_CAPABILITIES` | **请求飞控能力信息** |
| 521 | `MAV_CMD_REQUEST_CAMERA_INFORMATION` | **请求相机信息** |
| 522 | `MAV_CMD_REQUEST_CAMERA_SETTINGS` | **请求相机设置** |
| 525 | `MAV_CMD_REQUEST_STORAGE_INFORMATION` | **请求存储信息** |
| 527 | `MAV_CMD_REQUEST_FLIGHT_INFORMATION` | **请求飞行信息** |
| 529 | `MAV_CMD_REQUEST_VIDEO_STREAM_INFORMATION` | **请求视频流信息** |
| 530 | `MAV_CMD_REQUEST_VIDEO_STREAM_STATUS` | **请求视频流状态** |
| 2500 | `MAV_CMD_REQUEST_SMART_BATTERY_INFO` | **请求智能电池信息** |
| 2510 | `MAV_CMD_REQUEST_GENERATOR_STATUS` | **请求发电机状态** |

### 8.6 执行器控制指令

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 400 | `MAV_CMD_COMPONENT_ARM_DISARM` | **解锁/加锁** | 1=解锁/0=加锁、强制(21196) |
| 410 | `MAV_CMD_GET_HOME_POSITION` | **获取Home位置** | - |
| 510 | `MAV_CMD_SET_MESSAGE_INTERVAL` | **设置消息发送频率** | 消息ID、间隔(μs) |
| 511 | `MAV_CMD_GET_MESSAGE_INTERVAL` | **获取消息发送频率** | 消息ID |
| 5200 | `MAV_CMD_REQUEST_OPERATOR_CONTROL` | **请求操控权** | 请求or释放、密码 |

### 8.7 避障和限位

| ID | 指令名 | 中文说明 | 主要参数 |
|:--:|--------|----------|----------|
| 4500 | `MAV_CMD_DO_SET_OBSTACLE_AVOIDANCE_INTERVAL` | **设置避障消息频率间隔** | 间隔(μs) |
| 4501 | `MAV_CMD_LIMITS_SET` | **设置限位值** | 类型(0=GPS锁/1=围栏/2=高度)、最大/最小值 |
| 4502 | `MAV_CMD_LIMITS_GET` | **获取限位值** | 类型 |
| 4600 | `MAV_CMD_DO_FENCE_ENABLE` | **启用/禁用围栏** | 启用(1)/禁用(0)、围栏类型位掩码 |

---

## 9. 参数和校准相关枚举

### PREFLIGHT_STORAGE_PARAMETER_ACTION — 存储参数操作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `PARAM_READ_PERSISTENT` | 从持久存储读入所有参数到内存 |
| 1 | `PARAM_WRITE_PERSISTENT` | 将所有参数写入持久存储(Flash/EEPROM) |
| 2 | `PARAM_RESET_FACTORY_DEFAULT` | 恢复出厂默认参数（传感器校准、安全设置等） |
| 3 | `PARAM_RESET_SENSOR_DEFAULT` | 仅恢复传感器校准参数为出厂默认 |
| 4 | `PARAM_RESET_ALL_DEFAULT` | 重置所有参数为默认值 |

### PREFLIGHT_CALIBRATION_MAGNETOMETER — 磁力计校准动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `PREFLIGHT_CALIBRATION_MAGNETOMETER_NONE` | 无操作 |
| 1 | `PREFLIGHT_CALIBRATION_MAGNETOMETER_START` | 开始磁力计校准 |
| 76 | `PREFLIGHT_CALIBRATION_MAGNETOMETER_FORCE_SAVE` | 强制接受现有罗盘校准为有效（不重新校准） |

### PREFLIGHT_CALIBRATION_ACCELEROMETER — 加速度计校准动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_NONE` | 无操作 |
| 1 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_FULL` | 完整6位置加速度计校准 |
| 2 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_TRIM` | 板级（trim）校准 |
| 3 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_TEMPERATURE` | 加速度计温度校准 |
| 4 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_SIMPLE` | 简单加速度计校准 |
| 76 | `PREFLIGHT_CALIBRATION_ACCELEROMETER_FORCE_SAVE` | 强制接受现有加速度计校准 |

### REBOOT_SHUTDOWN_ACTION — 重启/关机动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `REBOOT_SHUTDOWN_ACTION_NONE` | 无操作 |
| 1 | `REBOOT_SHUTDOWN_ACTION_REBOOT` | 重启组件 |
| 2 | `REBOOT_SHUTDOWN_ACTION_SHUTDOWN` | 关闭组件 |
| 3 | `REBOOT_SHUTDOWN_ACTION_REBOOT_TO_BOOTLOADER` | 重启并停留在Bootloader中等待升级 |
| 4 | `REBOOT_SHUTDOWN_ACTION_POWER_ON` | 上电（若已上电则忽略） |

---

## 10. 执行器功能

### ACTUATOR_OUTPUT_FUNCTION — 执行器输出功能

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `ACTUATOR_OUTPUT_FUNCTION_NONE` | 无功能（禁用） |
| 1-16 | `ACTUATOR_OUTPUT_FUNCTION_MOTOR1` ~ `MOTOR16` | 电机1至16 |
| 33-48 | `ACTUATOR_OUTPUT_FUNCTION_SERVO1` ~ `SERVO16` | 舵机1至16 |

---

## 11. ESC电调相关

### ESC_CONNECTION_TYPE — 电调连接类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `ESC_CONNECTION_TYPE_PPM` | 传统PPM电调 |
| 1 | `ESC_CONNECTION_TYPE_SERIAL` | 串行总线电调 |
| 2 | `ESC_CONNECTION_TYPE_ONESHOT` | OneShot PPM电调 |
| 3 | `ESC_CONNECTION_TYPE_I2C` | I2C电调 |
| 4 | `ESC_CONNECTION_TYPE_CAN` | CAN总线电调 |
| 5 | `ESC_CONNECTION_TYPE_DSHOT` | DShot电调 |

### ESC_FAILURE_FLAGS — 电调故障标志位

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `ESC_FAILURE_OVER_CURRENT` | 过流故障 |
| 2 | `ESC_FAILURE_OVER_VOLTAGE` | 过压故障 |
| 4 | `ESC_FAILURE_OVER_TEMPERATURE` | 过热故障 |
| 8 | `ESC_FAILURE_OVER_RPM` | 过速故障 |
| 16 | `ESC_FAILURE_INCONSISTENT_CMD` | 指令不一致故障（超出范围） |
| 32 | `ESC_FAILURE_MOTOR_STUCK` | 电机堵转故障 |
| 64 | `ESC_FAILURE_GENERIC` | 通用ESC故障 |

---

## 12. 标准协议能力标志位 (standard.xml)

### MAV_PROTOCOL_CAPABILITY — 飞控协议能力（位掩码）

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 1 | `MAV_PROTOCOL_CAPABILITY_MISSION_FLOAT` | 支持MISSION_ITEM浮点消息（已废弃） |
| 2 | `MAV_PROTOCOL_CAPABILITY_PARAM_FLOAT` | 支持参数浮点消息（已废弃，用C_CAST代替） |
| 4 | `MAV_PROTOCOL_CAPABILITY_MISSION_INT` | **支持MISSION_ITEM_INT整数消息**（必须设置） |
| 8 | `MAV_PROTOCOL_CAPABILITY_COMMAND_INT` | **支持COMMAND_INT整数消息** |
| 16 | `MAV_PROTOCOL_CAPABILITY_PARAM_ENCODE_BYTEWISE` | 参数协议使用逐字节编码 |
| 32 | `MAV_PROTOCOL_CAPABILITY_FTP` | **支持文件传输协议FTP v1** |
| 64 | `MAV_PROTOCOL_CAPABILITY_SET_ATTITUDE_TARGET` | 支持机载控制姿态 |
| 128 | `MAV_PROTOCOL_CAPABILITY_SET_POSITION_TARGET_LOCAL_NED` | 支持本地NED坐标系位置/速度控制 |
| 256 | `MAV_PROTOCOL_CAPABILITY_SET_POSITION_TARGET_GLOBAL_INT` | 支持全球整数坐标位置/速度控制 |
| 512 | `MAV_PROTOCOL_CAPABILITY_TERRAIN` | 支持地形协议 |
| 2048 | `MAV_PROTOCOL_CAPABILITY_FLIGHT_TERMINATION` | 支持飞行终止指令 |
| 4096 | `MAV_PROTOCOL_CAPABILITY_COMPASS_CALIBRATION` | 支持板载罗盘校准 |
| 8192 | `MAV_PROTOCOL_CAPABILITY_MAVLINK2` | **支持MAVLink v2** |
| 16384 | `MAV_PROTOCOL_CAPABILITY_MISSION_FENCE` | 支持任务围栏协议 |
| 32768 | `MAV_PROTOCOL_CAPABILITY_MISSION_RALLY` | 支持集结点协议 |
| 131072 | `MAV_PROTOCOL_CAPABILITY_PARAM_ENCODE_C_CAST` | 参数协议使用C类型转换编码 |
| 262144 | `MAV_PROTOCOL_CAPABILITY_COMPONENT_IMPLEMENTS_GIMBAL_MANAGER` | 组件实现了云台管理器 |
| 524288 | `MAV_PROTOCOL_CAPABILITY_COMPONENT_ACCEPTS_GCS_CONTROL` | 支持将控制权锁定给特定GCS |
| 1048576 | `MAV_PROTOCOL_CAPABILITY_GRIPPER` | 连接了机械爪 |

### FIRMWARE_VERSION_TYPE — 固件版本类型

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `FIRMWARE_VERSION_TYPE_DEV` | 开发版 |
| 64 | `FIRMWARE_VERSION_TYPE_ALPHA` | Alpha版 |
| 128 | `FIRMWARE_VERSION_TYPE_BETA` | Beta版 |
| 192 | `FIRMWARE_VERSION_TYPE_RC` | 候选发布版(Release Candidate) |
| 255 | `FIRMWARE_VERSION_TYPE_OFFICIAL` | 正式稳定版 |

---

## 13. 绞盘和机械爪

### WINCH_ACTIONS — 绞盘动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `WINCH_RELAXED` | 电机自由转动 |
| 1 | `WINCH_RELATIVE_LENGTH_CONTROL` | 收放指定长度（可选指定速率） |
| 2 | `WINCH_RATE_CONTROL` | 按指定速率收放 |
| 3 | `WINCH_LOCK` | 锁定（收回到最紧位置后释放电机） |
| 4 | `WINCH_DELIVER` | 投递序列（下放→减速→触地→回收→锁定） |
| 5 | `WINCH_HOLD` | 电机保持当前位置 |
| 6 | `WINCH_RETRACT` | 完全收回 |
| 7 | `WINCH_LOAD_LINE` | 装线（计算总长度，张力超过阈值时停止） |
| 8 | `WINCH_ABANDON_LINE` | 放出全部线缆 |
| 9 | `WINCH_LOAD_PAYLOAD` | 放出刚好够挂载载荷的长度 |

### GRIPPER_ACTIONS — 机械爪动作

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `GRIPPER_ACTION_RELEASE` | 释放货物 |
| 1 | `GRIPPER_ACTION_GRAB` | 抓取货物 |
| 2 | `GRIPPER_ACTION_HOLD` | 保持当前抓取状态/位置 |

---

## 14. 绕圈飞行偏航模式

### ORBIT_YAW_BEHAVIOUR — 绕圈偏航行为

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `ORBIT_YAW_BEHAVIOUR_HOLD_FRONT_TO_CIRCLE_CENTER` | 机头始终指向圆心（默认） |
| 1 | `ORBIT_YAW_BEHAVIOUR_HOLD_INITIAL_HEADING` | 保持接收指令时的初始偏航方向 |
| 2 | `ORBIT_YAW_BEHAVIOUR_UNCONTROLLED` | 偏航不控制 |
| 3 | `ORBIT_YAW_BEHAVIOUR_HOLD_FRONT_TANGENT_TO_CIRCLE` | 机头跟随飞行路径（与圆相切） |
| 4 | `ORBIT_YAW_BEHAVIOUR_RC_CONTROLLED` | 偏航由RC控制 |
| 5 | `ORBIT_YAW_BEHAVIOUR_UNCHANGED` | 使用当前偏航行为不变 |

---

## 15. 网络通信

### WIFI_CONFIG_AP_MODE — WiFi模式

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `WIFI_CONFIG_AP_MODE_UNDEFINED` | 未定义 |
| 1 | `WIFI_CONFIG_AP_MODE_AP` | 接入点模式(AP) |
| 2 | `WIFI_CONFIG_AP_MODE_STATION` | 工作站模式(连接现有WiFi) |
| 3 | `WIFI_CONFIG_AP_MODE_DISABLED` | WiFi禁用 |

### CELLULAR_CONFIG_RESPONSE — 蜂窝网络配置响应

| 值 | 标识符 | 中文说明 |
|:--:|--------|----------|
| 0 | `CELLULAR_CONFIG_RESPONSE_ACCEPTED` | 更改已接受 |
| 1 | `CELLULAR_CONFIG_RESPONSE_APN_ERROR` | APN无效 |
| 2 | `CELLULAR_CONFIG_RESPONSE_PIN_ERROR` | PIN无效 |
| 3 | `CELLULAR_CONFIG_RESPONSE_REJECTED` | 更改被拒绝 |
| 4 | `CELLULAR_CONFIG_BLOCKED_PUK_REQUIRED` | SIM卡锁定，需要PUK码解锁 |

---

> 📌 **下一篇**：[02 — ArduPilot 专用指令集](02-ArduPilot专用指令集.md) — ArduPilot特有命令、飞行模式、EKF状态、云台、GoPro等
