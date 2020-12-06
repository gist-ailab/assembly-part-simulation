import enum
from operator import add, pos

from script.const import CONNECTOR_PARTS, PartType, AssemblyType
from script.fileApi import *
from enum import Enum
from socket_module import SocketModule

import copy
from itertools import combinations, product
import random

import numpy as np

penet_condition = {
    "ikea_stefan_side_left":{
        0: 10,
        3: 11,
        4: 12,
        10: 0,
        11: 3,
        12: 4
    },
    "ikea_stefan_side_right":{
        0: 10,
        3: 11,
        4: 12,
        10: 0,
        11: 3,
        12: 4
    },
    "ikea_stefan_bracket":{
        1: 2,
        2: 1
    }
}

class AssemblyManager(object):

    def __init__(self, logger, furniture_name, is_instruction, is_visualize, is_dyros, start_step,
                    cad_root="./cad_file", instruction_root="./instruction"):
        self.logger = logger
        self.furniture_name = furniture_name

        # input path
        self.cad_root = cad_root
        self.cad_path = join(self.cad_root, self.furniture_name)
        self.instruction_root = instruction_root
        self.instruction_path = join(self.instruction_root, self.furniture_name)
        
        self.is_instruction = is_instruction
        self.is_visualize = is_visualize
        self.is_dyros = is_dyros
        self.is_end = False

        self.socket_module = SocketModule(self.logger, is_instruction, 
                                                       is_visualize,
                                                       is_dyros)
        

        # 조립 폴더 생성
        self.assembly_root = "./assembly"
        self.logger.info("Start assembly from step{}".format(start_step))
        if start_step == 1:
            check_and_reset_dir(self.assembly_root)
        else:
            check_and_create_dir(self.assembly_root)        
            
        self.assembly_path = join("./assembly", self.furniture_name)
        check_and_create_dir(self.assembly_path)
        
        # Group(*.obj) 폴더 생성
        self.group_obj_path = join(self.assembly_path, "group_obj")
        check_and_create_dir(self.group_obj_path)
        # Group info 폴더 생성 => intruction 정보 분석에 사용
        self.group_info_root = join(self.assembly_path, "group_info")
        check_and_create_dir(self.group_info_root)
        
        self.result_path = join(self.assembly_path, "result")
        check_and_create_dir(self.result_path)
        self.SNU_result_path = join(self.assembly_path, "SNU_result")
        check_and_create_dir(self.SNU_result_path)
        self.Blender_result_path = join(self.assembly_path, "Blender_result")
        check_and_create_dir(self.Blender_result_path)

        
        # 내부에서 사용하는 데이터(저장은 선택)
        self.part_info_path = join(self.assembly_path, "part_info.yaml")
        self.connector_info_path = join(self.assembly_path, "connector_info.yaml")
        self.assembly_pair_path = join(self.assembly_path, "assembly_pair.yaml")
        self.refined_pair_path = "./assembly_pair_refined.yaml"

        self.part_info = None
        self.assemlby_pair = None
        self.furniture_parts = []
        self.connector_parts = CONNECTOR_PARTS
        self.assembly_info = None
        self.connector_info = None

        # 매 스탭 마다 바뀌는 정보
        self.group_info = None
        self.current_step = start_step - 1
        self.instruction_info = None
        self.instruction_assembly_info = None
        self.sorted_assembly_info = None
        self.is_retry = False
        self.new_group_id = None

        # 조립 마다 바뀌는 정보
        if self.current_step == 0:
            self.part_instance_status = {}
            self.group_status = {}
        else:
            self.group_status = load_yaml_to_dic(join(self.result_path,\
                "group_status_{}.yaml".format(self.current_step)))
            self.part_instance_status = load_yaml_to_dic(join(self.result_path, \
                 "part_instance_status_{}.yaml".format(self.current_step)))
        self.second_solution = {
            "group_status": {},
            "part_instance_status": {},
            "target_sequence": []
        }
        self.used_instance_set = []
        
    def initialize_CAD_info(self):
        self.logger.info("...Waiting for cad info from FreeCAD Module")
        self.part_info = self.socket_module.initialize_cad_info(self.cad_path)
        save_dic_to_yaml(self.part_info, self.part_info_path)
        # self.part_info = load_yaml_to_dic(self.part_info_path)
        self._initialize_assembly_pair()
        save_dic_to_yaml(self.assembly_pair, self.assembly_pair_path)
        # self.assembly_pair = load_yaml_to_dic(self.refined_pair_path)

        self._initialize_furniture_parts()
        self._initialize_connector_parts()
        self._initialize_part_instance_status()
        self._initialize_group_status()

    def _initialize_assembly_pair(self):
        """part info 를 바탕으로 가능한 모든 assembly pairs 를 출력
        - radius_group => all possible groups
        # radius info
            00 2.499999999999989 # pin:1
            01 2.499999999999995 # pin:0
            02 2.5 # long:1,4 middle:2,5 short:1,4
            03 2.7499999999999747 # left:3,4, right:3,4
            04 2.750000000000001 # left:0 right:0
            05 3.0 # brcket:0
            06 3.000000000000001 # long:6,7 short:6,7
            07 3.5 # short:0,2,3,5
            08 4.0 #(8~10) # long,middle,left,right wiht pin
            09 4.000000000000003  
            10 4.0000000000000036
            11 5.65 # bolt:0
            12 6.0 # pan_head_screw_iso(4ea):0
            13 6.1 # bottom
            14 6.2 # bracket(to bottom)
            15 7.9 # left, right(to long short mid)
            16 8.0 # bracket:1
        # offset heuristic rule(based on assemble direction == hole direction)
        - pin assembly offset = -15
        - flat offset = 30
            # offset based on parent edge direction
            if parent_edge dir == assemble dir
                offset = offset
            else:
                offset *= -1
        # additional constraint for bottom and bracket
        1. bracket + long(short) : planesParallel contraint, Face8, Face12, aligned
        2. bottom
            + short: (9, 12, aligned, 0), (4, 14, aligned, -9), (5, 36, aligned, 0)

        """
        # assert False, "Not use this function! load refined file instead"
        radius_group = {
            "pin": [0, 1, 7, 8, 9, 10],
            "bracket": [5, 6],
            "side_penet": [2, 15], 
            "flat": [3, 4, 11],
            "pan": [12, 16],
            "bottom": [13, 14]
        }
        bracket_additional = {
            "type": "parallel",
            "direction": "aligned",
            "face_pair": [8, 12]
        }
        def get_group(radius):
            idx = unique_radius.index(radius)
            for group in radius_group.keys():
                if idx in radius_group[group]:
                    return group
                
        assembly_pairs = {}
        
        unique_radius = []
        for part in self.part_info.keys():
            points = self.part_info[part]["assembly_points"] # type(points) == dict
            for point_idx in points.keys():
                radius = points[point_idx]["radius"]
                if radius in unique_radius:
                    pass
                else:
                    unique_radius.append(radius)
        unique_radius.sort()
        for idx, r in enumerate(unique_radius):
            print(idx, r)
        for part_name_1 in self.part_info.keys():
            assembly_pairs[part_name_1] = {}
            info1 = self.part_info[part_name_1]
            assembly_points_1 = info1["assembly_points"]
            for point_idx_1 in assembly_points_1.keys():
                assembly_pairs[part_name_1][point_idx_1] = []
                point_1 = assembly_points_1[point_idx_1]
                for part_name_2 in self.part_info.keys():
                    if part_name_1 == part_name_2:
                        continue
                    info2 = self.part_info[part_name_2]
                    assembly_points_2 = info2["assembly_points"]
                    for point_idx_2 in assembly_points_2.keys():
                        point_2 = assembly_points_2[point_idx_2]
                        if point_1["type"] == point_2["type"]:
                            continue
                        if get_group(point_1["radius"]) == get_group(point_2["radius"]):
                            # direction condtion
                            edge_dir_1 = point_1["edge_index"][1]
                            edge_dir_2 = point_2["edge_index"][1]
                            direction = "aligned" if edge_dir_1==edge_dir_2 else "opposed"
                            
                            # offset rule
                            offset = 0
                            if get_group(point_1["radius"]) == "pin":
                                offset = -15
                                if part_name_1 =="ikea_stefan_pin":
                                    offset *= -1
                            if get_group(point_1["radius"]) == "side_penet":
                                offset = -30
                                if "side" in part_name_2:
                                    offset *= -1
                            if get_group(point_1["radius"]) == "bottom":
                                offset = 1
                                if part_name_1 =="ikea_stefan_bracket":
                                    offset *= -1
                            if edge_dir_1 == "opposed":
                                offset *= -1
                            
                            # additional option
                            additional_option = None
                            if get_group(point_1["radius"]) == "bracket":
                                if part_name_1 =="ikea_stefan_bracket":
                                    additional_option = copy.deepcopy(bracket_additional)
                                else:
                                    additional_option = copy.deepcopy(bracket_additional)
                                    additional_option["face_pair"].reverse()
                            penet = None
                            if get_group(point_1["radius"]) == "side_penet":
                                penet = "ikea_stefan_bolt_side"
                            if get_group(point_1["radius"]) == "bottom":
                                penet = "pan_head_screw_iso(4ea)"
                            target = {
                                "part_name": part_name_2,
                                "assembly_point": point_idx_2,
                                "direction": direction,
                                "offset": offset,
                                "additional": additional_option,
                                "penet": penet
                            }
                            assembly_pairs[part_name_1][point_idx_1].append(target)
        
        self.assembly_pair =  assembly_pairs
    def _initialize_furniture_parts(self):
        for part_name in self.part_info.keys():
            if self.part_info[part_name]["type"] == PartType.furniture.value:
                self.furniture_parts.append(part_name)
            elif self.part_info[part_name]["type"] == PartType.connector.value:
                pass
            else:
                self.logger.error("type is not matching!")
                exit()
    def _initialize_connector_parts(self):
        assert self.connector_parts
        connector_quantity = self._get_connector_quantity()
        connector_info = {}
        for connector_id in connector_quantity.keys():
            connector_name = self.connector_parts[connector_id]
            connector_info[connector_name] = {
                "quantity": connector_quantity[connector_id]
            }
        self.connector_info = connector_info
        save_dic_to_yaml(self.connector_info, self.connector_info_path)
    def _initialize_part_instance_status(self):
        self.connector_instance_quantity = {}
        part_instance_status = {}
        for part_name in self.part_info.keys():
            part_instance_status[part_name] = {}
            available_assembly = {}
            for connector_name in self.connector_parts:
                available_assembly[connector_name] = 0
            for point_id in self.assembly_pair[part_name].keys():
                available_pairs = self.assembly_pair[part_name][point_id]
                unique_pair = set()
                for pair_info in available_pairs:
                    pair_name = pair_info["part_name"]
                    unique_pair.add(pair_name)
                for pair_name in unique_pair:
                    if pair_name in self.connector_parts:
                        available_assembly[pair_name] += 1
            try:
                quantity = self.connector_info[part_name]["quantity"]
            except:
                quantity = 1
            for i in range(quantity):
                part_instance_status[part_name][i] = {
                    "used_assembly_points": {},
                    "group_id": None,
                    "available_assembly": copy.deepcopy(available_assembly)
                }

        self.part_instance_status = part_instance_status
    def _get_connector_quantity(self):
        if self.is_instruction:
            return self.socket_module.get_connector_quantity()
        else:
            return load_yaml_to_dic("./instruction_ex/connector_quantity.yaml")
    def _initialize_group_status(self):
        # furniture part 를 베이스로 하여 그룹을 생성
        for group_id, part_name in enumerate(self.furniture_parts):
            group_status = {
                "composed_part": [{
                    "part_name": part_name,
                    "instance_id": 0
                }],
                "status": {
                    "document": None,
                    "object_info": {},
                    "assembly": [],
                },
                "composed_group": [group_id],
                "is_exist": True,
                "available_assembly": self.part_instance_status[part_name][0]["available_assembly"]
            }
            self.part_instance_status[part_name][0]["group_id"] = group_id
            self.group_status[group_id] = group_status
    
    def step(self):
        # update by assembled state
        self._update_group_info()
        self._update_group_to_scene()
        self._update_part_status()
        self.second_solution = {
            "group_status": {},
            "part_instance_status": {},
            "target_sequence": []
        }
        save_dic_to_yaml(copy.deepcopy(self.assembly_info), join(self.result_path, "assembly_info_{}.yaml".format(self.current_step)))
        save_dic_to_yaml(self.part_instance_status, join(self.result_path, "part_instance_status_{}.yaml".format(self.current_step)))
        save_dic_to_yaml(self.group_status, join(self.result_path, "group_status_{}.yaml".format(self.current_step)))
        save_dic_to_yaml(self.group_info, join(self.result_path, "group_info_{}.yaml".format(self.current_step)))
    
    def _update_group_info(self):
        # update group info using group status
        group_info = {}
        for group_id in self.group_status.keys():
            obj_root = join(self.group_obj_path, "group_{}".format(group_id))
            check_and_create_dir(obj_root)
            group_status = self.group_status[group_id]
            composed_group = group_status["composed_group"]
            is_exist = group_status["is_exist"]
            self.logger.info("...Waiting for extract group object group id: {}".format(group_id))
            self.socket_module.extract_group_obj(group_status, obj_root)
            available_assembly = group_status["available_assembly"]
            group_info[group_id] = {
                "obj_file": join(obj_root, "base.obj"),
                "obj_root": obj_root,
                "composed_group": composed_group,
                "is_exist": is_exist,
                "available_assembly": available_assembly
            }
        self.group_info = group_info
        self.group_info_path = join(self.group_info_root, "group_info_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_info, self.group_info_path)
    def _update_group_to_scene(self):
        assert self.socket_module.update_group_to_scene(self.group_info), "update group to scene error"
    def _update_part_status(self):
        assert self.socket_module.update_part_status(self.part_instance_status), "update part status error"
    
    def get_instruction_info(self):
        self.current_step += 1
        # update instruction info
        self._get_instruction_info()
        save_dic_to_yaml(self.instruction_info, join(self.result_path, "instruction_info_{}.yaml".format(self.current_step)))
    def _get_instruction_info(self):
        self.logger.info("... wating for instruction of [step {}]".format(self.current_step))
    
        if self.is_instruction:
            self.instruction_info = self.socket_module.get_instruction_info(self.current_step,
                                                                            self.group_info, 
                                                                            self.connector_info)
        else:
            yaml_path = "./instruction_ex/instruction_info_{}.yaml".format(self.current_step)
            self.instruction_info = load_yaml_to_dic(yaml_path)
        
        if self.instruction_info:
            self.logger.info("Get instruction of [step {}] information !".format(self.current_step))
            self.is_end = False
        else:
            self.logger.info("Instruction end!")
            self.is_end = True

    def initialize_part_to_scene(self):
        self.logger.info("...Waiting for initialize PyRep scene")
        self.socket_module.initialize_part_to_scene(self.part_info, self.assembly_pair)
        
    def compile_instruction_assembly_info(self):
        assert self.instruction_info
        
        """initialize compiled assembly info"""
        self.instruction_assembly_info = {
            "group_part_instance": {}, # all part instances in current stage
            "connector_instance": [], # may be added connector instance in current stage
            "connection_solutions": [], # list of compiled connection
            "checker": {} # used to check is assembly satisfy instruction info
        }
        
        """extract instruction info"""
        instruction_sequnce_id = self.instruction_info["sequence_id"] # int
        if self.current_step == instruction_sequnce_id:
            pass
        else:
            self.current_step = instruction_sequnce_id
        
        instruction_group_info = self.instruction_info["Group"] # list
        instruction_connector_info = self.instruction_info["Connector"] # list
        instruction_connection_info = self.instruction_info['connection'] # list
        
        """instruction checker"""
        instruction_checker = {
            "Group": {}, # check each group is used?
            "Connector": {}, # check each connector is used?
            "connection": {}, # check each connection is used?
        }

        """compile instruction group info
        - extract all composed part
        - update checker
        """
        group_part_instances = []
        for group_info in instruction_group_info:
            group_id = group_info["group_id"]
            
            instruction_checker["Group"].setdefault(group_id, False)
            
            current_group_status = self.group_status[group_id]
            current_used_parts = current_group_status["composed_part"]
            for used_part in current_used_parts:
                part_name = used_part["part_name"]
                instance_id = used_part["instance_id"]
                used_part_info = {
                    "part_name": part_name,
                    "instance_id": instance_id,
                }
                group_part_instances.append(used_part_info)
        
        """compile instruction connector info
        - update checker
        """
        for connector_info in instruction_connector_info:
            connector_id = connector_info["connector_id"]
            connector_name = connector_info["part_name"]
            assert connector_id == self.connector_parts.index(connector_name)
            
            connector_num = connector_info["number_of_connector"]
            if connector_num == None:
                count = 0
                connector_status =  self.part_instance_status[connector_name]
                for con_ins in connector_status.keys():
                    if connector_status[con_ins]["group_id"] == None:
                        count += 1
                
                connector_num = count
            instruction_checker["Connector"][connector_name] = connector_num

        """compile instruction connection info
        - define each connection's assembly type
        """
        connection_list = []
        for connection_info in instruction_connection_info:
            connection = self._compile_connection_info(connection_info)
            connection_list.append(connection)
        total_num = 0
        for connector_name in instruction_checker["Connector"].keys():
            total_num += instruction_checker["Connector"][connector_name]
        if len(connection_list) < total_num and len(connection_list) == 1:
            connection_list *= total_num

        """compile connection location to region and points
        - cluster each connection point with same group
        - search best matching region for connection loc
        - search all matching for connection loc => assembly point, cost
        """
        # cluster
        group_2_connection_point = {group_id: [] for group_id in instruction_checker["Group"].keys()}
        for connection_idx, connection in enumerate(connection_list):
            group_component_list = connection["component"]["group"]
            connector_id = connection["component"]["connector"]

            for component_idx, group_component in enumerate(group_component_list):
                group_id = group_component["id"]
                connection_location = group_component["connection_loc"]
                if connection_location == None:
                    continue
                group_2_connection_point[group_id].append(
                    {
                        "connector_id": connector_id,
                        "connection_idx": connection_idx,
                        "component_idx": component_idx,
                        "connection_location": connection_location
                    })

        # search matching for each connection location to region(PyRep Module)
        connection_solutions = {
            0: connection_list
        }

        for group_id in group_2_connection_point.keys():
            group_connection_list = group_2_connection_point[group_id]
            if len(group_connection_list) == 0:
                continue
            group_connection_locs = []
            connector_id = set()
            
            for group_connection in group_connection_list:
                connector_id.add(group_connection["connector_id"])
                connection_loc = group_connection["connection_location"]
                group_connection_locs.append(connection_loc)
            assert len(connector_id) == 1, "Not Implemented for multi connector"
            connector_id = list(connector_id)[0]
            connector_name = self.connector_parts[connector_id]

            
            compiled_location_solutions = self._compile_connection_location(group_id=group_id,
                                                                   connection_locs=group_connection_locs,
                                                                   connector_name=connector_name)
        

            for sol_idx, compiled_locations in enumerate(compiled_location_solutions):
                connection_solutions.setdefault(sol_idx, copy.deepcopy(connection_list))
                target_connection_list = connection_solutions[sol_idx]
                
                for loc_idx, group_connection in enumerate(group_connection_list):
                    con_idx = group_connection["connection_idx"]
                    com_idx = group_connection["component_idx"]

                    compiled_loc = compiled_locations[loc_idx]
                    part_name = compiled_loc["part_name"]
                    instance_id = compiled_loc["instance_id"]
                    point_cost = compiled_loc["point_cost"]

                    part_instance = {
                        "part_name": part_name,
                        "instance_id": instance_id,
                    }
                    part_id = group_part_instances.index(part_instance)

                    target_connection = target_connection_list[con_idx]
                    target_connection["component"]["group"][com_idx]["connection_loc"] = {
                        "part_id": part_id,
                        "point_cost": copy.deepcopy(point_cost)
                    }
                is_possible = True
                for target_connection in target_connection_list:
                    group_info_list = target_connection["component"]["group"]
                    for group_info in group_info_list:
                        try:
                            _ = group_info["connection_loc"]["part_id"]
                        except:
                            connection_solutions.pop(sol_idx)
                            is_possible = False
                            break
                    if not is_possible:
                        break

        self.instruction_assembly_info["group_part_instance"] = group_part_instances
        self.instruction_assembly_info["connection_solutions"] = connection_solutions

        instruction_checker["connection"] = {connection_idx: False \
            for connection_idx in range(len(connection_list))}
        self.instruction_assembly_info["checker"] = instruction_checker

        instruction_assembly_info = copy.deepcopy(self.instruction_assembly_info)
        for connection_info_list in instruction_assembly_info["connection_solutions"].values():
            for connection_info in connection_info_list:
                connection_info["assembly_type"] = copy.deepcopy(connection_info["assembly_type"].name)
        
        save_dic_to_yaml(instruction_assembly_info, join(self.result_path, \
            "instruction_assembly_info_{}.yaml".format(self.current_step)))
        
        self.logger.info("Success to extrct assembly info")

    @staticmethod
    def _compile_connection_info(connection_info):
        """connection = {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group": [
                    {
                        "id": 1,
                        "connection_loc": connection location(position or None)
                    }
                    },
                ],
                "connector": 1,
            }
        }"""
        connection = {}
        connection.setdefault("assembly_type", None)
        connection.setdefault("component", {})
        component_info = connection["component"]
        component_info.setdefault("group", [])
        component_info.setdefault("connector", None)
        
        assembly_type = {}
        components = connection_info["components"]
        for component in components:
            order = component["order"]
            component_type = component["type"] # connector / group
            assembly_type[order] = component_type

            component_id = int(component["id"]) # connector_id / group_id
            connection_loc = component["loc"]
            if component_type == "connector":
                component_info["connector"] = component_id
            elif component_type == "group":
                connection_group_info = {
                    "id": component_id,
                    "connection_loc": connection_loc
                }
                component_info["group"].append(connection_group_info)

            else:
                assert False                
        
        connection["assembly_type"] = AssemblyType.find_type(assembly_type)
        
        return connection
    def _compile_connection_location(self, group_id, connection_locs, connector_name):
        """get assembly point from location of group
        Args:
            group_id ([type]): [description]
            connection_locs ([type]): [description]

        Returns:
            list of compiled_info
            compiled_info = {
                loc_idx: assembly_point
            }
            assembly_point = { # == location info
                part_name: part_name(str)
                instance_id: instance_id(int)
                point_cost: {
                    point_id: cost(float)
                }
            }
        """
        compiled_locations = self.socket_module.get_assembly_point(group_id, connection_locs, connector_name)
        
        return compiled_locations

    def search_assembly_sequence(self):
        self.assembly_info = {}
        self.assembly_info["part"] = self.instruction_assembly_info["group_part_instance"]
        self.assembly_info["assembly"] = []
        self.assembly_info["assembly_sequence"] = []
        self.assembly_info["target_sequence"] = []
        # assembly_sequence = self.assembly_info["assembly_sequence"]
        """assembly_sequence
        list of sequence info
        sequence_info = {
            "sequence": list of pair idx
            "cost": cost of sequence
        }
        """ 
        connection_solutions = self.instruction_assembly_info["connection_solutions"]
        whole_assembly_sequence_info_list = []
        for connection_assembly_list in connection_solutions.values():
            assembly_sequence_info_list = [{
                "sequence": [],
                "cost": 0
            }]
            unique_cost = set()
            self.instruction_assembly_info["connector_instance"] = []
            for connection_assembly in connection_assembly_list:
                target_sequence_info_list, target_pair_list = self._extract_sequence_from_connection_assembly(connection_assembly)
                
                previous_pair_list = self.assembly_info["assembly"]
                target_pair_2_pair_idx = {pair_idx: None for pair_idx in range(len(target_pair_list))}
                for target_pair_idx, target_pair in enumerate(target_pair_list):
                    if target_pair in previous_pair_list:
                        pair_idx = previous_pair_list.index(target_pair)
                    else:
                        previous_pair_list += [target_pair]
                        pair_idx = previous_pair_list.index(target_pair)
                    target_pair_2_pair_idx[target_pair_idx] = pair_idx
                
                new_assembly_sequence_info_list = []
                for assembly_sequence_info in assembly_sequence_info_list:
                    for target_sequence_info in target_sequence_info_list: 
                        current_sequence_info = copy.deepcopy(assembly_sequence_info)
                        current_sequence = current_sequence_info["sequence"]
                        current_cost = current_sequence_info["cost"]
                
                        target_sequence = target_sequence_info["sequence"]
                        target_cost = target_sequence_info["cost"]
                    
                        for target_pair_idx in target_sequence:
                            pair_idx = target_pair_2_pair_idx[target_pair_idx]
                            current_sequence.append(pair_idx)

                        is_possible = self._check_available_sequence(previous_pair_list, current_sequence)
                        if not is_possible:
                            continue
                        current_cost += target_cost
                        if current_cost in unique_cost and current_cost > 0:
                            continue
                        unique_cost.add(current_cost)
                        sequence_info = {
                            "sequence": copy.deepcopy(current_sequence),
                            "cost": current_cost
                        }
                        new_assembly_sequence_info_list.append(sequence_info)
                
                if len(new_assembly_sequence_info_list) > 0:
                    assembly_sequence_info_list = copy.deepcopy(new_assembly_sequence_info_list)
                else:
                    continue
            whole_assembly_sequence_info_list += assembly_sequence_info_list
        temp_dict = {}
        for idx, v in enumerate(whole_assembly_sequence_info_list):
            temp_dict[idx] = v
        self.assembly_info["assembly_sequence"] = temp_dict

        temp_dict = {}
        for idx, v in enumerate(self.assembly_info["part"]):
            temp_dict[idx] = v
        self.assembly_info["part"] = temp_dict

        temp_dict = {}
        for idx, v in enumerate(self.assembly_info["assembly"]):
            temp_dict[idx] = copy.deepcopy(v)
        self.assembly_info["assembly"] = temp_dict

        save_dic_to_yaml(self.assembly_info, "test.yaml")

    def _extract_sequence_from_connection_assembly(self, connection_assembly):
        """connection_assembly = {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group": [
                    {
                        "id": 1,
                        "connection_loc":{
                            "part_id":
                            "point_cost": 0,
                        },
                    },
                    ...
                ],
                "connector": 1,
            }
        }"""
        used_assembly_instance = self.assembly_info["part"]
        assembly_component = connection_assembly["component"]
        assembly_type = connection_assembly["assembly_type"]
        
        #region find unused connector instance
        connctor_id = assembly_component["connector"]
        connector_name = self.connector_parts[connctor_id]

        used_connector_instance = self.instruction_assembly_info["connector_instance"]
        count = 0
        target_connector_instance = None
        connector_instance_info = self.part_instance_status[connector_name]
        for instance_idx in connector_instance_info.keys():
            connector_instance = {
                "part_name": connector_name,
                "instance_id": instance_idx
            }
            is_in_group = not (connector_instance_info[instance_idx]["group_id"] == None)
            if is_in_group or (connector_instance in used_connector_instance):
                continue
            target_connector_instance = connector_instance
            if not connector_instance in used_assembly_instance:
                used_assembly_instance.append(target_connector_instance)
            used_connector_instance.append(connector_instance)
            break
        #endregion
        assert target_connector_instance, "No available {} instance".format(connector_name)

        group_info_list = assembly_component["group"] # list of used_group info
        assembly_sequence_info_list = []

        if len(group_info_list) == 1:
            """group + connector
            """
            group_info = group_info_list[0]
            possible_sequences, available_pair = self._extract_possible_sequence(group_info=group_info,
                                                                                 connector_instance=target_connector_instance)
            
            for sequence in possible_sequences:
                sequence_info = {
                    "sequence": list(sequence),
                    "cost": 0
                }
                assembly_sequence_info_list.append(sequence_info)

        elif len(group_info_list) == 2 and assembly_type == AssemblyType.group_connector_group:
            """group + connector + group
            - any group can assemble with connector

            """
            #region group + connector
            group_info = group_info_list[0]
            
            possible_sequences, available_pair_0 = self._extract_possible_sequence(group_info=group_info,
                                                                                   connector_instance=target_connector_instance)
            
            possible_sequences = self._get_available_sequence(available_pair_0, assembly_num=1)

            assembly_info = group_info["connection_loc"]
            assert assembly_info, "No connection loc in group-connector-group"
            part_id = assembly_info["part_id"]
            point_cost = assembly_info["point_cost"]

            for sequence in possible_sequences:
                cost = 0
                for pair_idx in sequence:
                    target_pair = available_pair_0[pair_idx]["target_pair"]
                    if target_pair[0]["part_id"] == part_id:
                        point_id = target_pair[0]["assembly_point"]
                        cost += point_cost[point_id]
                    else:
                        point_id = target_pair[1]["assembly_point"]
                        cost += point_cost[point_id]
                sequence_info = {
                    "sequence": list(sequence),
                    "cost": cost
                }
                assembly_sequence_info_list.append(sequence_info)
            #endregion
            
            #region assemble group + group(connector)
            group_info = group_info_list[1]
            
            possible_sequences, available_pair_1 = self._extract_possible_sequence(group_info=group_info,
                                                                                   connector_instance=target_connector_instance)
            assembly_info = group_info["connection_loc"]
            assert assembly_info, "No connection loc in group-connector-group"
            part_id = assembly_info["part_id"]
            point_cost = assembly_info["point_cost"]
            
            #endregion
            #region combine sequence
            available_pair = available_pair_0 + available_pair_1
            added_pair_idx = len(available_pair_0)
            point_cost = assembly_info["point_cost"]
            
            new_assembly_sequence_info_list = []
            for first_sequence_info in assembly_sequence_info_list:
                for sequence in possible_sequences: # for second assembly
                    current_sequence_info = copy.deepcopy(first_sequence_info)
                    current_sequence = current_sequence_info["sequence"]
                    current_cost = current_sequence_info["cost"]

                    for pair_idx in sequence:
                        pair_idx += added_pair_idx
                        target_pair = available_pair[pair_idx]["target_pair"]
                        if target_pair[0]["part_id"] == part_id:
                            point_id = target_pair[0]["assembly_point"]
                            current_cost += point_cost[point_id]
                        else:
                            point_id = target_pair[1]["assembly_point"]
                            current_cost += point_cost[point_id]
                        current_sequence.append(pair_idx)
                    is_possible = self._check_available_sequence(available_pair, current_sequence)
                    if not is_possible:
                        continue
                    new_assembly_sequence_info_list.append({
                        "sequence": current_sequence,
                        "cost": current_cost
                    })
            assembly_sequence_info_list = copy.deepcopy(new_assembly_sequence_info_list)
            #endregion

        elif len(group_info_list) == 2 and assembly_type == AssemblyType.group_group_connector:
            """group + group + connector
            - group to group first(penet type)
            - then connector to group
            """
            available_pair = []
            group_boundary = 0
            for idx, group_info in enumerate(group_info_list):
                # connector to group
                possible_sequences, available_pair_0 = self._extract_possible_sequence(group_info, target_connector_instance)
                if not len(possible_sequences) > 0:
                    continue
                assembly_info = group_info["connection_loc"]
                available_pair += available_pair_0
                if assembly_info == None:
                    for sequence in possible_sequences:
                        sequence_info = {
                            "sequence": list(sequence),
                            "cost": 0
                        }
                        assembly_sequence_info_list.append(sequence_info)
                else:
                    point_cost =assembly_info["point_cost"]
                    for sequence in possible_sequences:
                        pair_idx = sequence[0]
                        target_pair = available_pair[pair_idx]["target_pair"]
                        
                        if assembly_info["part_id"] == target_pair[0]["part_id"]:
                            point_id = target_pair[0]["assembly_point"]
                            cost = point_cost[point_id]
                        else:
                            point_id = target_pair[1]["assembly_point"]
                            cost = point_cost[point_id]
                        sequence_info = {
                            "sequence": list(sequence),
                            "cost": cost
                        }
                        assembly_sequence_info_list.append(sequence_info)
                if idx == 0:
                    group_boundary = len(assembly_sequence_info_list)
                else:
                    pass
            new_assembly_sequence_info_list = []
            for idx, connector_sequence_info in enumerate(assembly_sequence_info_list):
                #region find used_part, point
                if idx > group_boundary:
                    other_group_info = group_info_list[0]
                else:
                    other_group_info = group_info_list[1]
                # initialize current(connector + group) sequence
                pair_idx = connector_sequence_info["sequence"][0] # len(current_sequence) == 1
                target_pair = available_pair[pair_idx]["target_pair"]
                
                # extract which part and point to use
                part_id_0 = target_pair[0]["part_id"] 
                part_id_1 = target_pair[1]["part_id"]
                if part_id_0 == used_assembly_instance.index(target_connector_instance):
                    used_part_id = part_id_1
                    used_point_id = target_pair[1]["assembly_point"]
                else:
                    used_part_id = part_id_0
                    used_point_id = target_pair[0]["assembly_point"]
                used_part_instance = used_assembly_instance[used_part_id]
                used_part_name = used_part_instance["part_name"]
                used_part_instance_id = used_part_instance["instance_id"]
                used_part_status = self.part_instance_status[used_part_name][used_part_instance_id]
                available_points = self._get_available_points(used_part_name, used_part_status) 
                
                target_assembly_point = self._get_other_point_of_penet(used_part_name, used_point_id)
                if not target_assembly_point in available_points:
                    continue
                #endregion
                
                #region find all possible sequence for target point to other group
                other_assembly_info = other_group_info["connection_loc"]
                available_pair_1 = []
                if other_assembly_info == None:
                    group_id = other_assembly_info["id"]
                    composed_parts_1 = self.group_status[group_id]["composed_part"]
                    for composed_part in composed_parts_1:
                        part_id_1 = used_assembly_instance.index(composed_part)
                        part_name_1 = used_assembly_instance[part_id_1]["part_name"]
                        instance_id_1 = used_assembly_instance[part_id_1]["instance_id"]
                        part_status_1 = self.part_instance_status[part_name_1][instance_id_1]
                        
                        assembly_points_1 = self._get_available_points(part_name_1, part_status_1)
                        available_pair_1 += self._get_available_assembly_pairs(part_id_0=used_part_id,
                                                                              part_name_0=used_part_name,
                                                                              assembly_points_0=[target_assembly_point],
                                                                              part_id_1=part_id_1,
                                                                              part_name_1=part_name_1,
                                                                              assembly_points_1=assembly_points_1,
                                                                              penet=connector_name)
                    possible_sequences = self._get_available_sequence(available_pair_1, assembly_num=1)

                else:
                    part_id_1 = other_assembly_info["part_id"]
                    part_name_1 = used_assembly_instance[part_id_1]["part_name"]
                    assembly_points_1 = list(other_assembly_info["point_cost"].keys())
                    available_pair_1 = self._get_available_assembly_pairs(part_id_0=used_part_id,
                                                                         part_name_0=used_part_name,
                                                                         assembly_points_0=[target_assembly_point],
                                                                         part_id_1=part_id_1,
                                                                         part_name_1=part_name_1,
                                                                         assembly_points_1=assembly_points_1,
                                                                         penet=connector_name)
                
                    possible_sequences = self._get_available_sequence(available_pair_1, assembly_num=1)

                for sequence in possible_sequences:
                    current_sequence_info = copy.deepcopy(connector_sequence_info)
                    current_sequence = current_sequence_info["sequence"]
                    current_cost = current_sequence_info["cost"] 
                    pair_idx = sequence[0]
                    target_assembly_pair = available_pair_1[pair_idx]
                    if not target_assembly_pair in available_pair:
                        available_pair.append(target_assembly_pair)
                    new_pair_idx = available_pair.index(target_assembly_pair)
                    
                    target_pair = target_assembly_pair["target_pair"]
                    if other_assembly_info == None:
                        current_cost += 0
                    else:
                        point_cost = other_assembly_info["point_cost"]
                        if target_pair[0]["part_id"] == part_id_1:
                            point_id = target_pair[0]["assembly_point"]
                            current_cost += point_cost[point_id]
                        else:
                            point_id = target_pair[1]["assembly_point"]
                            current_cost += point_cost[point_id]
                    current_sequence.append(new_pair_idx)
                    is_possible = self._check_available_sequence(available_pair, current_sequence)
                    if not is_possible:
                        continue
                    sequence_info = {
                        "sequence": current_sequence,
                        "cost": current_cost
                    }
                    new_assembly_sequence_info_list.append(sequence_info)
                #endregion
            
            assembly_sequence_info_list = copy.deepcopy(new_assembly_sequence_info_list)
        
        else:
            assert False
        
        return assembly_sequence_info_list, available_pair
    def _extract_possible_sequence(self, group_info, connector_instance):
        connector_name = connector_instance["part_name"]
        used_assembly_instance = self.assembly_info["part"]

        group_id = group_info["id"]
        assembly_info = group_info["connection_loc"]
        available_pair = []
        if assembly_info == None:
            # find available part inside group
            available_parts = []
            composed_parts = self.group_status[group_id]["composed_part"]
            for part_instance in composed_parts:
                part_name = part_instance["part_name"]
                instance_id = part_instance["instance_id"]
                part_status = self.part_instance_status[part_name][instance_id]
                if part_status["available_assembly"][connector_name] > 0:
                    available_points = self._get_available_points(part_name, part_status)
                    available_parts.append({
                        "part_instance": part_instance,
                        "available_points": available_points
                    })
            # find available points
            for available_part in available_parts:
                target_part_instance = available_part["part_instance"]
                part_id_0 = used_assembly_instance.index(target_part_instance)
                part_name_0 = target_part_instance["part_name"]
                assembly_points_0 = available_part["available_points"]

                part_id_1 = used_assembly_instance.index(connector_instance)
                part_name_1 = connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                     part_name_0=part_name_0,
                                                                     assembly_points_0=assembly_points_0,
                                                                     part_id_1=part_id_1,
                                                                     part_name_1=part_name_1,
                                                                     assembly_points_1=assembly_points_1)
        else:
            part_id_0 = assembly_info["part_id"]
            part_name_0 = used_assembly_instance[part_id_0]["part_name"]
            assembly_points_0 = list(assembly_info["point_cost"].keys())

            part_id_1 = used_assembly_instance.index(connector_instance)
            part_name_1 = connector_instance["part_name"]
            assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
            
            available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                 part_name_0=part_name_0,
                                                                 assembly_points_0=assembly_points_0,
                                                                 part_id_1=part_id_1,
                                                                 part_name_1=part_name_1,
                                                                 assembly_points_1=assembly_points_1)
        
        possible_sequences = self._get_available_sequence(available_pair, assembly_num=1)
        
        return possible_sequences, available_pair
    @staticmethod
    def _get_other_point_of_penet(part_name, point_id):
        other_point = None
        try:
            other_point = penet_condition[part_name][point_id]
        except:
            pass
        return other_point

    def simulate_instruction_assembly(self):
        assert len(self.assembly_info["assembly_sequence"]) > 0
        assembly_sequence_info = self.assembly_info["assembly_sequence"]
        sorted_sequence_info = sorted(assembly_sequence_info.items(), key=(lambda x: x[1]["cost"]))
        
        # assert len(assembly_sequences) == 1, "Not Implemented for multi case"
        assembly_sequences = [sequence_info[1]["sequence"] for sequence_info in sorted_sequence_info]
        target_sequence = None
        is_possible = False
        for assembly_sequence in assembly_sequences:
            if assembly_sequence:
                is_possible = self._simulate_assembly_sequecne(assembly_sequence)
            
            if is_possible:
                target_sequence = assembly_sequence
                break
            self.logger.info("############RETRY FIND ASSEMBLY SEQUENCE############")
        
        if not is_possible:
            self.logger.info("No available sequence for connection => Try other region matching...")
            if not self.is_retry:
                self.retry_instruction_assembly()
            self.is_retry = False

        else:
            self.assembly_info["target_sequence"] = copy.deepcopy(target_sequence)
            self.logger.info("End to simulate instruction assembly")

    def _simulate_assembly_sequecne(self, assembly_sequence):
        assembly_pairs = self.assembly_info["assembly"]

        sequence_part_status = copy.deepcopy(self.part_instance_status)
        sequence_group_status = copy.deepcopy(self.group_status)
        possible_sequence = []
        for pair_id in assembly_sequence:
            pair_assembly_info = assembly_pairs[pair_id]
            target_assembly_info = self._get_target_assembly_info(pair_assembly_info=pair_assembly_info,
                                                                    current_part_status=sequence_part_status,
                                                                    current_group_status=sequence_group_status)

            target_pair = target_assembly_info["target"]["target_pair"]
            current_status = target_assembly_info["status"]
            self.logger.info("""
            ...Waiting for simulate assemble:

                    ===>  {}_{}_{} and {}_{}_{}
            """.format(target_pair[0]["part_name"],
                       target_pair[0]["instance_id"],
                       target_pair[0]["assembly_point"],
                       target_pair[1]["part_name"],
                       target_pair[1]["instance_id"],
                       target_pair[1]["assembly_point"]))
            is_possible = False
            try:
                # is_possible = self.socket_module.check_assembly_possibility(target_assembly_info)
                response = self.socket_module.check_assembly_possibility(target_assembly_info)
                is_possible = response["is_possible"]
                self.logger.info("is possible? {}".format(is_possible))
            except:
                self.logger.info("ERROR!")

            if not is_possible:
                return False
            # update local status
            new_status = response["status"]
            possible_sequence.append(pair_id)
            """extract assembly info"""
            target_part_info_0 = target_pair[0]
            target_part_name_0 = target_part_info_0["part_name"]
            target_part_instance_id_0 = target_part_info_0["instance_id"]
            target_assembly_point_0 = target_part_info_0["assembly_point"]

            target_part_info_1 = target_pair[1]
            target_part_name_1 = target_part_info_1["part_name"]
            target_part_instance_id_1 = target_part_info_1["instance_id"]
            target_assembly_point_1 = target_part_info_1["assembly_point"]

            """update part instance status"""
            current_part_status_0 = sequence_part_status[target_part_name_0][target_part_instance_id_0]
            current_part_status_1 = sequence_part_status[target_part_name_1][target_part_instance_id_1]
            
            current_group_id_0 = current_part_status_0["group_id"]
            current_group_id_1 = current_part_status_1["group_id"]

            #region update used assembly points
            current_part_status_0["used_assembly_points"][target_assembly_point_0] = {
                "part_name": target_part_name_1,
                "instance_id": target_part_instance_id_1,
                "assembly_point": target_assembly_point_1
            }
            current_part_status_1["used_assembly_points"][target_assembly_point_1] = {
                "part_name": target_part_name_0,
                "instance_id": target_part_instance_id_0,
                "assembly_point": target_assembly_point_0
            }
            #endregion
            
            #region update available assembly(with connector) of part status
            if target_part_name_0 in self.connector_parts:
                current_part_status_1["available_assembly"][target_part_name_0] -= 1
            if target_part_name_1 in self.connector_parts:
                current_part_status_0["available_assembly"][target_part_name_1] -= 1
            #endregion

            #region get composed part and update group id and update available assembly for group
            current_composed_part = []
            # assemble in different group
            if not current_group_id_0 == current_group_id_1:
                # group + group => new group
                if current_group_id_0 in sequence_group_status.keys() and \
                    current_group_id_1 in sequence_group_status.keys():
                    new_group_id = len(sequence_group_status)
            
                # group + connector => group
                elif current_group_id_0 in sequence_group_status.keys():
                    new_group_id = current_group_id_0
                elif current_group_id_1 in sequence_group_status.keys():
                    new_group_id = current_group_id_1
            
                # connector + connector => stefan + pan head bolt
                else:
                    assert current_group_id_0 and current_group_id_1, "connector + connector?"
                    new_group_id = current_group_id_0
                
                if not current_group_id_0 == None:
                    current_composed_part += sequence_group_status[current_group_id_0]["composed_part"]
                if not current_group_id_1 == None:
                    current_composed_part += sequence_group_status[current_group_id_1]["composed_part"]
            
            # assembly in same group
            else:
                assert current_group_id_0 and current_group_id_1, "connector + connector?"
                new_group_id = current_group_id_0
                current_composed_part = sequence_group_status[current_group_id_0]["composed_part"]
            
            new_composed_part = current_composed_part
            if current_group_id_0 == None:
                new_composed_part.append({
                    "part_name": target_part_name_0,
                    "instance_id": target_part_instance_id_0
                })
            if current_group_id_1 == None:
                new_composed_part.append({
                    "part_name": target_part_name_1,
                    "instance_id": target_part_instance_id_1
                })
            # update gruop id of part instance and available assembly for group
            new_available_assembly = {connector_name: 0 for connector_name in self.connector_parts}
            for part_instance in new_composed_part:
                part_name = part_instance["part_name"]
                instance_id = part_instance["instance_id"]
                part_instance_status = sequence_part_status[part_name][instance_id]
                part_instance_status["group_id"] = new_group_id
                available_assembly = part_instance_status["available_assembly"]
                for connector_name in available_assembly.keys():
                    new_available_assembly[connector_name] += available_assembly[connector_name]
            #endregion
            
            """update group status"""
            # update existance state of group
            if current_group_id_0 and (not current_group_id_0 == new_group_id):
                sequence_group_status[current_group_id_0]["is_exist"] = False
            if current_group_id_1 and (not current_group_id_1 == new_group_id):
                sequence_group_status[current_group_id_1]["is_exist"] = False

            # add new assembly to status => new_status
            new_assembly = current_status["assembly"] + [target_assembly_info["target"]]
            new_status["assembly"] = new_assembly

            # update composed group => new_composed_group
            if new_group_id in sequence_group_status.keys():
                new_composed_group = sequence_group_status[new_group_id]["composed_group"]
            # create new group => new status
            else: 
                new_composed_group = sequence_group_status[current_group_id_0]["composed_group"] \
                    + sequence_group_status[current_group_id_1]["composed_group"]

            
            sequence_group_status[new_group_id] = {
                "is_exist": True,
                "composed_part": copy.deepcopy(new_composed_part),
                "status": copy.deepcopy(new_status),
                "composed_group": copy.deepcopy(new_composed_group),
                "available_assembly": copy.deepcopy(new_available_assembly)
            }

        if len(possible_sequence) < len(assembly_sequence):
            if len(self.second_solution["target_sequence"]) < len(possible_sequence):
                self.second_solution = {
                    "part_instance_status": sequence_part_status,
                    "group_status": sequence_group_status,
                    "target_sequence": possible_sequence
                }
            return False
        # update global status
        self.part_instance_status = sequence_part_status
        self.group_status = sequence_group_status

        return True
    def _get_target_assembly_info(self, pair_assembly_info, current_part_status,
                                current_group_status):
        used_part_instance = self.assembly_info["part"]

        pair_info = pair_assembly_info["target_pair"]
        method = pair_assembly_info["method"]

        part_id_0 = pair_info[0]["part_id"]
        part_id_1 = pair_info[1]["part_id"]
        assembly_point_0 = pair_info[0]["assembly_point"]
        assembly_point_1 = pair_info[1]["assembly_point"]

        part_info_0 = used_part_instance[part_id_0]
        part_info_1 = used_part_instance[part_id_1]
        part_name_0 = part_info_0["part_name"]
        part_name_1 = part_info_1["part_name"]
        part_instance_id_0 = part_info_0["instance_id"]
        part_instance_id_1 = part_info_1["instance_id"]
        
        # status
        part_status_0 = current_part_status[part_name_0][part_instance_id_0]
        group_id_0 = part_status_0["group_id"]
        part_status_1 = current_part_status[part_name_1][part_instance_id_1]
        group_id_1 = part_status_1["group_id"]
        
        current_assembly_status = []
        target_document = None
        target_object_info = {}
        if not group_id_0 == group_id_1:
            if (not group_id_0 == None) and (not group_id_1 == None):
                group_status_0 = current_group_status[group_id_0]["status"]
                group_status_1 = current_group_status[group_id_1]["status"]

                object_info_0 = group_status_0["object_info"]
                object_info_1 = group_status_0["object_info"]
                if len(object_info_0) < len(object_info_1):
                    target_document = group_status_1["document"]
                    target_object_info = group_status_1["object_info"]
                else:
                    target_document = group_status_0["document"]
                    target_object_info = group_status_0["object_info"]
                current_assembly_status += group_status_0["assembly"]
                current_assembly_status += group_status_1["assembly"]
            else:
                if not group_id_0 == None:
                    current_assembly_status += current_group_status[group_id_0]["status"]["assembly"]
                    target_document = current_group_status[group_id_0]["status"]["document"]
                    target_object_info = current_group_status[group_id_0]["status"]["object_info"]
                
                elif not group_id_1 == None:
                    current_assembly_status += current_group_status[group_id_1]["status"]["assembly"]
                    target_document = current_group_status[group_id_1]["status"]["document"]
                    target_object_info = current_group_status[group_id_1]["status"]["object_info"]
                    
        else:
            assert group_id_0 and group_id_1, "connector + connector?"
            target_document = current_group_status[group_id_0]["status"]["document"]
            target_object_info = current_group_status[group_id_0]["status"]["object_info"]
            current_assembly_status = current_group_status[group_id_0]["status"]["assembly"]

        target_assembly_info = {
            "target": {
                "target_pair": {
                    0:{
                        "part_name": part_name_0,
                        "instance_id": part_instance_id_0,
                        "assembly_point": assembly_point_0
                    },
                    1:{
                        "part_name": part_name_1,
                        "instance_id": part_instance_id_1,
                        "assembly_point": assembly_point_1
                    }
                },  
                "method": method
            },
            "status": {
                "document": target_document,
                "object_info": target_object_info,
                "assembly": current_assembly_status
            }
            
        }

        return target_assembly_info
    
    def retry_instruction_assembly(self):
        connection_list = self.instruction_assembly_info["connection"]
        for connection_idx, connection in enumerate(connection_list):
            used_group_list = connection["component"]["group"]
            for group_connection in used_group_list:
                group_connection["connection_loc"] = None
        self.is_retry = True
        self.search_assembly_sequence()
        self.simulate_instruction_assembly()
        
    def simulate_hidden_assembly(self):
        # 1. check available assembly for each part in group
        current_group_parts = self.assembly_info["part"] # dict of part_instance
        """point
        part_instance
        point_id
        """
        if "ikea_stefan_bolt_side" in self.instruction_assembly_info["checker"]["Connector"].keys():
            pass
        else:
            return False
        part_instance_idx_list = range(len(current_group_parts))
        all_possible_part_pair = combinations(part_instance_idx_list, 2)
        
        already_exist_part_pair = self.used_instance_set
        for pair_idx in self.assembly_info["target_sequence"]:
            pair_info = self.assembly_info["assembly"][pair_idx]["target_pair"]
            part_id_0 = pair_info[0]["part_id"]
            part_id_1 = pair_info[1]["part_id"]
            part_instance_0 = current_group_parts[part_id_0]
            part_instance_1 = current_group_parts[part_id_1]

            already_exist_part_pair.append(set([part_instance_0.values(), part_instance_1.values()]))

        available_assembly_pair = []
        for part_pair in all_possible_part_pair:
            part_id_0 = part_pair[0]
            part_id_1 = part_pair[1]
            
            part_instance_0 = current_group_parts[part_id_0]
            part_name_0 = part_instance_0["part_name"]
            instance_id_0 = part_instance_0["instance_id"]
            
            part_instance_1 = current_group_parts[part_id_1]
            part_name_1 = part_instance_1["part_name"]
            instance_id_1 = part_instance_1["instance_id"]
            
            checker = set([part_instance_0.values(), part_instance_1.values()])
            if checker in already_exist_part_pair:
                continue
            
            part_status_0 = self.part_instance_status[part_name_0][instance_id_0]
            assembly_points_0 = self._get_available_points(part_name_0, part_status_0)
            
            part_status_1 = self.part_instance_status[part_name_1][instance_id_1]
            assembly_points_1 = self._get_available_points(part_name_1, part_status_1)
            

            if (len(assembly_points_0) > 0) and (len(assembly_points_1) > 0):
                assembly_pair = self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                   part_name_0=part_name_0,
                                                                   assembly_points_0=assembly_points_0,
                                                                   part_id_1=part_id_1,
                                                                   part_name_1=part_name_1,
                                                                   assembly_points_1=assembly_points_1) 
                if len(assembly_pair) > 0:

                    available_assembly_pair += assembly_pair
        # 2. check available_assembly in current status
        used_point = []
        used_assembly_pair = []
        
        for pair_idx, pair_assembly_info in enumerate(available_assembly_pair):
            target_assembly_info = self._get_target_assembly_info(pair_assembly_info=pair_assembly_info,
                                                                  current_part_status=self.part_instance_status,
                                                                  current_group_status=self.group_status)

            target_pair = target_assembly_info["target"]["target_pair"]
            current_status = target_assembly_info["status"]
            if target_pair[0] in used_point:
                continue
            if target_pair[1] in used_point:
                continue
            target_part_info_0 = target_pair[0]
            target_part_name_0 = target_part_info_0["part_name"]
            target_part_instance_id_0 = target_part_info_0["instance_id"]
            target_assembly_point_0 = target_part_info_0["assembly_point"]

            target_part_info_1 = target_pair[1]
            target_part_name_1 = target_part_info_1["part_name"]
            target_part_instance_id_1 = target_part_info_1["instance_id"]
            target_assembly_point_1 = target_part_info_1["assembly_point"]

            current_part_status_0 = self.part_instance_status[target_part_name_0][target_part_instance_id_0]
            current_part_status_1 = self.part_instance_status[target_part_name_1][target_part_instance_id_1]
            
            group_id_0 = current_part_status_0["group_id"]
            group_id_1 = current_part_status_1["group_id"]
            if not group_id_0 == group_id_1:
                continue

            self.logger.info("""...Waiting for simulate Hidden assemble:

                    ===>  {}_{}_{} and {}_{}_{}
            """.format(target_pair[0]["part_name"],
                       target_pair[0]["instance_id"],
                       target_pair[0]["assembly_point"],
                       target_pair[1]["part_name"],
                       target_pair[1]["instance_id"],
                       target_pair[1]["assembly_point"]))
            is_possible = False
            try:
                # is_possible = self.socket_module.check_assembly_possibility(target_assembly_info)
                response = self.socket_module.check_assembly_possibility(target_assembly_info)
                is_possible = response["is_possible"]
                self.logger.info("is possible? {}".format(is_possible))
            except:
                self.logger.info("ERROR!")

            if not is_possible:
                continue
            # update local status
            """extract assembly info"""
            

            

            new_status = response["status"]
            """update part instance status"""
            current_part_status_0 = self.part_instance_status[target_part_name_0][target_part_instance_id_0]
            current_part_status_1 = self.part_instance_status[target_part_name_1][target_part_instance_id_1]
            
            group_id_0 = current_part_status_0["group_id"]
            group_id_1 = current_part_status_1["group_id"]
            if not group_id_0 == group_id_1:
                continue
            group_id = group_id_0
            #region update used assembly points
            current_part_status_0["used_assembly_points"][target_assembly_point_0] = {
                "part_name": target_part_name_1,
                "instance_id": target_part_instance_id_1,
                "assembly_point": target_assembly_point_1
            }
            current_part_status_1["used_assembly_points"][target_assembly_point_1] = {
                "part_name": target_part_name_0,
                "instance_id": target_part_instance_id_0,
                "assembly_point": target_assembly_point_0
            }
            #endregion
            
            #region update available assembly(with connector) of part status
            if target_part_name_0 in self.connector_parts:
                current_part_status_1["available_assembly"][target_part_name_0] -= 1
            if target_part_name_1 in self.connector_parts:
                current_part_status_0["available_assembly"][target_part_name_1] -= 1
            #endregion

            # update gruop id of part instance and available assembly for group
            new_available_assembly = {connector_name: 0 for connector_name in self.connector_parts}
            for part_instance_key in current_group_parts.keys():
                part_instance = current_group_parts[part_instance_key]
                part_name = part_instance["part_name"]
                instance_id = part_instance["instance_id"]
                part_instance_status = self.part_instance_status[part_name][instance_id]
                available_assembly = part_instance_status["available_assembly"]
                for connector_name in available_assembly.keys():
                    new_available_assembly[connector_name] += available_assembly[connector_name]
            
            """update group status"""
            # add new assembly to status => new_status
            new_assembly = current_status["assembly"] + [target_assembly_info["target"]]
            new_status = response["status"]
            new_status["assembly"] = new_assembly

            self.group_status[group_id]["status"] = copy.deepcopy(new_status)
            self.group_status[group_id]["available_assembly"] = copy.deepcopy(new_available_assembly)

            """update hidden pair"""
            used_assembly_pair.append(pair_assembly_info)
            used_point.append(target_part_info_0)
            used_point.append(target_part_info_1)
            part_instance_0 = {
                "part_name": target_part_name_0,
                "instance_id": target_part_instance_id_0
            }
            part_instance_1 = {
                "part_name": target_part_name_1,
                "instance_id": target_part_instance_id_1
            }
            already_exist_part_pair.append(set([part_instance_0.values(), part_instance_1.values()]))

        start_idx = len(self.assembly_info["assembly"])
        
        hidden_sequence = list(range(start_idx, start_idx + len(used_assembly_pair)))
        for pair_idx, assembly_pair in zip(hidden_sequence, used_assembly_pair):
            self.assembly_info["assembly"][pair_idx] = assembly_pair
            self.assembly_info["target_sequence"].append(pair_idx)
         
    def compile_2_SNU_format(self):
        """
        SNU_assembly_info = {
            "part"
            "assembly"
            "sequence"
        }
        """
        self.sorted_assembly_info = {}
        SNU_assembly_info = {}
        SNU_assembly_info["part"] = copy.deepcopy(self.assembly_info["part"])
        assembly_pair_dict = self.assembly_info["assembly"]
        assembly_dict = {}
        for assembly_id in assembly_pair_dict.keys():
            assembly_pair = assembly_pair_dict[assembly_id]
            target_pair = assembly_pair["target_pair"]
            assembly_dict[assembly_id] = copy.deepcopy(target_pair)
        SNU_assembly_info["assembly"] = assembly_dict
        
        SNU_assembly_info["sequence"] = self.assembly_info["target_sequence"]
        
        sorted_doc = self._sorting_assembly_info(SNU_assembly_info)
        SNU_assembly_info = copy.deepcopy(sorted_doc)
        save_dic_to_yaml(SNU_assembly_info, join(self.SNU_result_path, "snu_sequence_{}.yaml".format(self.current_step)))
        self.sorted_assembly_info = SNU_assembly_info

    def visualization(self):
        self.socket_module.start_visualization(current_step=self.current_step,
                                               group_info=self.group_info,
                                               group_status=self.group_status,
                                               instruction_info=self.instruction_info,
                                               assembly_info=self.sorted_assembly_info,
                                               is_end=self.is_end)
        self.logger.info("Visualize Step {} using Blender".format(self.current_step))

    @staticmethod
    def _sorting_assembly_info(assembly_info):
        used_part = assembly_info["part"]
        used_assembly = []
        whole_sequence = []
        remove_condition = [
            set(["ikea_stefan_bolt_side", "ikea_stefan_long"]),
            set(["ikea_stefan_bolt_side", "ikea_stefan_short"]),
            set(["ikea_stefan_bolt_side","ikea_stefan_middle"])
        ]
        furniture_2_part_id = {}
        connector_2_part_id = {
            "ikea_stefan_bracket": [],
            "ikea_stefan_pin": [],
            "ikea_stefan_bolt_side": [],
            "pan_head_screw_iso(4ea)": []
        }
        parts = assembly_info["part"] # dict
        all_assembly = assembly_info["assembly"] # dict
        step_sequence = assembly_info["sequence"] # list
        for assembly_idx in step_sequence:
            target = all_assembly[assembly_idx]
            part_id_0 = target[0]["part_id"]
            part_id_1 = target[1]["part_id"]
            part_0 = parts[part_id_0]
            part_1 = parts[part_id_1]
            
            part_name_0 = part_0["part_name"]
            part_name_1 = part_1["part_name"]
            part_pair = set([part_name_1, part_name_0])
            if part_pair in remove_condition:
                continue
            if part_name_0 in connector_2_part_id.keys():
                connector_2_part_id[part_name_0].append(part_id_0)
            else:
                furniture_2_part_id[part_name_0] = part_id_0

            if part_name_1 in connector_2_part_id.keys():
                connector_2_part_id[part_name_1].append(part_id_1)
            else:
                furniture_2_part_id[part_name_1] = part_id_1
            used_assembly.append(target)
            sequence_idx = used_assembly.index(target)
            whole_sequence.append(sequence_idx)
        # sequence: connector -> furniture => furniture(connector) -> furniture
        connector_2_sequence = {connector_name: [] for connector_name in connector_2_part_id.keys()}

        for assembly_idx in whole_sequence:
            assembly = used_assembly[assembly_idx]
            part_id_0 = assembly[0]["part_id"]
            part_id_1 = assembly[1]["part_id"]

            for connector_name in connector_2_sequence.keys():
                connector_id_list = connector_2_part_id[connector_name]
                if part_id_0 in connector_id_list:
                    connector_2_sequence[connector_name].append(assembly_idx)
                elif part_id_1 in connector_id_list:
                    temp = copy.deepcopy(assembly[0])
                    assembly[0] = copy.deepcopy(assembly[1])
                    assembly[1] = temp
                    connector_2_sequence[connector_name].append(assembly_idx)
        for connector_name in connector_2_sequence.keys():
            connector_sequence = connector_2_sequence[connector_name]
            sorted_sequence = []
        
            for furniture_name in furniture_2_part_id.keys():
                furniture_part_id = furniture_2_part_id[furniture_name]
    
                for assembly_idx in connector_sequence:
                    assembly = used_assembly[assembly_idx]
                    part_id_1 = assembly[1]["part_id"]
                    if part_id_1 == furniture_part_id:
                        sorted_sequence.append(assembly_idx)
    
            connector_2_sequence[connector_name] = copy.deepcopy(sorted_sequence)
        """sorting sequence by used state"""
        sorted_whole_sequence = []
        used_connector = []
        for connector_name in connector_2_sequence.keys():
            connector_sequence = connector_2_sequence[connector_name]
            for assembly_idx in connector_sequence:
                assembly = used_assembly[assembly_idx]
                connector_id = assembly[0]["part_id"]
                part_id = assembly[1]["part_id"]
                if connector_id in used_connector:
                    continue

                sorted_whole_sequence.append(assembly_idx)
            for remain_sequence in connector_sequence:
                if remain_sequence in sorted_whole_sequence:
                    continue
                sorted_whole_sequence.append(remain_sequence)
        """compiled info"""
        compiled_assembly_info = {}
        
        compiled_assembly_info["part"] = used_part

        temp = {}
        for idx, val in enumerate(used_assembly):
            temp[idx] = copy.deepcopy(val)
        compiled_assembly_info["assembly"] = temp

        compiled_assembly_info["sequence"] = sorted_whole_sequence

        return compiled_assembly_info

    #region utils
    def _get_available_points(self, part_name, part_status):
        assert self.part_info
        all_points = set(self.part_info[part_name]["assembly_points"].keys())
        used_point = set(part_status["used_assembly_points"].keys())
        return list(all_points - used_point)
    def _get_available_assembly_pairs(self, part_id_0, part_name_0, assembly_points_0, 
                                            part_id_1, part_name_1, assembly_points_1, penet=None):
        assert self.assembly_pair
        available_assembly = []
        part_0_info = self.assembly_pair[part_name_0]
        for assembly_point_idx_0 in assembly_points_0:
            availabe_pair_list = part_0_info[assembly_point_idx_0]
            for pair_info in availabe_pair_list:
                if pair_info["part_name"]==part_name_1\
                    and pair_info["assembly_point"] in assembly_points_1:
                    if not pair_info["penet"] == penet:
                        continue
                    assembly_pair_info = {
                        "method":{
                            "direction": pair_info["direction"],
                            "offset": pair_info["offset"],
                            "additional": copy.deepcopy(pair_info["additional"])
                        },
                        "target_pair": {
                            0:{
                                "part_id": part_id_0,
                                "assembly_point": assembly_point_idx_0
                            },
                            1:{
                                "part_id": part_id_1,
                                "assembly_point": pair_info["assembly_point"]
                            }
                        }
                    }
                    available_assembly.append(assembly_pair_info)
                
        return available_assembly
    def _get_available_sequence(self, assembly_pairs, assembly_num, group_condition=[]):
        """get all possible sequence from assembly_pairs
        - using rule is one point is used once
        - condition means 
        Args:
            assembly_pairs (list): [description]
            assembly_num (int)
            condition (list of pair_idx)
        return: 
            possible_sequence (list of tuple):
        """
        pair_idx_list = range(len(assembly_pairs))
        all_possible_sequence = set(combinations(pair_idx_list, assembly_num)) # list of tuple

        impossible_sequence = []
        
        # check sequence
        for sequence in all_possible_sequence:
            is_possible = self._check_available_sequence(assembly_pairs, sequence)
            if not is_possible:
                impossible_sequence.append(sequence)
        possible_sequence = list(all_possible_sequence - set(impossible_sequence))

        return possible_sequence
    @staticmethod
    def _check_available_sequence(assembly_pairs, sequence):
        used_point = [] # point == {assembly point, part_id}
        is_possible = True
        for pair_idx in sequence:
            target_assembly_pair = assembly_pairs[pair_idx]
            target_pair = target_assembly_pair["target_pair"]
            for idx in target_pair.keys():
                point = target_pair[idx]
                if point in used_point:
                    is_possible = False
                    return is_possible
                else:
                    used_point.append(point)
        return is_possible
    #endregion
    
    def compile_whole_sequence(self):
        sequence_root = self.SNU_result_path
        sequence_file_list = get_file_list(sequence_root)
        
        used_part = []
        used_assembly = []
        whole_sequence = []

        for sequence_file in sequence_file_list:
            assembly_info = load_yaml_to_dic(sequence_file)
            
            parts = assembly_info["part"] # dict
            all_assembly = assembly_info["assembly"] # dict
            step_sequence = assembly_info["sequence"] # list
            
            for assembly_idx in step_sequence:
                target_assembly = all_assembly[assembly_idx]
                if target_assembly in used_assembly:
                    # assert False, "ERROR"
                    continue
                
                part_id_0 = target_assembly[0]["part_id"]
                part_id_1 = target_assembly[1]["part_id"]
                
                part_0 = parts[part_id_0]
                part_1 = parts[part_id_1]

                if not part_0 in used_part:
                    used_part.append(part_0)
                if not part_1 in used_part:
                    used_part.append(part_1)
                
                part_id_0 = used_part.index(part_0)
                part_id_1 = used_part.index(part_1)
                
                target_assembly[0]["part_id"] = part_id_0
                target_assembly[1]["part_id"] = part_id_1

                part_name_0 = part_0["part_name"]
                part_name_1 = part_1["part_name"]
                
                used_assembly.append(target_assembly)
                sequence_idx = used_assembly.index(target_assembly)
                whole_sequence.append(sequence_idx)

        """compiled info"""
        compiled_assembly_info = {}
        
        temp = {}
        for idx, val in enumerate(used_part):
            temp[idx] = val
        compiled_assembly_info["part"] = temp

        temp = {}
        for idx, val in enumerate(used_assembly):
            temp[idx] = copy.deepcopy(val)
        compiled_assembly_info["assembly"] = temp

        compiled_assembly_info["sequence"] = whole_sequence

        save_dic_to_yaml(compiled_assembly_info, "final_result.yaml")
        return compiled_assembly_info

if __name__ == "__main__":
    pass
    # doc = AssemblyManager.compile_whole_sequence("./assembly/STEFAN/SNU_result")
    