import socket
from enum import Enum

from script.const import SocketType
import random as rd

class FreeCAD(object):
    def __init__(self):
        pass
    

class PyrepClient(object):
    def __init__(self):
        try:
            socket_type = SocketType.pyrep.value
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((socket_type["host"], socket_type["port"]))
        except:
            print("pyrep client error")

    def request_assembly_region(self, group_info, target):
        print(group_info)
        print(target)
        return rd.randint(0, 2)
    
    def close(self):
        self.client_socket.close()


if __name__ == "__main__":
    pyrep_client = PyrepClient()