import socket
from enum import Enum

from script.const import SocketType, FreeCADRequestType
from script.socket_utils import *
from script.fileApi import *
import random
import time
from sequence_joo import *




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
        print("Get Part info from FreeCAD Module")

        return part_info

    def check_assembly_possibility(self, assembly_info):
        request = FreeCADRequestType.check_assembly_possibility
        print("Request {} to FreeCAD Module".format(request))
        sendall_pickle(self.s_freecad, request)
        response = recvall_pickle(self.s_freecad)
        while not response:
            response = recvall_pickle(self.s_freecad)
        # send assembly_info and get true false
        request = assembly_info
        sendall_pickle(self.s_freecad, request)
        print("...Waiting for simulate assembly from FreeCAD Module")
        is_possible = recvall_pickle(self.s_freecad)
        print("is possible? {}".format(is_possible))

        return is_possible

    def close(self):
        self.s_freecad.close()
    #endregion

if __name__=="__main__":
    s = SocketModule()
    part_info = s.initialize_cad_info("./cad_file/STEFAN")
    save_dic_to_yaml(part_info, "./assembly/STEFAN/part_info.yaml")
    # TODO: create part instance info
    """
    part_instance_quantity = {
        "ikea_stefan_bolt_side": 6,
        "ikea_stefan_bracket": 4,
        "ikea_stefan_pin": 14,
        "pan_head_screw_iso(4ea)": 4,
    }
    part_instance_info = {}
    for part_name in part_info.keys():
        part_instance_info[part_name] = {}
        try:
            quantity = part_instance_quantity[part_name]
        except:
            quantity = 1
        for i in range(quantity):
            part_instance_info[part_name][i] = {
                "used_assembly_points": [],
                "status": {}
            }
    save_dic_to_yaml(part_instance_info, "./part_instance_info.yaml")
    """
    part_instance_info = load_yaml_to_dic("./part_instance_info.yaml")
    assemble_status = {}
    for instance_name in part_instance_info.keys():
        assemble_status[instance_name] = []
    """
    #TODO: get instance, point id from instruction
    1. group to instance
    2. check region
    3. 
    """
    part_names = part_instance_info.keys() # == part_info.keys()
    for instruction_info in sequence_5:
        """
        part_0, part_1 = random.sample(part_names, 2)
        
        instance_id_list_0 = list(part_instance_info[part_0].keys())
        instance_id_list_1 = list(part_instance_info[part_1].keys())
        instance_id_0 = random.choice(instance_id_list_0)
        instance_id_1 = random.choice(instance_id_list_1)

        instance_info_0 = part_instance_info[part_0][instance_id_0]
        instance_info_1 = part_instance_info[part_1][instance_id_1]

        assembly_points_0 = part_info[part_0]["assembly_points"] # dict
        assembly_points_1 = part_info[part_1]["assembly_points"] # dict
        
        point_idx_list_0 = list(assembly_points_0.keys())
        point_idx_list_1 = list(assembly_points_1.keys())
        if not (len(point_idx_list_0) > 0 and len(point_idx_list_1) > 0):
            continue
        point_idx_0 = random.choice(point_idx_list_0)
        point_idx_1 = random.choice(point_idx_list_1)
        if point_idx_0 in instance_info_0["used_assembly_points"] or point_idx_1 in instance_info_1["used_assembly_points"]:
            continue

        status_0 = instance_info_0["status"]
        status_1 = instance_info_1["status"]
        """
        part_0 = instruction_info[0]["part_name"]
        instance_id_0 = instruction_info[0]["instance_id"]
        point_idx_0 = instruction_info[0]["assembly_point"]
        instance_info_0 = part_instance_info[part_0][instance_id_0]
        status_0 = instance_info_0["status"]
        
        part_1 = instruction_info[1]["part_name"]
        instance_id_1 = instruction_info[1]["instance_id"]
        point_idx_1 = instruction_info[1]["assembly_point"]
        instance_info_1 = part_instance_info[part_1][instance_id_1]
        status_1 = instance_info_1["status"] 
        assembly_info = {
            0: {
                "part_name": part_0,  # part info의 key(=part name)
                "instance_id": instance_id_0,
                "assembly_point": point_idx_0,
                "status": status_0
            },
            1: {
                "part_name": part_1,
                "instance_id": instance_id_1,
                "assembly_point": point_idx_1,
                "status": status_1
            }
        }
        try:
            is_possible = s.check_assembly_possibility(assembly_info)
        except:
            print(assembly_info)
        if is_possible:
            instance_info_0["used_assembly_points"].append(point_idx_0)
            instance_info_1["used_assembly_points"].append(point_idx_1)
            instance_info_0["status"][point_idx_0] = {
                "part_name": part_1,
                "instance_id": instance_id_1,
                "assembly_point": point_idx_1,
            }
            instance_info_1["status"][point_idx_1] = {
                "part_name": part_0,
                "instance_id": instance_id_0,
                "assembly_point": point_idx_0,
            }
    save_dic_to_yaml(part_instance_info, "./instance_info_sequence_5.yaml")
    
    
