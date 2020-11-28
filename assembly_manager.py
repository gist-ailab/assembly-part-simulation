from operator import add
from script.const import PartType, AssemblyType
from script.fileApi import *
from enum import Enum
from socket_module import SocketModule

import copy
from itertools import combinations
import random

import numpy as np

class AssemblyManager(object):

    def __init__(self, logger, furniture_name, cad_root="./cad_file", instruction_root="./instruction"):
        self.logger = logger
        self.furniture_name = furniture_name

        # input path
        self.cad_root = cad_root
        self.cad_path = join(self.cad_root, self.furniture_name)
        self.instruction_root = instruction_root
        self.instruction_path = join(self.instruction_root, self.furniture_name)
        
        self.is_end = False

        # 조립 폴더 생성
        self.assembly_root = "./assembly"
        check_and_create_dir("./assembly")
        self.assembly_path = join("./assembly", self.furniture_name)
        check_and_create_dir(self.assembly_path)
        # Group(*.obj) 폴더 생성
        self.group_obj_path = join(self.assembly_path, "group_obj")
        check_and_create_dir(self.group_obj_path)
        # Group info 폴더 생성 => intruction 정보 분석에 사용
        self.group_info_root = join(self.assembly_path, "group_info")
        check_and_create_dir(self.group_info_root)
        
        self.socket_module = SocketModule(self.logger)
        
        # 내부에서 사용하는 데이터(저장은 선택)
        self.part_info_path = join(self.assembly_path, "part_info.yaml")
        self.assembly_pair_path = join(self.assembly_path, "assembly_pair.yaml")
        self.refined_pair_path = "./assembly_pair_refined.yaml"
        
        self.part_info = None
        self.connector_info = None
        self.assemlby_pair = None
        self.furniture_parts, self.connector_parts = [], [] # save part_name
        self.assembly_info = None

        # 매 스탭 마다 바뀌는 정보
        self.current_step = 0
        self.group_info = None
        self.group_info_path = join(self.group_info_root, "group_info_{}.yaml".format(self.current_step))
        self.instruction_info = None
        self.connection_assembly_sequence = None
        
        # 조립 마다 바뀌는 정보
        self.part_instance_status = {}
        self.group_status = {}

    def initialize_CAD_info(self):
        self.logger.info("...Waiting for cad info from FreeCAD Module")
        self.part_info = self.socket_module.initialize_cad_info(self.cad_path)
        save_dic_to_yaml(self.part_info, self.part_info_path)
        # self.part_info = load_yaml_to_dic(self.part_info_path)
        self._initialize_assembly_pair()
        save_dic_to_yaml(self.assembly_pair, self.assembly_pair_path)
        # self.assembly_pair = load_yaml_to_dic(self.refined_pair_path)

        self._initialize_each_parts()
        self._initialize_part_instance_status()
        self._initialize_connector_info()            
        self._initialize_group_status()
    def _initialize_assembly_pair(self):
        """part info 를 바탕으로 가능한 모든 assembly pairs 를 출력
        - radius_group => all possible groups
        # radius info
            0 2.499999999999989 # pin:1
            1 2.499999999999995 # pin:0
            2 2.5000000000000004 # long:1,4 middle:2,5 short:1,4
            3 2.7499999999999747 # left:3,4, right:3,4
            4 2.750000000000001 # left:0 right:0
            5 3.000000000000001 # brcket:0
            6 3.0000000000000027 # long:6,7 short:6,7
            7 3.4999999999999996 # short:0,2,3,5
            8 3.5 # bracket:1
            9 4.0  #(9~13) # long,middle,left,right wiht pin
            10 4.000000000000001
            11 4.000000000000002
            12 4.000000000000003
            13 4.0000000000000036
            14 5.65 # bolt:0
            15 6.0 # pan_head_screw_iso(4ea):0
            16 7.9 # bolt:1 
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
            "pin": [0, 1, 7, 9, 10, 11, 12, 13],
            "bracket": [5, 6],
            "flat_penet": [2, 16], 
            "flat": [3, 4, 14], # 5.65
            "pan": [8, 15] # 6
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
                            if get_group(point_1["radius"]) == "flat_penet":
                                offset = -30 
                                if part_name_1 =="ikea_stefan_bolt_side":
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
                            target = {
                                "part_name": part_name_2,
                                "assembly_point": point_idx_2,
                                "direction": direction,
                                "offset": offset,
                                "additional": additional_option
                            }
                            assembly_pairs[part_name_1][point_idx_1].append(target)
        
        self.assembly_pair =  assembly_pairs
    def _initialize_each_parts(self):
        for part_name in self.part_info.keys():
            if self.part_info[part_name]["type"] == PartType.furniture.value:
                self.furniture_parts.append(part_name)
            elif self.part_info[part_name]["type"] == PartType.connector.value:
                self.connector_parts.append(part_name)
            else:
                self.logger.error("type is not matching!")
                exit()
    def _initialize_part_instance_status(self):
        part_instance_quantity = {
            "ikea_stefan_bolt_side": 6,
            "ikea_stefan_bracket": 4,
            "ikea_stefan_pin": 14,
            "pan_head_screw_iso(4ea)": 4,
        }
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
                quantity = part_instance_quantity[part_name]
            except:
                quantity = 1
            for i in range(quantity):
                part_instance_status[part_name][i] = {
                    "used_assembly_points": {},
                    "group_id": None,
                    "available_assembly": copy.deepcopy(available_assembly)
                }

        self.part_instance_status = part_instance_status
    def _initialize_connector_info(self):
        connector_info = {}
        for connector_id, connector_name in enumerate(self.connector_parts):
            connector_info[connector_id] = {
                "part_name": connector_name
            }
        self.connector_info = connector_info
    def _initialize_group_status(self):
        # furniture part 를 베이스로 하여 그룹을 생성
        for group_id, part_name in enumerate(self.furniture_parts):
            group_status = {
                "composed_part": [{
                    "part_name": part_name,
                    "instance_id": 0
                }],
                "status": [],
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

        save_dic_to_yaml(copy.deepcopy(self.assembly_info), "example_assembly_info_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.part_instance_status, "example_part_instance_status_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_status, "example_group_status_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_info, "example_group_info_{}.yaml".format(self.current_step))

        self.current_step += 1
        # update instruction info
        self._get_instruction_info()
        save_dic_to_yaml(self.instruction_info, "example_instruction_info_{}.yaml".format(self.current_step))
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
    def _get_instruction_info(self):
        self.logger.info("... wating for instruction of [step {}]".format(self.current_step))
        self.instruction_info = self.socket_module.get_instruction_info(self.current_step, self.group_info, self.connector_info)
        if self.instruction_info:
            self.logger.info("Get instruction of [step {}] information !".format(self.current_step))
            self.is_end = False
        else:
            self.logger.info("Instruction end!")
            self.is_end = True

    def initialize_part_to_scene(self):
        self.logger.info("...Waiting for initialize PyRep scene")
        self.socket_module.initialize_part_to_scene(self.part_info, self.assembly_pair)
        
    def extract_assembly_info(self):
        assert self.instruction_info
        self.assembly_info = {}
        self.assembly_info["part"] = []
        used_part_instances = self.assembly_info["part"]
        self.connection_assembly_sequence = []
        """extract instruction info"""
        instruction_group_info = self.instruction_info["Group"]
        instruction_connection_info = self.instruction_info['Connection']
        
        """extract used parts from using group"""
        group_assembly = {}
        for group_info in instruction_group_info:
            group_id = group_info["group_id"]
            group_assembly.setdefault(group_id, [])
            used_group_status = self.group_status[group_id]
            used_parts = used_group_status["composed_part"]
            for used_part in used_parts:
                part_name = used_part["part_name"]
                instance_id = used_part["instance_id"]
                used_part_info = {
                    "part_name": part_name,
                    "instance_id": instance_id,
                }
                used_part_instances.append(used_part_info)

        """extract connection assembly_sequence from connection info"""
        
        connection_assembly_sequence = []

        for connection_info in instruction_connection_info:
            connection_assembly = self._get_connection_assembly(connection_info)
            connection_assembly_sequence.append(connection_assembly)
        # search assembly point for each group
                
        for connection_assembly in connection_assembly_sequence:
            component_info = connection_assembly["component"]
            group_list = component_info["group"]
            connector_id = component_info["connector"]
            for group_info in group_list:
                group_id = group_info["id"]
                connection_loc = group_info["assembly_point"]
                group_assembly[group_id].append({
                    "connection_loc": connection_loc,
                    "connector_name": self.connector_parts[connector_id]
                })
        
        for group_id in group_assembly.keys():
            connection_list = group_assembly[group_id]
            connection_locs = []
            connector_name = None
            assembly_points = []
            for connection in connection_list:
                if not connection["connection_loc"]:
                    continue
                connection_locs.append(connection["connection_loc"])
                connector_name = connection["connector_name"]
            assembly_points = self._get_assembly_points(group_id, connection_locs, connector_name)
            
            for connection_assembly in connection_assembly_sequence:
                component_info = connection_assembly["component"]
                group_list = component_info["group"]
                for group_info in group_list:
                    connection_loc = group_info["assembly_point"]
                    if connection_loc in connection_locs:
                        idx = connection_locs.index(connection_loc)
                        group_info["assembly_point"] = assembly_points[idx]

        self.connection_assembly_sequence = copy.deepcopy(connection_assembly_sequence)

        # To save form
        for connection_assembly in connection_assembly_sequence:
            connection_assembly["assembly_type"] = connection_assembly["assembly_type"].name
        save_dic_to_yaml(copy.deepcopy(self.connection_assembly_sequence), "example_connection_sequence_{}.yaml".format(self.current_step))

        self.logger.info("Success to extrct assembly info")
            
    def _get_connection_assembly(self, connection_info):
        """connection_assembly = {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group": [
                    {
                        "id": 1,
                        "assembly_point": component loc(position or None)
                    }
                    },
                ],
                "connector": 1,
            }
        }"""
        connection_assembly = {}
        connection_assembly.setdefault("assembly_type", None)
        connection_assembly.setdefault("component", {})
        component_info = connection_assembly["component"]
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
                    "assembly_point": connection_loc
                }
                component_info["group"].append(connection_group_info)

            else:
                assert False                
        
        connection_assembly["assembly_type"] = AssemblyType.find_type(assembly_type)
        
        return connection_assembly
    def _get_region_id(self, group_id, connection_loc):
        region_id = self.socket_module.get_region_id(group_id=group_id,
                                                    connection_loc=connection_loc)
    def _get_assembly_points(self, group_id, connection_locs, connector_name):
        """get assembly point from location

        Args:
            group_id ([type]): [description]
            connection_loc ([type]): [description]

        Returns:
            assembly_point = {
                part_name:
                instance_id:
                assembly_point
            }
        """
        if connector_name:
            assembly_points = self.socket_module.get_assembly_point(group_id, connection_locs, connector_name)
        else:
            assembly_points = None
        return assembly_points

    def search_assembly_sequence(self):
        self.assembly_info["assembly"] = []
        self.assembly_info["assembly_sequence"] = []
        # region_assembly_sequence = region_assembly_sequence_ex["sequence_{}".format(self.current_step)]
        # assembly_sequence = self.assembly_info["assembly_sequence"]
        # for group_assembly in region_assembly_sequence:
        #     seq = self._extract_sequence_from_region_assembly(group_assembly)
        #     assembly_sequence += seq
        assembly_sequence = self.assembly_info["assembly_sequence"]
        for connection_assembly in self.connection_assembly_sequence:
            seq = self._extract_sequence_from_connection_assembly(connection_assembly)
            assembly_sequence += seq

        temp_dict = {}
        for idx, v in enumerate(self.assembly_info["part"]):
            temp_dict[idx] = v
        self.assembly_info["part"] = temp_dict
        temp_dict = {}
        for idx, v in enumerate(self.assembly_info["assembly"]):
            temp_dict[idx] = v
        self.assembly_info["assembly"] = temp_dict

    def _extract_sequence_from_region_assembly(self, region_assembly):
        used_assembly_instance = self.assembly_info["part"]
        assembly_component = region_assembly["component"]
        assembly_type = region_assembly["assembly_type"]
        # connector instance
        connctor_id = assembly_component["connector"]
        connector_name = self.connector_info[connctor_id]["part_name"]
        assembly_num = assembly_component["assembly_number"]

        used_connector_instance = []

        count = 0
        assert count < assembly_num, "number of connector error {}".format(assembly_num)
        connector_instance_info = self.part_instance_status[connector_name]
        for instance_idx in connector_instance_info.keys():
            connector_instance = {
                "part_name": connector_name,
                "instance_id": instance_idx
            }
            is_in_group = not (connector_instance_info[instance_idx]["group_id"] == None)
            if (connector_instance in used_connector_instance) or \
                is_in_group or\
                    (connector_instance in used_assembly_instance):
                continue
            used_connector_instance.append(connector_instance)
            used_assembly_instance.append(connector_instance)
            count += 1
            if count == assembly_num:
                break
            else:
                continue
        assert count == assembly_num, "number of connector error: there is no enough {}".format(connector_name)

        # group(part instance)
        group_info_list = assembly_component["group"] # list of used_group info
        
        # get one sequence
        available_pair = []
        group_assembly_sequence = [] 

        if len(group_info_list) == 1:
            """group + connector
            - assume that connector used here is newly added to group
            - so the output(available sequences) is all same result
                => choose one for random
            """
            group_info = group_info_list[0]           
            group_id = group_info["id"]
            target_part_instance = group_info["part_instance"]
            
            target_part_name = target_part_instance["part_name"]
            target_part_instance_id = target_part_instance["instance_id"]
            target_part_instance_status = self.part_instance_status[target_part_name][target_part_instance_id]

            used_assembly_points = set(target_part_instance_status["used_assembly_points"].keys())
            region_id = group_info["region"]
            if region_id:
                part_assembly_points = set(self.part_info[target_part_name]["region_info"][region_id]["points"])
            else:
                part_assembly_points = set(self.part_info[target_part_name]["assembly_points"].keys())
            part_assembly_points -= used_assembly_points
            part_assembly_points = list(part_assembly_points)
            
            part_id_0 = used_assembly_instance.index(target_part_instance)
            part_name_0 = target_part_name
            assembly_points_0 = part_assembly_points

            assert len(assembly_points_0) > assembly_num 
            
            for connector_instance in used_connector_instance:
                part_id_1 = used_assembly_instance.index(connector_instance)
                part_name_1 = connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())

                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num)
            one_possible_sequence = list(random.choice(possible_sequences))
            
            group_assembly_sequence += one_possible_sequence

        elif len(group_info_list) == 2 and assembly_type == AssemblyType.group_connector_group:
            """group + connector => group + group
            or group + group => group + connector
            """
            # choice one group which has less 
            # assume that idx order is small to big group(or more meaning)
            
            #region assemble group + connector
            """group + connector
            - assume that connector used here is newly added to group
            - so the output(available sequences) is all same result
                => choose one for random
            """
            group_info = group_info_list[0]
            group_id = group_info["id"]

            target_part_instance = group_info["part_instance"]
            target_part_name = target_part_instance["part_name"]
            target_part_instance_id = target_part_instance["instance_id"]
            target_part_instance_status = self.part_instance_status[target_part_name][target_part_instance_id]

            used_assembly_points = set(target_part_instance_status["used_assembly_points"].keys())
            region_id = group_info["region"]
            if region_id:
                part_assembly_points = set(self.part_info[target_part_name]["region_info"][region_id]["points"])
            else:
                part_assembly_points = set(self.part_info[target_part_name]["assembly_points"].keys())
            part_assembly_points -= used_assembly_points
            part_assembly_points = list(part_assembly_points)
            
            part_id_0 = used_assembly_instance.index(target_part_instance)
            part_name_0 = target_part_name
            assembly_points_0 = part_assembly_points

            assert len(assembly_points_0) > assembly_num 
            
            for connector_instance in used_connector_instance:
                part_id_1 = used_assembly_instance.index(connector_instance)
                part_name_1 = connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())

                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num)
            one_possible_sequence = list(random.choice(possible_sequences))
            group_assembly_sequence += one_possible_sequence

            #endregion
        
            #region assemble group + group(connector)
            group_info = group_info_list[1]           
            group_id = group_info["id"]
            target_part_instance = group_info["part_instance"]
            
            target_part_name = target_part_instance["part_name"]
            target_part_instance_id = target_part_instance["instance_id"]
            target_part_instance_status = self.part_instance_status[target_part_name][target_part_instance_id]

            used_assembly_points = set(target_part_instance_status["used_assembly_points"].keys())
            region_id = group_info["region"]
            if region_id:
                part_assembly_points = set(self.part_info[target_part_name]["region_info"][region_id]["points"])
            else:
                part_assembly_points = set(self.part_info[target_part_name]["assembly_points"].keys())
            part_assembly_points -= used_assembly_points
            part_assembly_points = list(part_assembly_points)
            
            part_id_0 = used_assembly_instance.index(target_part_instance)
            part_name_0 = target_part_name
            assembly_points_0 = part_assembly_points

            assert len(assembly_points_0) > assembly_num 
            
            for connector_instance in used_connector_instance:
                part_id_1 = used_assembly_instance.index(connector_instance)
                part_name_1 = connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())

                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num, 
                                                            group_condition=group_assembly_sequence)
            one_possible_sequence = list(random.choice(possible_sequences))#TODO: get one possible sequence
            group_assembly_sequence += one_possible_sequence
            #endregion

        else:
            assert False
        previous_pair_list = self.assembly_info["assembly"]
        previous_idx = len(previous_pair_list)
        previous_pair_list += available_pair
        group_assembly_sequence = list(np.array(group_assembly_sequence) + previous_idx) 

        return group_assembly_sequence
    def _extract_sequence_from_connection_assembly(self, connection_assembly):
        """connection_assembly = {
            "assembly_type": AssemblyType.group_connector,
            "component": {
                "group": [
                    {
                        "id": 1,
                        "assembly_point":{
                            "part_name": "ikea_stefan_long",
                            "instance_id": 0,
                            "point_idx": 0,
                        },
                    },
                ],
                "connector": 1,
            }
        }"""
        used_assembly_instance = self.assembly_info["part"]
        assembly_component = connection_assembly["component"]
        assembly_type = connection_assembly["assembly_type"]
        
        # connector instance
        connctor_id = assembly_component["connector"]
        connector_name = self.connector_info[connctor_id]["part_name"]

        used_connector_instance = None
        count = 0
        connector_instance_info = self.part_instance_status[connector_name]
        for instance_idx in connector_instance_info.keys():
            connector_instance = {
                "part_name": connector_name,
                "instance_id": instance_idx
            }
            is_in_group = not (connector_instance_info[instance_idx]["group_id"] == None)
            if is_in_group or (connector_instance in used_assembly_instance):
                continue
            used_connector_instance = connector_instance
            used_assembly_instance.append(connector_instance)
            break
        assert used_connector_instance
        
        group_info_list = assembly_component["group"] # list of used_group info
        
        group_assembly_sequence = []
        if len(group_info_list) == 1:
            """group + connector
            """
            group_info = group_info_list[0]
            group_id = group_info["id"]
            assembly_info = group_info["assembly_point"]
            available_pair = []
            if assembly_info == None:
                # find available part
                available_parts = []
                composed_parts = self.group_status[group_id]["composed_part"]
                for part_instance in composed_parts:
                    part_name = part_instance["part_name"]
                    instance_id = part_instance["instance_id"]
                    part_status = self.part_instance_status[part_name][instance_id]
                    if part_status["available_assembly"][connector_name] > 0:
                        used_point = set(part_status["used_assembly_points"].keys())
                        all_points = set(self.part_info[part_name]["assembly_points"].keys())
                        available_parts.append({
                            "part_instance": part_instance,
                            "available_points": list(all_points - used_point)
                        })
                for available_part in available_parts:
                    target_part_instance = available_part["part_instance"]
                    part_id_0 = used_assembly_instance.index(target_part_instance)
                    part_name_0 = target_part_instance["part_name"]
                    assembly_points_0 = available_part["available_points"]

                    part_id_1 = used_assembly_instance.index(used_connector_instance)
                    part_name_1 = used_connector_instance["part_name"]
                    assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                    available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
                
            else:
                target_part_name = assembly_info["part_name"]
                target_part_instance_id = assembly_info["instance_id"]

                target_part_instance = {
                    "part_name": target_part_name,
                    "instance_id": target_part_instance_id
                }
                part_id_0 = used_assembly_instance.index(target_part_instance)
                part_name_0 = target_part_instance["part_name"]
                assembly_points_0 = [assembly_info["point_id"]]

                part_id_1 = used_assembly_instance.index(used_connector_instance)
                part_name_1 = used_connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num=1)
            one_possible_sequence = list(random.choice(possible_sequences))
            group_assembly_sequence += one_possible_sequence

        elif len(group_info_list) == 2 and assembly_type == AssemblyType.group_connector_group:
            #region group + connector
            group_info = group_info_list[0]
            group_id = group_info["id"]
            assembly_info = group_info["assembly_point"]
            available_pair = []
            if assembly_info == None:
                # find available part
                available_parts = []
                composed_parts = self.group_status[group_id]["composed_part"]
                for part_instance in composed_parts:
                    part_name = part_instance["part_name"]
                    instance_id = part_instance["instance_id"]
                    part_status = self.part_instance_status[part_name][instance_id]
                    if part_status["available_assembly"][connector_name] > 0:
                        used_point = set(part_status["used_assembly_points"].keys())
                        all_points = set(self.part_info[part_name]["assembly_points"].keys())
                        available_parts.append({
                            "part_instance": part_instance,
                            "available_points": list(all_points - used_point)
                        })
                for available_part in available_parts:
                    target_part_instance = available_part["part_instance"]
                    part_id_0 = used_assembly_instance.index(target_part_instance)
                    part_name_0 = target_part_instance["part_name"]
                    assembly_points_0 = available_part["available_points"]

                    part_id_1 = used_assembly_instance.index(used_connector_instance)
                    part_name_1 = used_connector_instance["part_name"]
                    assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                    available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
                
            else:
                target_part_name = assembly_info["part_name"]
                target_part_instance_id = assembly_info["instance_id"]

                target_part_instance = {
                    "part_name": target_part_name,
                    "instance_id": target_part_instance_id
                }
                part_id_0 = used_assembly_instance.index(target_part_instance)
                part_name_0 = target_part_instance["part_name"]
                assembly_points_0 = [assembly_info["point_id"]]

                part_id_1 = used_assembly_instance.index(used_connector_instance)
                part_name_1 = used_connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num=1)
            one_possible_sequence = list(random.choice(possible_sequences))
            group_assembly_sequence += one_possible_sequence

            #endregion
            
            #region assemble group + group(connector)
            group_info = group_info_list[1]
            group_id = group_info["id"]
            assembly_info = group_info["assembly_point"]
            if assembly_info == None:
                # find available part
                available_parts = []
                composed_parts = self.group_status[group_id]["composed_part"]
                for part_instance in composed_parts:
                    part_name = part_instance["part_name"]
                    instance_id = part_instance["instance_id"]
                    part_status = self.part_instance_status[part_name][instance_id]
                    if part_status["available_assembly"][connector_name] > 0:
                        used_point = set(part_status["used_assembly_points"].keys())
                        all_points = set(self.part_info[part_name]["assembly_points"].keys())
                        available_parts.append({
                            "part_instance": part_instance,
                            "available_points": list(all_points - used_point)
                        })
                for available_part in available_parts:
                    target_part_instance = available_part["part_instance"]
                    part_id_0 = used_assembly_instance.index(target_part_instance)
                    part_name_0 = target_part_instance["part_name"]
                    assembly_points_0 = available_part["available_points"]

                    part_id_1 = used_assembly_instance.index(used_connector_instance)
                    part_name_1 = used_connector_instance["part_name"]
                    assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                    available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
                
            else:
                target_part_name = assembly_info["part_name"]
                target_part_instance_id = assembly_info["instance_id"]

                target_part_instance = {
                    "part_name": target_part_name,
                    "instance_id": target_part_instance_id
                }
                part_id_0 = used_assembly_instance.index(target_part_instance)
                part_name_0 = target_part_instance["part_name"]
                assembly_points_0 = [assembly_info["point_id"]]

                part_id_1 = used_assembly_instance.index(used_connector_instance)
                part_name_1 = used_connector_instance["part_name"]
                assembly_points_1 = list(self.part_info[part_name_1]["assembly_points"].keys())
                available_pair += self._get_available_assembly_pairs(part_id_0=part_id_0,
                                                                    part_name_0=part_name_0,
                                                                    assembly_points_0=assembly_points_0,
                                                                    part_id_1=part_id_1,
                                                                    part_name_1=part_name_1,
                                                                    assembly_points_1=assembly_points_1)
            
            possible_sequences = self._get_available_sequence(available_pair, assembly_num=1,
                                                            group_condition=group_assembly_sequence)
            one_possible_sequence = list(random.choice(possible_sequences))
            group_assembly_sequence += one_possible_sequence
            
            #endregion

        else:
            assert False
        
        previous_pair_list = self.assembly_info["assembly"]
        previous_idx = len(previous_pair_list)
        previous_pair_list += available_pair
        group_assembly_sequence = list(np.array(group_assembly_sequence) + previous_idx)

        return group_assembly_sequence
    def _get_available_assembly_pairs(self, part_id_0, part_name_0, assembly_points_0, 
                                            part_id_1, part_name_1, assembly_points_1):
        assert self.assembly_pair
        available_assembly = []
        part_0_info = self.assembly_pair[part_name_0]
        for assembly_point_idx_0 in assembly_points_0:
            availabe_pair_list = part_0_info[assembly_point_idx_0]
            for pair_info in availabe_pair_list:
                if pair_info["part_name"]==part_name_1\
                    and pair_info["assembly_point"] in assembly_points_1:
                    assembly_pair_info = {
                        "method":{
                            "direction": pair_info["direction"],
                            "offset": pair_info["offset"],
                            "additional": pair_info["additional"]
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
        """get all possible sequence from current part and pair
        - using rule is one point is used once
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
        # check condition
        condition_used_point = []
        
        global_pairs = self.assembly_info["assembly"]
        global_condition = self.assembly_info["assembly_sequence"]
        for pair_idx in global_condition:
            target_assembly_pair = global_pairs[pair_idx]
            target_pair = target_assembly_pair["target_pair"]
            for idx in target_pair.keys():
                point = target_pair[idx]
                condition_used_point.append(point)
        
        local_condition = group_condition
        for pair_idx in local_condition:
            target_assembly_pair = assembly_pairs[pair_idx]
            target_pair = target_assembly_pair["target_pair"]
            for idx in target_pair.keys():
                point = target_pair[idx]
                condition_used_point.append(point)
        # check sequence
        for sequence in all_possible_sequence:
            used_point = copy.deepcopy(condition_used_point) # point == {assembly point, part_id}
            is_possible = True
            for pair_idx in sequence:
                target_assembly_pair = assembly_pairs[pair_idx]
                target_pair = target_assembly_pair["target_pair"]
                for idx in target_pair.keys():
                    point = target_pair[idx]
                    if point in used_point:
                        is_possible = False
                        break
                    else:
                        used_point.append(point)
                if not is_possible:
                    break
            if not is_possible:
                impossible_sequence.append(sequence)
        possible_sequence = list(all_possible_sequence - set(impossible_sequence))

        return possible_sequence

    def simulate_instruction_step(self):
        assert self.assembly_info["assembly_sequence"]

        assembly_sequences = [self.assembly_info["assembly_sequence"]]
        
        assert len(assembly_sequences) == 1, "Not Implemented for multi case"
        for assembly_sequence in assembly_sequences:
            is_possible = self._simulate_assembly_sequecne(assembly_sequence)
            assert is_possible, "Not Implemented for fail to assembly"
            break
    def _simulate_assembly_sequecne(self, assembly_sequence):
        assembly_pairs = self.assembly_info["assembly"]

        sequence_part_status = copy.deepcopy(self.part_instance_status)
        sequence_group_status = copy.deepcopy(self.group_status)

        for pair_id in assembly_sequence:
            pair_assembly_info = assembly_pairs[pair_id]
            target_assembly_info = self._get_target_assembly_info(pair_assembly_info=pair_assembly_info,
                                                                    current_part_status=sequence_part_status,
                                                                    current_group_status=sequence_group_status)

            target_pair = target_assembly_info["target"]["target_pair"]
            current_status = target_assembly_info["status"]
            self.logger.info("""...Waiting for simulate assemble:
                {}_{} and {}_{}""".format(target_pair[0]["part_name"],
                                        target_pair[0]["instance_id"],
                                        target_pair[1]["part_name"],
                                        target_pair[1]["instance_id"]))
            is_possible = False
            try:
                is_possible = self.socket_module.check_assembly_possibility(target_assembly_info)
            except:
                self.logger.info("ERROR!")

            if not is_possible:
                return False

            # update local status
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
            new_status = current_status + [target_assembly_info["target"]]

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
        if not group_id_0 == group_id_1:
            if not group_id_0 == None:
                current_assembly_status += current_group_status[group_id_0]["status"]
            if not group_id_1 == None:
                current_assembly_status += current_group_status[group_id_1]["status"]
        else:
            assert group_id_0 and group_id_1, "connector + connector?"
            current_assembly_status = current_group_status[group_id_0]["status"]

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
            "status": current_assembly_status
        }

        return target_assembly_info
    


    #region test function
    def test_search_sequence(self):
        new_seq = []
        sequence = seq["sequence_{}".format(self.current_step)]
        if self.current_step == 5:
            print()
        for pair in sequence:
            target_pair = {}
            for pair_idx in pair.keys():
                part_info = pair[pair_idx]
                part_name = part_info["part_name"]
                instance_id = part_info["instance_id"]
                point_idx = part_info["assembly_point"]
                part_key = {
                    "part_name": part_name,
                    "instance_id": instance_id
                }
                part_id = None
                for idx in self.assembly_info["part"].keys():
                    if self.assembly_info["part"][idx] == part_key:
                        part_id = idx
                        break
                target_pair[pair_idx] = {
                    "assembly_point": point_idx,
                    "part_id": part_id
                }
            asm_idx = None
            for idx in self.assembly_info["assembly"].keys():
                if self.assembly_info["assembly"][idx]["target_pair"] == target_pair:
                    asm_idx = idx
                    break
            new_seq.append(asm_idx)
        assert new_seq
        self.assembly_info["assembly_sequence"].append(new_seq)
    
    #endregion