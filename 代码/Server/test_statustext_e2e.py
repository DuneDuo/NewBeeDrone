# 用真实 MAVLink 包测 StatusText（encode -> pack -> parse_buffer -> update）
import time
import config, os
from pymavlink.dialects.v20.common import MAVLink
from mavlink.models.statustext import StatusText

class DummyDrone:
    def __init__(self, sys_id):
        self.sys_id = sys_id

mav_fc = MAVLink(None, srcSystem=1, srcComponent=1)      # 飞控侧
mav_srv = MAVLink(None, srcSystem=255, srcComponent=190) # 服务器侧

def recv(severity, text, id, chunk_seq):
    """飞控 encode+pack，服务器 parse，返回解析后的 msg。text 传 str，内部按 char[50] 补 null。"""
    raw = text.encode('utf-8')[:50].ljust(50, b'\x00')   # 飞控侧填满 50 字节再发
    msg = mav_fc.statustext_encode(severity=severity, text=raw, id=id, chunk_seq=chunk_seq)
    buf = msg.pack(mav_fc)
    parsed = mav_srv.parse_buffer(buf)
    return parsed[0]

print("========== 关键验证：char[50] 尾部 null 怎么处理 ==========")
m = recv(4, "GPS glitch", 0, 0)
print(f"severity={m.severity}  id={m.id}  chunk_seq={m.chunk_seq}")
print(f"repr(text)={m.text!r}")
print(f"len(text)={len(m.text)}")
print(f"'len<50' 判断结果: {len(m.text) < 50}  （False 说明 null 没剔，判断会失效）")

print()
print("========== 1. 单条短消息 ==========")
st = StatusText(DummyDrone(1))
st.update(recv(4, "GPS glitch", 0, 0))
st.update(recv(3, "EKF error", 1, 0))

print()
print("========== 2. 分块长消息（>50 字，拆 2 块）==========")
long_text = "EKF2 IMU0 tilt alignment complete, yaw offset: -2.3 deg, will use mag for heading recovery"  # 92 字
chunk0 = long_text[:50]
chunk1 = long_text[50:]
print(f"全文 {len(long_text)} 字，chunk0={len(chunk0)} 字, chunk1={len(chunk1)} 字")
st.update(recv(6, chunk0, 42, 0))
st.update(recv(6, chunk1, 42, 1))

print()
print("========== 3. 丢块（orphan chunk，触发 else 分支）==========")
st.update(recv(6, "recovery", 99, 1))

print()
print("========== 4. close 收尾（flush 残留的 50 字整块）==========")
exact50 = "A" * 50
st.update(recv(5, exact50, 7, 0))
print("（此时 buf 里应卡着这条 50 字消息，len 不小于 50 不会立刻 flush）")
st.flush()   # 模拟 close() 的收尾

print()
print("========== 完成，检查 logs/status_text/ 下的 txt ==========")
d = config.status_text_dir
for root, dirs, files in os.walk(d):
    for f in files:
        p = os.path.join(root, f)
        print(f"--- {p} ---")
        print(open(p, encoding='utf-8').read())
