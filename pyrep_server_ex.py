from socket import *
from script.const import SockType

port = 8081

serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.bind(('', port))
serverSock.listen(1)

connectionSock, addr = serverSock.accept()

# start instruction step
msg = SockType.start_instruction_step.value
connectionSock.send(msg.encode('utf-8'))

# while instruction step
for i in range(10):
    # send path of current group info
    msg = "group_info_" + str(i)
    connectionSock.send(msg.encode('utf-8'))

    # recieve ture or false to check ready
    data = connectionSock.recv().decode('utf-8')

# end instruction step
msg = SockType.end_instruction_step.value
connectionSock.send(msg.encode('utf-8'))
# end assembly
msg = SockType.end_assembly.value
connectionSock.send(msg.encode('utf-8'))

serverSock.close()