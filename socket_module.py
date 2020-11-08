import socket
from enum import Enum

from script.const import SocketType, FreeCADRequestType
from script.socket_utils import *
from script.fileApi import *
import random as rd
import time
class SocketModule():
    def __init__(self):
        self.s_freecad = self.initialize_freecad_client()
        # self.s_pyrep = self.initialize_pyrep_server()

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

    def initialize_freecad_client(self):
        host = SocketType.freecad.value["host"]
        port = SocketType.freecad.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        print("==> Connected to FreeCAD server on {}:{}".format(host, port))
        
        return sock

    #region freecad module
    def initialize_cad_info(self, cad_file_path):
        """
        """
        request = FreeCADRequestType.initialize_cad_info
        print("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.s_freecad, request)
        response = recvall_pickle(self.s_freecad)
        while not response:
            response = recvall_pickle(self.s_freecad)
        # send cad file path and get part info
        request = cad_file_path
        sendall_pickle(self.s_freecad, request)
        print("...Waiting for part info from FreeCAD Module")
        part_info = recvall_pickle(self.s_freecad)
        time.sleep(1)
        print("Get Part info from FreeCAD Module")
        print(part_info)

        return part_info


    def check_assembly_possibility(self, ):
        pass

    def close(self):
        self.s_freecad.close()
    #endregion

if __name__=="__main__":
    s = SocketModule()
    part_info = s.initialize_cad_info("./cad_file/STEFAN")
    save_dic_to_yaml(part_info, "./assembly/STEFAN/part_info.yaml")