import socket
from enum import Enum

from script.const import SocketType, FreeCADRequestType, PyRepRequestType, InstructionRequestType
from script.socket_utils import *
from script.fileApi import *
import random
import time
from pyprnt import prnt

class SocketModule():
    def __init__(self, logger):
        self.logger = logger
        self.c_freecad = self.initialize_freecad_client()
        self.c_pyrep = self.initialize_pyrep_client()
        self.c_instruction = self.initialize_instruction_client()

    def initialize_freecad_client(self):
        host = SocketType.freecad.value["host"]
        port = SocketType.freecad.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        self.logger.info("==> Connected to FreeCAD server on {}:{}".format(host, port))
        
        return sock

    def initialize_pyrep_client(self):
        host = SocketType.pyrep.value["host"]
        port = SocketType.pyrep.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        self.logger.info("==> Connected to PyRep server on {}:{}".format(host, port))
        
        return sock

    def initialize_instruction_client(self):
        host = SocketType.instruction.value["host"]
        port = SocketType.instruction.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        self.logger.info("==> Connected to Instruction server on {}:{}".format(host, port))
        
        return sock

    #region freecad module
    def initialize_cad_info(self, cad_file_path):
        """
        """
        request = FreeCADRequestType.initialize_cad_info
        self.logger.info("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to get initialize_cad_info"
        # send cad file path and get part info
        request = cad_file_path
        sendall_pickle(self.c_freecad, request)
        part_info = recvall_pickle(self.c_freecad)
        self.logger.info("Get Part info from FreeCAD Module")

        return part_info

    def check_assembly_possibility(self, target_assembly_info):
        request = FreeCADRequestType.check_assembly_possibility
        self.logger.info("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to check_assembly_possibility"
        # send assembly_info and get true false
        request = target_assembly_info
        sendall_pickle(self.c_freecad, request)
        is_possible = recvall_pickle(self.c_freecad)
        self.logger.info("is possible? {}".format(is_possible))

        return is_possible

    def extract_group_obj(self, group_status, obj_root):
        request = FreeCADRequestType.extract_group_obj
        self.logger.info("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.c_freecad, request)
        response = recvall_pickle(self.c_freecad)
        assert response, "Not ready to extract_group_obj"
        # send assembly_info and get true false
        request = {
            "group_status": group_status,
            "obj_root": obj_root
        }
        sendall_pickle(self.c_freecad, request)
        success_to_export = recvall_pickle(self.c_freecad)
        if success_to_export:
            self.logger.info("Success to export obj")
        else:
            self.logger.info("Fail to export obj")
    #endregion
    
    #region pyrep module
    def initialize_part_to_scene(self, part_info):
        request = PyRepRequestType.initialize_part_to_scene
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to initialize pyrep scene"
        # send part info and initialize pyrep scene
        request = {
            "part_info": part_info,
        }
        sendall_pickle(self.c_pyrep, request)
        is_success = recvall_pickle(self.c_pyrep)
        if is_success:
            self.logger.info("Success to initialize Scene")
        else:
            self.logger.info("Fail to initialize Scene")
    
    def update_group_to_scene(self, group_info):
        request = PyRepRequestType.update_group_to_scene
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to update group to scene"
        # send part info and initialize pyrep scene
        request = {
            "group_info": group_info,
        }
        sendall_pickle(self.c_pyrep, request)
        is_success = recvall_pickle(self.c_pyrep)
        if is_success:
            self.logger.info("Success to update group to Scene")
        else:
            self.logger.info("Fail to update group to Scene")

    def get_region_id(self, group_id, connection_loc):
        request = PyRepRequestType.get_region_id
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to initialize pyrep scene"
        # send part info and initialize pyrep scene
        request = {
            "group_id": group_id,
            "connection_loc": connection_loc
        }
        sendall_pickle(self.c_pyrep, request)
        region_id = recvall_pickle(self.c_pyrep)
        assert region_id, "Fail to initialize Scene"
    
    #endregion

    #region instruction module
    def get_instruction_info(self, current_step, group_info, connector_info):
        request = InstructionRequestType.get_instruction_info
        self.logger.info("Request {} to Instruction Module".format(request))
        sendall_pickle(self.c_instruction, request)
        response = recvall_pickle(self.c_instruction)
        assert response, "Not ready to get instruction info"
        # send group_info and get instruction info
        request = {
            "current_step": current_step,
            "group_info": group_info,
            "connector_info": connector_info
        }
        sendall_pickle(self.c_instruction, request)
        instruction_info = recvall_pickle(self.c_instruction)
        self.logger.info("Instruction info is")
        prnt(instruction_info)
        
        return instruction_info
    #endregion

    def close(self):
        self.c_freecad.close()
        self.c_pyrep.close()
        self.c_instruction.close()

if __name__=="__main__":
    s = SocketModule()
