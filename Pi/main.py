import time
from transport import open_connection

while True:
    fc = None
    server = None
    try:
        fc = open_connection("fc")
        server = open_connection("server")
        if fc is None or server is None:
            raise ValueError("连接失败")
        while True:
            msg = fc.recv_msg()
            if msg is not None:
                server.write(msg.get_msgbuf())
            msg = server.recv_msg()
            if msg is not None:
                fc.write(msg.get_msgbuf())
    except Exception:
        for conn in (fc, server):
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(3)