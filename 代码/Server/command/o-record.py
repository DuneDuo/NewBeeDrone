"""命令台账层：Command（一次执行一行）。

纯数据，记录"这一次执行走到哪一步"。和定义层（models/cmd.py 的 CommandSpec）分开：
  - cmd.py        的 CommandSpec 是"这一类命令怎么定义"（静态，一份）
  - 本文件的 Command        是"这一次执行走到哪"（动态，每次一份）

三块内容：
  1. 状态常量   —— 命令状态（pending/sent/executing/done/timeout）
  2. error 常量 —— 本地异常类型（timeout/link_lost）
  3. Command 类 —— 台账行
"""


# ============================================================
# 一、状态 / error 常量
#     都是字符串。为什么不用数字？因为台账要写进 JSON 给人看，
#     字符串一眼懂，数字还得查表。
# ============================================================

# --- 命令状态（台账行的 state 字段，一台状态机） ---
PENDING = "pending"        # 已建好、还没发
SENT = "sent"              # 已发送，等第一个 ack
EXECUTING = "executing"    # 执行中（进度型等终态 ack / 机动型等遥测达成）
DONE = "done"              # 终态：完成
FAIL = "fail"              # 终态：失败（本地超时 / 飞控拒绝 / 链路断都归这里）

# --- error 类型（本地判的异常 + 飞控回的失败码，只写类型） ---
ERROR_TIMEOUT = "timeout"          # 链路活着、重试耗尽仍没 ack
ERROR_LINK_LOST = "link_lost"      # 链路断了
ERROR_DENIED = "denied"            # 飞控回 MAV_RESULT_DENIED
ERROR_UNSUPPORTED = "unsupported"  # 飞控回 MAV_RESULT_UNSUPPORTED
ERROR_FAILED = "failed"            # 飞控回 MAV_RESULT_FAILED


# ============================================================
# 二、Command：台账行，一次执行一行（动态）
# ============================================================

class Command:
    """一次命令执行的台账行。每调用一次 drone.cmd.takeoff(10) 就 new 一个。

    只记"这一次执行"的信息，不抄定义字段：
      name   → 命令名（审计查"哪条" + 查 spec 的 key）
      cmd    → MAV_CMD 号（重发重建消息用）
      params → 实际填的 param1~7（审计查"具体数值" + 重发重建）

    定义字段（completion / idempotent / effect_check / complete_check /
    timeout / max_retry）**不抄进来**——它们在定义表 spec 里，引擎需要时
    按 name 查 spec 拿，避免台账和定义重复存两份。

    不存 msg 对象，只存 cmd + params；发送/重发时用 _encode 临时重建消息。
    """

    def __init__(self, name, cmd, params):
        # --- 只记"这一次执行"的最小信息 ---
        self.name = name                  # 命令名（审计 + 查 spec 的 key）
        self.cmd = cmd                    # MAV_CMD 号（重发重建消息用）
        self.params = params or {}        # 实际填的 param1~7（审计 + 重发重建）

        # --- 运行时才填的"动态"字段（这次执行走到哪了） ---
        self.run_id = None                # manager 分配的自增号（主键）
        self.state = PENDING              # 当前状态（PENDING→SENT→EXECUTING→DONE/FAIL）
        self.result = None                # 飞控回的 MAV_RESULT 终态（0=ACCEPTED 等）
        self.error = None                 # 本地异常：None / timeout / link_lost
        self.retry_count = 0              # 重发了几次
        self.started_at = None            # 创建时间
        self.sent_at = None               # 发送时间（重发会更新）
        self.done_at = None               # 完成时间
        self.detail = None                # 给人看的补充说明
        self.done_event = None            # threading.Event，阻塞等待用
