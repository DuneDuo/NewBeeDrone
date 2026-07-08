import socket
client = socket.socket()
client.settimeout(3)
client.connect(('8.152.207.82', 5000))
client.send(b'Hello')
data=client.recv(1024)
text = data.decode('UTF-8')
print(text)
client.close
