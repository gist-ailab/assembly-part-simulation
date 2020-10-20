from socket import *


port = 8080

clientSock = socket(AF_INET, SOCK_STREAM)
clientSock.connect(('127.0.0.1', port))

data = clientSock.recv(1024)
print(data)