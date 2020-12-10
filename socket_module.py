import socket
from enum import Enum

from script.const import SocketType, FreeCADRequestType, \
    PyRepRequestType, InstructionRequestType, BlenderRequestType, DyrosRequestType
from script.socket_utils import *
from script.fileApi import *
import random
import time
from pyprnt import prnt
from easy_tcp_python2_3 import socket_utils as su

class SocketModule():
    def __init__(self, logger, is_instruction, is_visualize, is_dyros):
        self.logger = logger
        self.c_freecad = self.initialize_freecad_client()
        self.c_pyrep = self.initialize_pyrep_client()
        
        self.is_instruction = is_instruction
        self.is_visualize = is_visualize
        self.is_dyros = is_dyros
        
        if self.is_instruction:
            is_connected = False
            is_once = True
            while not is_connected:
                try:
                    self.c_instruction = self.initialize_instruction_client()
                    is_connected = True
                except:
                    if is_once:
                        print("...waiting for parsing")
                        is_once = False
                    time.sleep(1)
        
        if self.is_visualize:
            is_connected = False
            is_once = True
            while not is_connected:
                try:
                    self.c_blender = self.initialize_blender_client()
                    is_connected = True
                except:
                    if is_once:
                        print("...waiting for visualization")
                        is_once = False
                    time.sleep(1)
            
        if self.is_dyros:
            is_connected = False
            is_once = True
            while not is_connected:
                try:
                    # self.c_dyros = self.initialize_dyros_client()
                    self.c_dyros_1 = self.initialize_dyros_client_1()
                    self.c_dyros_2 = self.initialize_dyros_client_2()
                    is_connected = True
                except:
                    if is_once:
                        print("...waiting for dyros server")
                        is_once = False
                    time.sleep(1)
            
            
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

    def initialize_blender_client(self):
        host = SocketType.blender.value["host"]
        port = SocketType.blender.value["port"]
        sock = socket.socket()
        sock.connect((host, port))
        self.logger.info("==> Connected to Blender server on {}:{}".format(host, port))
        
        return sock

    # def initialize_dyros_client(self):
    #     host = SocketType.dyros.value["host"]
    #     port = SocketType.dyros.value["port"]
    #     sock = su.initialize_client(host, port)
    #     self.logger.info("==> Connected to Dyros server on {}:{}".format(host, port))
        
    #     return sock
    def initialize_dyros_client_1(self):
        host = SocketType.dyros_1.value["host"]
        port = SocketType.dyros_1.value["port"]
        sock = su.initialize_client(host, port)
        self.logger.info("==> Connected to Dyros 1 server on {}:{}".format(host, port))
        
        return sock
    def initialize_dyros_client_2(self):
        host = SocketType.dyros_2.value["host"]
        port = SocketType.dyros_2.value["port"]
        sock = su.initialize_client(host, port)
        self.logger.info("==> Connected to Dyros 2 server on {}:{}".format(host, port))
        
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
        # is_possible = recvall_pickle(self.c_freecad)
        response = recvall_pickle(self.c_freecad)
        
        return response

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
    def initialize_part_to_scene(self, part_info, pair_info):
        request = PyRepRequestType.initialize_part_to_scene
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to initialize pyrep scene"
        # send part info and initialize pyrep scene
        request = {
            "part_info": part_info,
            "pair_info": pair_info
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
        return is_success

    def update_part_status(self, part_status):
        request = PyRepRequestType.update_part_status
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to update part status"
        # send part info and initialize pyrep scene
        request = {
            "part_status": part_status,
        }
        sendall_pickle(self.c_pyrep, request)
        is_success = recvall_pickle(self.c_pyrep)
        if is_success:
            self.logger.info("Success to update part status")
        else:
            self.logger.info("Fail to update group to Scene")
        return is_success

    def get_assembly_point(self, group_id, connection_locs, connector_name):
        request = PyRepRequestType.get_assembly_point
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to get assembly point from scene"
        # send part info and initialize pyrep scene
        request = {
            "group_id": group_id,
            "connection_locs": connection_locs,
            "connector_name": connector_name
        }
        sendall_pickle(self.c_pyrep, request)
        assembly_points = recvall_pickle(self.c_pyrep)
        assert assembly_points, "Fail to get assembly point from scene"
        
        return assembly_points
    
    def get_cost_of_available_pair(self, group_id, check_pair):
        request = PyRepRequestType.get_cost_of_available_pair
        self.logger.info("Request {} to PyRep Module".format(request))
        sendall_pickle(self.c_pyrep, request)
        response = recvall_pickle(self.c_pyrep)
        assert response, "Not ready to get cost from scene"
        # send part info and initialize pyrep scene
        request = {
            "group_id": group_id,
            "check_pair": check_pair
        }
        sendall_pickle(self.c_pyrep, request)
        pair_cost = recvall_pickle(self.c_pyrep)
        assert pair_cost, "Fail to get cost from scene"
        
        return pair_cost

    #endregion

    #region instruction module
    def get_connector_quantity(self):
        request = InstructionRequestType.get_connector_quantity
        self.logger.info("Request {} to Instruction Module".format(request))
        sendall_pickle(self.c_instruction, request)
        response = recvall_pickle(self.c_instruction)
        assert response, "Not ready to extract instruction info"
        
        sendall_pickle(self.c_instruction, True)
        connector_quantity = recvall_pickle(self.c_instruction)
        
        self.logger.info("Success to get quantity of connector")
        return connector_quantity

    def get_instruction_info(self, current_step, group_info, connector_info):
        request = InstructionRequestType.get_instruction_info
        self.logger.info("Request {} to Instruction Module".format(request))
        sendall_pickle(self.c_instruction, request)
        response = recvall_pickle(self.c_instruction)
        assert response, "Not ready to get instruction info"
        # send group_info and get instruction info
        for group_id in group_info.keys():
            obj_path = group_info[group_id]["obj_file"]
            with open(obj_path, "r") as f:
                group_info[group_id]["obj_raw"] = f.readlines()
        request = {
            "current_step": current_step,
            "group_info": group_info,
            "connector_info": connector_info,
        }
        sendall_pickle(self.c_instruction, request)
        instruction_info = recvall_pickle(self.c_instruction)
        self.logger.info("Instruction info is")
        prnt(instruction_info)
        
        return instruction_info
    #endregion

    #region blender module
    def start_visualization(self, current_step, group_info, instruction_info, 
                                  group_status, assembly_info, is_end):
        assert self.is_visualize, "No visualize server exist"
        request = BlenderRequestType.start_visualization
        self.logger.info("Request {} to Blender Module".format(request))
        sendall_pickle(self.c_blender, request)
        response = recvall_pickle(self.c_blender)
        assert response, "Not ready to start visualization"
        group_files = {group_id: {} for group_id in group_info.keys()}
        for group_id in group_info.keys():
            obj_root = group_info[group_id]["obj_root"]
            
            obj_files = get_file_list(obj_root)
            for file_path in obj_files:
                with open(file_path, "r") as f:
                    group_files[group_id][file_path] = f.readlines()
        request = {
            "current_step": current_step,
            "group_info": group_info,
            "group_status": group_status,
            "group_files": group_files,
            "instruction_info": instruction_info,
            "assembly_info": assembly_info,
            "is_end": is_end
        }
        sendall_pickle(self.c_blender, request)
        is_start = recvall_pickle(self.c_blender)
        if is_start:
            self.logger.info("visualization start")
    #endregion

    #region dyros module
    def send_final_assembly_sequence(self, assembly_sequence, is_end):
        request = DyrosRequestType.send_final_assembly_sequence
        self.logger.info("Request {} to Dyros Module".format(request))
        if not is_end:
            su.sendall_pickle(self.c_dyros_1, request)
            response = su.recvall_pickle(self.c_dyros_1)
            assert response, "Not ready to dyros"
            
            request = assembly_sequence
            su.sendall_pickle(self.c_dyros_1, request)
            is_success = su.recvall_pickle(self.c_dyros_1)
        else:
            su.sendall_pickle(self.c_dyros_2, request)
            response = su.recvall_pickle(self.c_dyros_2)
            assert response, "Not ready to dyros"
            
            request = assembly_sequence
            su.sendall_pickle(self.c_dyros_2, request)
            is_success = su.recvall_pickle(self.c_dyros_2)
        if is_success:
            self.logger.info("Success to send Final sequence")
        assert is_success, "sdfsfadfasdfsdfsdfsdfsadf"
        return is_success
    #endregion

    def close(self):
        self.c_freecad.close()
        self.c_pyrep.close()
        if self.is_instruction:
            self.c_instruction.close()
        if self.is_visualize:
            self.c_blender.close()
        if self.is_dyros:
            self.c_dyros.close()

if __name__=="__main__":
    s = SocketModule()
