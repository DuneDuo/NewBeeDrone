# NewBeeDrone Mission / Security 架构设计

> 文档定位：服务器端（Server）模块架构与接口约定。本文整理已确定的职责边界、公开接口和文件结构，不代表这些接口均已实现。尚未确定的实现细节集中列于文末。

## 1. 背景与设计目标

NewBeeDrone 需要在单个飞行动作之外，提供飞控任务计划管理和持续运行的安全监督能力。为避免任务协议、配送流程与安全处置混杂，采用以下分工：

- 命令模块（Command）：执行单个飞行动作，并管理命令的等待、完成、失败与取消。
- 任务计划模块（Mission）：管理飞行控制器（Flight Controller，以下简称飞控）保存的任务计划。
- 安全监督模块（Security）：持续读取遥测（Telemetry），发现异常并通过 Command 执行安全处置。
- 业务层（Business Layer）：编排配送等业务流程，组合调用 Command 和 Mission。

设计目标：

1. 对上层提供少量、稳定的应用程序编程接口（Application Programming Interface，API）。
2. 将任务协议传输状态与业务状态机（State Machine）分离。
3. 使安全监督不依赖业务层主动轮询，能够抢占正在等待的普通命令。
4. 复用统一遥测、通信能力及公共配置，保持单向依赖。
5. 第一版按职责拆分文件，不提前引入复杂框架或独立配置系统。

本文的 Security 指运行安全（Safety）监督，不承担身份认证、访问控制等信息安全能力，也不等同于独立硬件安全系统。

## 2. API 的含义与层次

API 约定调用名称、参数、结果及错误语义。调用方表达意图，由被调用模块封装内部实现。例如 `drone.mission.upload(items)` 表示上传任务计划，业务层不需要处理逐条请求、重传或确认消息。

| 层次 | 示例 | 职责 |
| --- | --- | --- |
| Web 接口（Web API） | 将来供前端使用的服务接口 | 将外部请求交给业务层；本文不定义具体路由 |
| 项目内部 Python API | `drone.cmd.takeoff(alt)`、`drone.mission.upload(items)` | 表达模块能力，是本文的主要设计对象 |
| 第三方库 API | pymavlink 提供的消息构造与发送能力 | 实现协议消息编码、解码等基础功能 |
| 通信协议（Protocol） | MAVLink 命令协议、任务协议 | 定义通信双方交换的消息及交互规则 |
| 传输通道（Transport） | 项目最终选定的链路 | 承载协议数据；本文不确定硬件连接或部署方式 |

MAVLink（Micro Air Vehicle Link）协议与项目内部 API 属于不同层次。上层接口不应因底层传输方式变化而改变。

## 3. 职责边界

| 模块 | 负责 | 不负责 |
| --- | --- | --- |
| Mission | 上传、下载、清空任务计划；设置当前任务项；维护本地传输状态及已观测进度 | 配送 A→B 的业务状态机；解锁、起飞、保持、返航等即时动作 |
| Security | 独立线程监督；读取统一遥测；检测、策略判断、抢占与安全动作调度；报告自身状态 | 自行收取链路数据；直接拼装或发送 MAVLink；维护另一套飞机遥测；编排配送业务 |
| Command | 单个飞行动作的参数处理、发送、确认、完成判断；本地命令取消 | 整条任务计划上传协议；配送流程；持续安全巡检 |
| 业务层 | 业务前置检查、任务编排、调用顺序、业务完成及失败处理 | 任务协议握手；绕过 Command 发安全动作 |
| MAVLink 层 | 消息编解码、统一收发与消息分发所需基础能力 | 业务决策、安全策略 |
| 统一遥测状态 | 保存收到的飞机状态、更新时间和有效性信息 | 发出飞行动作、决定安全策略 |

`PRECHECK`、`DELIVERY`、`RETURNING` 等业务状态属于业务层。Mission 内部的上传、下载、成功、失败等状态仅描述协议操作，不能代替业务状态。

## 4. Mission API

对外主要入口为 `MissionManager`，使用形式为：

```python
drone.mission.upload(items)
drone.mission.download()
drone.mission.clear()
drone.mission.set_current(seq)
drone.mission.status()
```

| 接口 | 参数 | 语义及结果 |
| --- | --- | --- |
| `upload(items)` | 有序任务项集合 | 将计划上传至飞控；管理完整传输过程并报告成功或失败。上传成功不代表开始执行或业务完成 |
| `download()` | 无 | 获取飞控保存的任务计划，成功后返回任务项集合；用于核对、调试和恢复时的信息读取 |
| `clear()` | 无 | 清除本接口所管理的飞控任务计划，报告操作结果；不等同于暂停飞行 |
| `set_current(seq)` | 任务项序号，从 0 开始 | 请求切换当前任务项；可能影响正在执行的计划，不是单纯修改本地字段，也不负责解锁或启动业务 |
| `status()` | 无 | 返回本地状态快照（Snapshot），不主动向飞控发送查询，也不改变飞机状态 |

### 4.1 任务传输

上传的主要交互为发送 `MISSION_COUNT`，按飞控的 `MISSION_REQUEST_INT` 请求发送 `MISSION_ITEM_INT`，最后处理任务确认消息（Acknowledgement，ACK）`MISSION_ACK`。下载由 `MISSION_REQUEST_LIST` 发起，按序获取任务项并完成确认；清空使用 `MISSION_CLEAR_ALL`。传输实现负责超时、重试与错误结果处理。协议依据见 [MAVLink Mission Protocol](https://mavlink.io/en/services/mission.html)。

上层不得自行实现上传循环。一次操作失败时，不能把部分接收的下载结果当作完整计划，也不能仅因本地消息发送成功就宣告操作成功。

### 4.2 当前任务项与状态查询

`set_current(seq)` 的协议映射需要与实际飞控能力匹配。MAVLink 定义了 `MAV_CMD_DO_SET_MISSION_CURRENT`，并保留旧的 `MISSION_SET_CURRENT` 相关流程；本项目的兼容范围和确认判据需在实现时确定。任务进度可根据收到的 `MISSION_CURRENT`、`MISSION_ITEM_REACHED` 更新。参见 [MAVLink 任务管理与进度消息](https://mavlink.io/en/services/mission.html#messageenum-summary)。

建议 `status()` 至少表达以下信息，具体类型尚未冻结：

| 信息 | 含义 |
| --- | --- |
| `state` | 当前本地协议操作状态 |
| `count` | 最近一次已知的任务项数量 |
| `current_seq` | 最近观测到的当前任务项 |
| `last_reached` | 最近收到的已到达任务项 |
| 更新时间、有效性 | 区分已知、未知及过期数据 |
| 最近操作结果或错误 | 便于业务层定位失败 |

尚未获取的数据应表达为未知，不能默认为 0。进度消息的到达取决于实际运行状态与链路，不保证每个检查周期都有更新。

### 4.3 与 Command 的边界

Mission 不增加 `start()`、`pause()`、`rtl()` 等飞行动作接口。业务层上传计划后，通过 Command 请求执行所需动作，例如 `drone.cmd.set_mode("mission")`；具体前置条件及模式映射由 Command 与业务层落实。

保持位置（Hold）、返航（Return to Launch，RTL）和降落（Land）分别通过 `cmd.hold()`、`cmd.rtl()`、`cmd.land()` 请求。任务计划中可以包含飞行动作类型的任务项，但存储这些任务项与立即执行动作是不同职责。

若 `set_current()` 最终采用命令协议，应复用统一命令事务能力，避免另建一套命令确认与重试逻辑；其内部适配方式列为待细化事项，不改变对外的 Mission API。

## 5. Security API

Security 使用独立监督线程（Thread），公开接口保持精简：

```python
security.start()
security.stop()
security.status()
security.check_once()  # 主要用于调试和测试
```

| 接口 | 职责 | 使用方及约束 |
| --- | --- | --- |
| `start()` | 启动持续监督循环 | 由应用生命周期管理代码调用；实现应避免重复创建线程 |
| `stop()` | 请求监督线程结束并清理相关资源 | 主要用于程序关闭和测试；不表示飞机停止动作 |
| `status()` | 返回监督运行状态及最近检查信息 | 供业务层或 Web 查询；只读，无控制副作用 |
| `check_once()` | 执行一轮检查，供验证检测结果使用 | 主要用于调试和测试；是否包含策略执行尚未明确，接入前必须确定其副作用契约 |

`status()` 建议包含 `running`、`level`、`last_check`、当前事件以及最近处置结果。字段类型和事件集合形式在实现时统一。

正常运行不要求业务层反复调用电量、心跳等检查函数。监督循环按以下顺序工作：

```text
读取统一遥测状态
        ↓
checks：检测异常，生成事件
        ↓
policy：评估事件，选择处置
        ↓
manager：记录事件，必要时抢占并执行动作
        ↓
更新监督状态，等待下一周期
```

建议将 `check_once()` 定义为仅检测并返回事件，由正式监督循环显式执行策略和动作；此项是为消除调试副作用歧义提出的实现建议，不作为此前已确认的约定。

### 5.1 抢占 Command

抢占（Preemption）的已确定顺序为：

```text
检测到异常 → 策略确定动作 → cmd.cancel(reason) → cmd.hold()/rtl()/land()
```

`cmd.cancel(reason)` 是 CommandManager 的本地控制操作：将当前命令置为取消终态、记录原因、解除等待并释放当前命令占用。它不表示飞控已停止执行旧动作，也不等同于向飞控发送某个取消消息。

安全动作仍由 Command 统一执行。命令确认与实际动作完成应区分：底层确认的含义由命令协议定义，动作完成则需要各命令适用的反馈判据，不能统一把收到 ACK 当作飞行目标达成。参见 [MAVLink Command Protocol](https://mavlink.io/en/services/command.html)。

实现必须处理取消与安全命令提交之间的竞争：业务线程被唤醒后，不能抢先提交普通命令覆盖安全处置。仅连续调用两个函数不能保证原子性（Atomicity）；具体锁、优先级或控制权机制需在 Command 集成阶段落实。

### 5.2 检测与策略分离

`checks.py` 回答“发生了什么”，输出安全事件（Safety Event）；`policy.py` 回答“如何处理”，输出处置决策。检查函数不得直接调用 `rtl()` 等动作。

候选检查包括电量、心跳（Heartbeat）、定位有效性、飞行状态、地理围栏（Geofence）、遥测新鲜度以及命令是否超时。是否启用取决于实际可用数据和策略配置，本文不认定所有检查均已具备输入。

例如“电量告警 → 记录告警”“严重低电量 → 返航”“紧急低电量 → 降落”仅用于解释检测与策略的分工，不是已批准的运行规则。具体阈值、优先级、动作前置条件和恢复条件尚待确定。

## 6. 文件结构与职责

以下为目标结构。`core/`、`web/` 等仅表示集成位置，不据此声明其现有实现内容；业务层的具体目录另行确定。

```text
Server/
├── mission/
│   ├── __init__.py
│   ├── manager.py
│   ├── transfer.py
│   └── models.py
├── security/
│   ├── __init__.py
│   ├── manager.py
│   ├── checks.py
│   ├── policy.py
│   └── models.py
├── command/
├── mavlink/
├── core/
├── web/
└── config.py
```

### 6.1 `mission/`

| 文件 | 职责 | 边界 |
| --- | --- | --- |
| `__init__.py` | 导出 `MissionManager`、`MissionItem` 等公开类型 | 不启动线程、不建立连接；不要求上层导入内部传输类 |
| `manager.py` | 实现五个 Mission API；校验请求；管理操作占用；创建传输；汇总结果；维护可查询状态 | 不承载配送业务；将逐步握手交给传输实现 |
| `transfer.py` | 实现上传、下载及相关计划操作的协议过程；可包含 `UploadTransfer`、`DownloadTransfer`；处理请求序号、确认、超时和重传 | 复用统一 MAVLink 收发；不独占接收连接、不决策飞行安全 |
| `models.py` | 定义 `MissionItem`、`TransferState`、`MissionStatus`、`MissionProgress` 等数据结构 | 只描述计划与协议状态，不保存配送业务状态，不发送消息 |

`MissionItem` 需要表达序号、指令、坐标系（Coordinate Frame）及指令参数。此前讨论的 `seq / command / frame / params / lat / lon / alt` 是结构示意；最终字段必须明确参数数量、单位、高度基准及支持的任务项范围，不能默认所有任务项都是经纬度航点。

`TransferState` 可使用 `IDLE / UPLOADING / DOWNLOADING / SUCCESS / FAILED` 表达主要流程。清空、设置当前项及其他终态的表示方式待实现时补齐，不与业务状态混用。

### 6.2 `security/`

| 文件 | 职责 | 边界 |
| --- | --- | --- |
| `__init__.py` | 导出 `SecurityManager` 及需要公开的状态类型 | 不产生运行副作用 |
| `manager.py` | 实现生命周期及查询 API；运行监督循环；串联检查、策略和处置；通过 Command 取消普通命令并执行安全动作 | 不直接发送 MAVLink；不重新实现遥测采集 |
| `checks.py` | 读取统一遥测与必要的命令状态，输出 `SafetyEvent`；承载各项检测函数 | 不执行动作、不修改 Command 当前命令 |
| `policy.py` | 根据事件、配置和必要上下文决定告警、保持、返航或降落等处置 | 不收发协议、不自行调用飞行动作 |
| `models.py` | 定义 `SafetyEvent`、安全等级与 `SecurityStatus` 等结构 | 作为数据模型使用，不启动线程、不持有通信流程 |

`SafetyEvent` 可包含事件类型、严重程度、原因和观测值。最终模型应区分事件严重程度、期望动作与实际处置结果，避免把“决定返航”显示成“已成功返航”；枚举及字段尚未冻结。

公共阈值、检查周期和超时配置统一归入 `Server/config.py`。第一版不新增 `security/config.py`。本文不指定电量百分比、检查周期或围栏距离的数值。

## 7. 调用关系与运行方式

### 7.1 业务控制路径

```text
Web / 其他业务入口
        ↓
      业务层
      ├── CommandManager ──────────────────┐
      └── MissionManager → Mission Transfer ┤
                                           ↓
                                    统一 MAVLink 层
                                           ↓
                                          飞控
```

业务层决定何时上传、何时请求执行、何时暂停，以及被安全处置中断后如何结束或恢复业务。Mission 上传完成后不会自行切换飞行模式。

### 7.2 接收与监督路径

```text
飞控 → 统一接收与分发
           ├── 遥测更新 → 统一 Drone 状态 → Security 读取
           ├── 命令响应 → Command 事务处理
           └── Mission 消息 → 传输推进 / 计划进度更新

Security 独立线程
    checks → policy → manager → Command → 统一 MAVLink 层
```

接收与分发路径为各模块提供输入；Mission、Command 与 Security 不各自竞争读取同一个连接。分发回调只做必要的状态更新或事件通知，不在接收路径上阻塞等待命令完成。

Security 读取 `drone.state` 所代表的统一状态，不维护第二套电量、位置或飞行状态。具体字段以集成时的数据模型为准。跨线程读取需要一致的快照或适当同步，并保留更新时间和有效性，避免把过期数据视为实时观测。

应用装配代码负责创建对象、注入依赖以及启动和停止 Security。这里 `security` 表示实例引用，不强制规定它必须挂在 `drone.security` 下。

## 8. 依赖方向与关键设计原则

### 8.1 依赖方向

| 调用方 | 允许使用的能力 |
| --- | --- |
| 业务层 | Command API、Mission API、Security 状态 |
| MissionManager | Mission 模型、传输实现、必要的底层适配能力 |
| Mission Transfer | Mission 模型、统一 MAVLink 能力、公共配置 |
| SecurityManager | checks、policy、Security 模型、统一遥测读取接口、Command API、公共配置 |
| Security checks | 遥测快照、必要的只读命令状态、模型与检查配置 |
| Security policy | 事件、上下文、模型与策略配置 |
| Command | 命令模型、统一 MAVLink 能力、遥测完成判据与公共配置 |
| MAVLink 基础层、公共配置 | 不反向依赖业务层、MissionManager 或 SecurityManager |

事件通过注册回调或其他消息分发机制传递，上层在装配阶段完成连接；运行时消息向上传递不要求下层反向导入上层模块。Command 不依赖 Security；Mission 与 Security 不形成相互导入。

复用检查逻辑应限于无副作用的遥测判据。如果公共判据需要抽取，应放入双方可依赖的下层位置，不让 Command 反向导入 `security/checks.py`。

### 8.2 关键原则

1. **按职责分层。** 业务编排、任务计划管理、命令执行和安全监督各自有唯一主要入口。
2. **统一通信和状态来源。** 共用 MAVLink 收发与 Drone 遥测，避免重复接收和状态分叉。
3. **区分不同层次的成功。** 消息发送、协议确认、飞行动作完成和业务完成分别判断。
4. **显式处理并发。** 同一目标上冲突的计划操作需要互斥或明确拒绝；安全抢占需要命令调度保障。
5. **监督保持可响应。** 安全动作若使用阻塞式 Command，必须控制等待方式，避免长时间停止后续检查；具体机制在实现阶段确定。
6. **处置结果可追踪。** 记录触发原因、选定动作、取消结果、发送结果和执行反馈。重复事件应有去重或抑制机制，防止每个周期重复取消和重发。
7. **本地取消范围明确。** `cmd.cancel()` 不自动终止 Mission 传输，也不表示远端任务停止。安全接管期间业务是否暂停计划修改，需要显式协调。
8. **配置与实现分离。** 阈值和策略参数集中管理，不在检查函数中散布数值。
9. **不承诺链路外控制能力。** Security 依赖服务器运行及可用通信；链路中断时不能将尝试发送的动作报告为成功。飞控失效保护（Failsafe）与独立硬件安全能力另行设计。

## 9. 已确定内容与待细化事项

已确定：Mission 的五个公开接口；Security 的生命周期、状态查询和单次检查入口；两个模块的文件结构；业务层调用 Command 与 Mission；Security 独立监督、读取统一遥测、先取消普通 Command 再通过 Command 执行安全动作；公共配置集中在 `Server/config.py`。

以下内容仍需在实现与联调前细化，本文不将其记为已完成决策：

| 事项 | 需要明确的内容 |
| --- | --- |
| API 结果契约 | 返回类型、异常与错误码、阻塞或异步形式、超时及取消语义 |
| `check_once()` | 是否仅检测；返回单个事件还是集合；与监督线程同时运行时如何同步 |
| Mission 数据模型 | 支持的任务项、坐标系、参数与单位、空计划处理、目标及计划类型范围 |
| 传输状态与兼容性 | 操作互斥、错误恢复、重试上限、状态失效规则、固件支持范围 |
| Command 集成 | `set_current()` 适配；模式与动作映射；取消终态；安全优先级与竞争处理 |
| 安全策略 | 检查项、阈值、动作前提、事件优先级、重复抑制、升级与恢复条件 |
| 运行生命周期 | 线程启动条件、停止等待、动作期间的监督响应及异常退出处理 |
| 硬件与部署 | 实际飞控型号和固件、服务器部署位置、通信通道、传感器与定位能力 |

架构约定来自本次 Mission / Security 设计讨论；外部链接仅用于说明协议语义，不证明项目已实现相应能力。实现验收应覆盖任务传输成功与失败、安全抢占竞争、过期遥测、重复事件及关闭流程，并以实际代码和联调结果为准。
