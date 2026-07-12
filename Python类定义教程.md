# Python 类定义教程

> 面向 Server 端开发，用 transport 和 watchdog 做例子。

---

## 1. 类和实例是什么

```python
# 类是模板
class Dog:
    def bark(self):
        print("汪汪")

# 实例是按模板造出来的具体对象
dog1 = Dog()    # 一只狗
dog2 = Dog()    # 又一只狗
dog1.bark()     # 汪汪
```

放到你的项目里：

```python
# DroneConnection 是模板
conn1 = DroneConnection(sock1, addr1, sys_id=1)   # 飞机1的连接
conn2 = DroneConnection(sock2, addr2, sys_id=2)   # 飞机2的连接
# 两架飞机，两个实例，各自独立
```

---

## 2. 类的基本部件

```python
class ClassName:
    """文档字符串：一句话说明这个类干什么"""

    # ---- 类属性：所有实例共享 ----
    DEFAULT_TIMEOUT = 3.0      # 常量，放类级别

    # ---- __init__：初始化实例 ----
    def __init__(self, param1, param2):
        """self 就是新创建的那个实例"""
        self.param1 = param1          # 实例属性，各管各的
        self.param2 = param2          # 从外部传入
        self._private_thing = None    # 下划线开头 = 内部用的，外面别碰

    # ---- 方法：实例能干的事 ----
    def do_something(self):
        """每个方法第一个参数都是 self"""
        return self.param1 + self.param2

    def get_status(self):
        """返回当前状态"""
        return self._private_thing

    # ---- 私有方法：内部用的 ----
    def _internal_helper(self):
        """外面不应该调"""
        pass
```

---

## 3. 实例属性 vs 类属性

```python
class HeartbeatWatchdog:
    """心跳监控"""

    TIMEOUT = 3.0          # 类属性：所有飞机用同一个超时标准
    CHECK_INTERVAL = 1.0   # 类属性：检查频率也一样

    def __init__(self):
        self._last = {}    # 实例属性：{conn_id: timestamp}
                            # 只有一个 watchdog 实例，但 _last 存所有飞机
```

**一句话**：不变的配置放类属性，运行时会变的数据放实例属性。

---

## 4. `self` 是什么

```python
class DroneConnection:
    def __init__(self, sock, sys_id):
        self.sock = sock          # 存到实例身上
        self.sys_id = sys_id
        self._running = False

    def recv_msg(self):
        # 用 self.sock 而不是 sock —— 因为 sock 存在实例身上
        return recv_from(self.sock)

# 调用时不用传 self，Python 自动传
conn = DroneConnection(my_sock, 1)
conn.recv_msg()
#    ↑ 这个 conn 就是 self
# 等价于 DroneConnection.recv_msg(conn)
```

---

## 5. `__init__` vs 普通方法

```python
class Collector:
    def __init__(self, log_dir):
        """创建实例时自动调用，只调一次"""
        self._log_dir = log_dir
        self._files = {}
        self._ready = True

    def update(self, conn_id, msg):
        """每次收到遥测数据时调，调很多次"""
        ...
```

| | `__init__` | 普通方法 |
|---|---|---|
| 什么时候调 | `Collector("logs")` 时自动 | 手动 `coll.update(...)` |
| 调几次 | 1 次 | N 次 |
| 干什么 | 设初始状态 | 干活 |

---

## 6. 私有属性 / 方法

```python
class DroneConnection:
    def __init__(self, sock, sys_id):
        self.sys_id = sys_id     # 公开：外面能读 conn.sys_id
        self._sock = sock        # 私有：外面不该碰 conn._sock
        self._running = False    # 私有：内部状态

    def recv_msg(self):                # 公开方法
        return self._do_recv()

    def _do_recv(self):                # 私有方法：内部实现
        return recv_from(self._sock)
```

Python 的 `_` 是**约定**不是强制，但遵守这个约定别人读你代码知道哪些能碰哪些不能碰。

---

## 7. 完整示例：DroneConnection

```python
"""transport.py — TCP 连接管理"""

import socket
from logger import logger

log = logger("transport")


class DroneConnection:
    """一架无人机与服务器的 TCP 连接"""

    HEARTBEAT_TIMEOUT = 5.0          # 等身份确认的超时

    def __init__(self, sock, addr):
        self.sys_id = None           # 公开，receiver 和 handler 都要读
        self.addr = addr             # 公开，知道从哪连的

        self._sock = sock            # 私有，外面不直接操作 socket
        self._running = False

    def __repr__(self):
        """打印时友好显示"""
        return f"DroneConnection(sys_id={self.sys_id}, addr={self.addr})"

    # ---- 公开方法 ----

    def recv_raw(self):
        """收原始字节，非阻塞"""
        try:
            self._sock.settimeout(0.01)
            return self._sock.recv(4096)
        except socket.timeout:
            return b""

    def send_raw(self, data):
        """发原始字节"""
        return self._sock.send(data)

    def close(self):
        """关闭连接"""
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        log.info(f"连接已关闭: {self}")


def create_server_socket(host="0.0.0.0", port=57600):
    """创建监听的 TCP socket"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    log.info(f"TCP 服务启动: {host}:{port}")
    return sock
```

---

## 8. 完整示例：HeartbeatWatchdog

```python
"""heartbeat_watchdog.py — 心跳监控"""

import time
import threading
from logger import logger

log = logger("watchdog")


class HeartbeatWatchdog:
    """每架飞机的在线状态监控"""

    def __init__(self, timeout=3.0, check_interval=1.0):
        self._timeout = timeout
        self._interval = check_interval
        self._last = {}             # {conn_id: timestamp}
        self._online = {}           # {conn_id: True/False}
        self._lock = threading.Lock()
        self._running = False

    # ---- 公开方法 ----

    def feed(self, conn_id):
        """收到心跳时调用，刷新时间"""
        with self._lock:
            was_offline = not self._online.get(conn_id, False)
            self._last[conn_id] = time.time()
            self._online[conn_id] = True
            if was_offline:
                log.info(f"飞机 {conn_id} 已恢复在线")

    def remove(self, conn_id):
        """连接断开时调用，清理"""
        with self._lock:
            self._last.pop(conn_id, None)
            self._online.pop(conn_id, None)

    def is_online(self, conn_id):
        """查询某飞机是否在线"""
        with self._lock:
            return self._online.get(conn_id, False)

    def start(self):
        """启动后台检查线程"""
        self._running = True
        t = threading.Thread(target=self._check, daemon=True)
        t.start()

    def stop(self):
        """停止检查"""
        self._running = False

    # ---- 私有方法 ----

    def _check(self):
        """后台线程：每秒扫一遍，超时告警"""
        while self._running:
            time.sleep(self._interval)
            now = time.time()
            with self._lock:
                for conn_id, last in list(self._last.items()):
                    if now - last > self._timeout and self._online.get(conn_id):
                        self._online[conn_id] = False
                        log.warning(f"飞机 {conn_id} 失联！{now - last:.1f}s 无心跳")
```

---

## 9. 设计原则速查

| 原则 | 例子 |
|------|------|
| 类名大驼峰 | `DroneConnection` ✅ `drone_connection` ❌ |
| 方法小写下划线 | `recv_msg()` ✅ `RecvMsg()` ❌ |
| 私有加 `_` | `self._sock` `self._running` |
| 常量全大写 | `HEARTBEAT_TIMEOUT = 5.0` |
| `__init__` 只做初始化 | 不启动线程、不建立连接 |
| 一个类一个文件 | `transport.py` 只有 `DroneConnection` |
| 方法短、职责单一 | 一个方法只做一件事 |
| 锁保护共享数据 | `self._lock` 包裹所有 `self._last` 读写 |
