import socket
from enum import Enum

from script.const import SocketType, FreeCADRequestType, PyRepRequestType, InstructionRequestType
from script.socket_utils import *
from script.fileApi import *
import random
import time
from pyprnt import prnt

class SocketModule():
    def __init__(self):
        self.c_freecad = self.initialize_freecad_client()
        self.c_pyrep = self.initialize_pyrep_client()
        self.c_instruction = self.initialize_instruction_client()

    def initialize_freecad_client(self):
        host = SocketType.freecad.value["host"]
        port = SocketType.freecad.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        print("==> Connected to FreeCAD server on {}:{}".format(host, port))
        
        return sock

    def initialize_pyrep_client(self):
        host = SocketType.pyrep.value["host"]
        port = SocketType.pyrep.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        print("==> Connected to PyRep server on {}:{}".format(host, port))
        
        return sock

    def initialize_instruction_client(self):
        host = SocketType.instruction.value["host"]
        port = SocketType.instruction.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        print("==> Connected to Instruction server on {}:{}".format(host, port))
        
        return sock

    #region freecad module
    def initialize_cad_info(self, cad_file_path):
        """
        """
        request = FreeCADRequestType.initialize_cad_info
        print("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to get initialize_cad_info"
        # send cad file path and get part info
        request = cad_file_path
        sendall_pickle(self.c_freecad, request)
        print("...Waiting for part info from FreeCAD Module")
        part_info = recvall_pickle(self.c_freecad)
        print("Get Part info from FreeCAD Module")

        return part_info

    def check_assembly_possibility(self, target_assembly_info):
        request = FreeCADRequestType.check_assembly_possibility
        print("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to check_assembly_possibility"
        # send assembly_info and get true false
        request = target_assembly_info
        sendall_pickle(self.c_freecad, request)
        print("...Waiting for simulate assembly from FreeCAD Module")
        is_possible = recvall_pickle(self.c_freecad)
        print("is possible? {}".format(is_possible))

        return is_possible

    def extract_group_obj(self, group_status, obj_root):
        request = FreeCADRequestType.extract_group_obj
        print("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to extract_group_obj"
        # send assembly_info and get true false
        request = {
            "group_status": group_status,
            "obj_root": obj_root
        }
        sendall_pickle(self.c_freecad, request)
        print("...Waiting for export group obj")
        success_to_export = recvall_pickle(self.c_freecad)
        print("{} to export obj".format(success_to_export))

    #endregion
    
    #region pyrep module
    def initialize_pyrep_scene(self, part_info, group_info):
        """
        """
        request = PyRepRequestType.initialize_scene
        print("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to initialize pyrep scene"
        # send part info and initialize pyrep scene
        request = {
            "part_info": part_info,
            "group_info": group_info
        }
        sendall_pickle(self.c_pyrep, request)
        print("...Waiting for initialize PyRep scene")
        is_success = recvall_pickle(self.c_pyrep)
        if is_success:
            print("Success to initialize Scene")
        else:
            print("Fail to initialize Scene")
    
    #endregion

    #region instruction module
    def get_instruction_info(self, group_info, connector_info):
        request = InstructionRequestType.get_instruction_info
        print("Request {} to Instruction Module".format(request))
        sendall_pickle(self.c_instruction, request)
        response = recvall_pickle(self.c_instruction)
        assert response, "Not ready to get instruction info"
        # send group_info and get instruction info
        request = {
            "group_info": group_info,
            "connector_info": connector_info
        }
        sendall_pickle(self.c_instruction, request)
        print("...Waiting for instruction info")
        instruction_info = recvall_pickle(self.c_instruction)
        print("Instruction info is")
        prnt(instruction_info)
        
        return instruction_info
    #endregion



    def close(self):
        self.c_freecad.close()
        self.c_pyrep.close()
        self.c_instruction.close()

if __name__=="__main__":
    s = SocketModule()
    
    
    #     is_possible = False
    #     try:
    #         is_possible = s.check_assembly_possibility(assembly_info)
    #     except:
    #         print("ERROR")
    #     if is_possible:
    #         instance_info_0["used_assembly_points"].append(point_idx_0)
    #         instance_info_1["used_assembly_points"].append(point_idx_1)
    #         instance_info_0["instance_group_id"] = group_id
    #         instance_info_1["instance_group_id"] = group_id
    #         instance_group_status[group_id] = assembly_info["status"] + [assembly_info["target"]]
    # save_dic_to_yaml(part_instance_info, "./part_instance_info_sequence_3.yaml")
    # save_dic_to_yaml(instance_group_status, "./instance_group_status_sequence_3.yaml")
    
    
