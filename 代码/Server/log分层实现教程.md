# Log 分层实现教程

> 把日志按层分到不同文件夹：`logs/drone/`（drone + dispatch）、`logs/command/`（command）。
> 只改 `logger.py` 一个文件（加张映射表），调用方一个字不用动。
> 这份是**设计 + 参考**，代码你自己写。

---

## 零、一句话说清楚

现在 `logger.py` 是共享基础设施，所有层的日志都写进**同一个** `mavlink_xxx.log`。分层要做的是：**在 `logger.py` 里加一张"名字 → 子目录"的映射表**，根据 `logger("xxx")` 传的 name 决定写进哪个文件夹。

---

## 一、目标映射

| name | 层 | 写进 |
|---|---|---|
| `drone` | core（连接/收发） | `logs/drone/` |
| `dispatch` | mavlink（消息分发） | `logs/drone/` |
| `command` | command（命令台账） | `logs/command/` |
| `handlers` | mavlink | 不用 log（删掉死代码） |

以后加 mission / 业务层 / 安全层，各加一行。

---

## 二、核心就两个东西

1. **`_LAYER` 字典**：`name → 子目录`。加新层 = 加一行。
2. **`_file_handlers` 字典**：缓存每个子目录的文件 handler，同层共享一个文件。

其余（console 输出、formatter）保持不动。

---

## 三、参考代码（logger.py 整个换成这样）

```python
import config
import os
import logging
from datetime import datetime

_formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

# name → 子目录。没列到的走 "misc"。
# 以后加 mission / 业务层 / 安全层，在这里各加一行。
_LAYER = {
    "drone":    "drone",     # 连接 / 收发（core）
    "dispatch": "drone",     # 消息分发（mavlink）
    "command":  "command",   # 命令台账（command）
}

_file_handlers = {}   # subdir -> FileHandler，同一层共享一个文件

def logger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    if log.handlers:          # 同一个 name 只挂一次 handler
        return log
    log.addHandler(_console_handler)
    sub = _LAYER.get(name, "misc")
    if sub not in _file_handlers:
        os.makedirs(os.path.join(config.log_dir, sub), exist_ok=True)
        fh = logging.FileHandler(
            os.path.join(config.log_dir, sub,
                         datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"))
        fh.setLevel(logging.INFO)
        fh.setFormatter(_formatter)
        _file_handlers[sub] = fh
    log.addHandler(_file_handlers[sub])
    return log
```

---

## 四、关键点逐条理解（别照抄不理解）

- **`_LAYER`**：`"drone"` 和 `"dispatch"` 都指向 `"drone"`，所以它俩写进 `logs/drone/` 同一个文件，靠日志里的 `[name]` 区分是谁打的。
- **`_LAYER.get(name, "misc")`**：没列到的名字进 `logs/misc/`，**不会崩**。这是兜底，防止将来忘加或临时 logger 报错。
- **`if sub not in _file_handlers`**：每个子目录只建一次文件 handler。第一次 `logger("drone")` 建了 `logs/drone/xxx.log` 并缓存；第二次 `logger("dispatch")` 发现 "drone" 已在缓存，直接复用同一个 handler → 共享同一文件。
- **`if log.handlers: return log`**：同一个 name 的 logger 只挂一次 handler，避免重复挂导致一条日志打两遍。
- **文件名去掉了 `mavlink_` 前缀**：层名已经靠目录区分了，文件名直接时间戳。

---

## 五、清理 handlers.py 的死 logger

`handlers.py` 顶部有这两行，但 handlers 从来没调过 `log.xxx`，是死代码。不删的话，import 时会在 `logs/misc/` 建一个空文件：

```python
from logger import logger      # ← 删
log = logger("handlers")       # ← 删
```

---

## 六、改完的效果

运行后自动生成：

```
logs/
  drone/20260830_143000.log     ← drone + dispatch 的日志
  command/20260830_143000.log   ← command 台账
```

---

## 七、待办清单

- [ ] 重写 `logger.py`（加 `_LAYER` 映射 + `_file_handlers` 缓存）
- [ ] 删 `handlers.py` 里两行死 logger
- [ ] 跑一次，确认 `logs/drone/` 和 `logs/command/` 各自生成文件、内容正确

---

## 附：一个没解决的坑（可选）

`config.log_dir` 现在还是相对路径 `"logs"`，只有从 Server 根目录运行才找得到。要根治就在 `config.py` 顶部加：

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent   # = Server/
log_dir = str(BASE_DIR / "logs")
```

（这个和分层是两件事，可一起做也可先放着。）
