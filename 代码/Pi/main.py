import time
from transport import open_connection
from logger import logger
log = logger("relay")

while True:
    fc = None
    server = None
    try:
        fc = open_connection("fc")
        server = open_connection("server")
        if fc is None or server is None:
            raise ValueError("连接失败")
        log.info("双向转发已启动")
        while True:
            # transport 给连接设了 0.1s 超时。串口内部会吞掉超时返回空，
            # 但 TCP 的 recv 会把 TimeoutError 原样抛出——不在这里接住，
            # 一次超时就穿出去把整条连接拆掉（表现为连上 100ms 就断）。
            try:
                msg = fc.recv_msg()
            except TimeoutError:
                msg = None
            if msg is not None:
                server.write(msg.get_msgbuf())

            try:
                msg = server.recv_msg()
            except TimeoutError:
                msg = None
            if msg is not None:
                fc.write(msg.get_msgbuf())
    except Exception:
        # 别裸吞：这个 except 曾经把 TimeoutError 藏了一下午
        log.exception("转发循环异常")
        for conn in (fc, server):
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(3)
