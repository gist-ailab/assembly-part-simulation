import socket
from enum import Enum

from script.const import SocketType
import random as rd

class SocketModule():
    def __init__(self):
        self.s_freecad = self.initialize_freecad_server()
        self.s_pyrep = self.initialize_pyrep_server()
        

    def initialize_pyrep_server(self):
        host = SocketType.pyrep.value["host"]
        port = SocketType.pyrep.value["port"]
        print("Waiting for PyRep client {}:{}".format(host, port))
        s_pyrep = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_pyrep.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_pyrep.bind((host, port))
        s_pyrep.listen(True)
        pyrep_socket, pyrep_addr = s_pyrep.accept()
        print("Connected by {}:{}".format(host, port))
        return pyrep_socket

    def initialize_freecad_server(self):
        host = SocketType.freecad.value["host"]
        port = SocketType.freecad.value["port"]
        print("Waiting for FreeCAD client {}:{}".format(host, port))
        s_freecad = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_freecad.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_freecad.bind((host, port))
        s_freecad.listen(True)
        freecad_socket, freecad_addr = s_freecad.accept()
        print("Connected by {}:{}".format(host, port))


if __name__=="__main__":
    s = SocketModule()