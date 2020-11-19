from script.const import PartType, AssemblyType, AssemblyPair
from script.fileApi import *
from enum import Enum
from socket_module import SocketModule
from pyprnt import prnt
import copy

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
        self.whole_assembly_info = None

        # 조립 마다 바뀌는 정보
        self.part_instance_status = {}
        self.group_status = {}

    def initialize_CAD_info(self):
        self.logger.info("...Waiting for cad info from FreeCAD Module")
        self.part_info = self.socket_module.initialize_cad_info(self.cad_path)
        # self.part_info = load_yaml_to_dic(self.part_info_path)
        # self._initialize_assembly_pair()
        # save_dic_to_yaml(self.assembly_pair, self.assembly_pair_path)
        self.assembly_pair = load_yaml_to_dic(self.refined_pair_path)

        self._initialize_part_instance_status()
        self._initialize_each_parts()
        self._initialize_connector_info()            
        self._initialize_group_status()

    def _initialize_assembly_pair(self):
        """part info 를 바탕으로 가능한 모든 assembly pairs 를 출력
        """
        assert False, "Not use this function! load refined file instead"
        radius_group = {
            "pin group": [0, 1, 7, 9, 10, 11, 12, 13],
            "braket group": [5, 6, 8],
            "flat_penet group": [2, 3, 4, 14],
            "pan": [15]
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
                            offset = 0
                            if get_group(point_1["radius"]) == "pin group":
                                offset = -15 # 0.015
                            target = {
                                "part_name": part_name_2,
                                "assembly_point": point_idx_2,
                                "direction": "aligned",
                                "offset": offset
                            }
                            assembly_pairs[part_name_1][point_idx_1].append(target)
        
        self.assembly_pair =  assembly_pairs
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
            try:
                quantity = part_instance_quantity[part_name]
            except:
                quantity = 1
            for i in range(quantity):
                part_instance_status[part_name][i] = {
                    "used_assembly_points": [],
                    "group_id": None
                }

        self.part_instance_status = part_instance_status
        # save_dic_to_yaml(self.part_instance_status, "example_part_instance_status.yaml")
    def _initialize_each_parts(self):
        for part_name in self.part_info.keys():
            if self.part_info[part_name]["type"] == PartType.furniture.value:
                self.furniture_parts.append(part_name)
            elif self.part_info[part_name]["type"] == PartType.connector.value:
                self.connector_parts.append(part_name)
            else:
                self.logger.error("type is not matching!")
                exit()
    def _initialize_connector_info(self):
        connector_info = {}
        for connector_id, connector_name in enumerate(self.connector_parts):
            connector_info[connector_id] = {
                "part_name": connector_name
            }
        self.connector_info = connector_info
        # save_dic_to_yaml(self.connector_info, "example_connector_info.yaml")
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
                "is_exist": True
            }
            self.part_instance_status[part_name][0]["group_id"] = group_id
            self.group_status[group_id] = group_status
        # save_dic_to_yaml(self.group_status, "example_group_status.yaml")
    
    def update_group_info(self):
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
            group_info[group_id] = {
                "obj_file": join(obj_root, "base.obj"),
                "obj_root": obj_root,
                "composed_group": composed_group,
                "is_exist": is_exist
            }
        self.group_info = group_info
        self.group_info_path = join(self.group_info_root, "group_info_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_info, self.group_info_path)
    
    def initialize_pyrep_scene(self):
        self.logger.info("...Waiting for initialize PyRep scene")
        self.socket_module.initialize_pyrep_scene(self.part_info, self.group_info)
        self.current_step = 1
    
    def initialize_instruction_scene(self):
        # what step?, group status
        pass

    def update_instruction_scene(self):
        # group status
        pass

    def get_instruction_info(self):
        self.logger.info("... wating for instruction of [step {}]".format(self.current_step))
        self.instruction_info = self.socket_module.get_instruction_info(self.current_step, self.group_info, self.connector_info)
        if self.instruction_info:
            self.logger.info("Get instruction of [step {}] information !".format(self.current_step))
            self.is_end = False
        else:
            self.logger.info("Instruction end!")
            self.is_end = True
            
    def extract_assembly_info(self):
        used_group_info = {} # => for group assembly
        used_part_instance = [] # => unique instances
        
        instruction_group_info = self.instruction_info['Group']
        for group_info in instruction_group_info:
            group_id = group_info["group_id"]
            used_group_pose = group_info["pose"]
            used_group_status = self.group_status[group_id]
            used_parts = used_group_status["composed_part"]
            for used_part in used_parts:
                part_name = used_part["part_name"]
                instance_id = used_part["instance_id"]
                used_part_info = {
                    "part_name": part_name,
                    "instance_id": instance_id,
                }
                used_part_instance.append(used_part_info)
            used_group_info[group_id] = {
                "status": used_group_status,
                "pose": used_group_pose
            }
        # add connector instance to used part
        used_connector_info = self.instruction_info["Connector"]
        for connector_info in used_connector_info:
            connector_id = connector_info["connector_id"]
            num = connector_info["number_of_connector"]
            connector_name = self.connector_info[connector_id]["part_name"]
            instance_info = self.part_instance_status[connector_name]
            count = 0
            assert count < num, "number of connector error {}".format(num)
            for instance_id in instance_info.keys():
                added_part = {
                    "part_name": connector_name,
                    "instance_id": instance_id,
                }
                if added_part in used_part_instance:
                    continue
                used_part_instance.append(added_part)
                count += 1
                if count == num:
                    break
                else:
                    continue
            assert count == num, "number of connector error: there is no enough {}".format(connector_name)
        
        # assembly pair 와 part_instance_status를 이용
        avaliable_pair = []

        for part_id, part_instance in enumerate(used_part_instance):
            # 각 part_instance에 대해 사용가능한 페어를 저장
            instance_name = part_instance["part_name"]
            instance_id = part_instance["instance_id"]
            instance_used_point = self.part_instance_status[instance_name][instance_id]["used_assembly_points"]

            instance_pairs = self.assembly_pair[instance_name]
            
            for point_idx in instance_pairs.keys():
                if point_idx in instance_used_point:
                    continue
                point_pair_list = instance_pairs[point_idx]
                for point_pair_info in point_pair_list:
                    pair_part_name = point_pair_info["part_name"]
                    pair_point = point_pair_info["assembly_point"]
                    direction = point_pair_info["direction"]
                    offset = point_pair_info["offset"]
                    # check avaliable point pair
                    for other_part_id, other_instance in enumerate(used_part_instance):
                        if other_part_id == part_id: # 같은 인스턴스 간 결합 제외
                            continue
                        if other_instance["part_name"] == pair_part_name: # 페어 가능한 인스턴스
                            other_instance_id = other_instance["instance_id"]
                            other_instance_used_point = self.part_instance_status[pair_part_name][other_instance_id]["used_assembly_points"]
                            if pair_point in other_instance_used_point:
                                continue
                            assembly_pair = [
                                    {
                                        "part_id": part_id,
                                        "assembly_point": point_idx
                                    },
                                    {
                                        "part_id": other_part_id,
                                        "assembly_point": pair_point
                                    }
                                ]
                            method = {
                                "direction": direction,
                                "offset": offset
                            }
                            if assembly_pair in avaliable_pair:
                                continue
                            assembly_pair.reverse()
                            if assembly_pair in avaliable_pair:
                                continue
                            assembly_pair.reverse()
                            pair_assembly_info = {
                                "target_pair": {
                                    0: assembly_pair[0],
                                    1: assembly_pair[1]
                                },
                                "method": method
                            }
                            avaliable_pair.append(pair_assembly_info)

        self.assembly_info = {}
        self.assembly_info["group_info"] = used_group_info
        self.assembly_info["part"] = {}
        self.assembly_info["assembly"] = {}
        self.assembly_info["assembly_sequence"] = []
        for idx, part in enumerate(used_part_instance):
            self.assembly_info["part"][idx] = part
        for idx, pair in enumerate(avaliable_pair):
            self.assembly_info["assembly"][idx] = pair
        # prnt(self.assembly_info)
        self.logger.info("Success to extract assembly info")

    def search_assemble_sequences(self):
        assert self.assembly_info
        available_assembly = self.assembly_info["assembly"]
        # All possible sequence => Too many sequences
        # TODO: using group pose to extract group assembly
        """
        1. group 1, pose 1, group 2, pose 2 => (region 1, region 2) * n using pyrep module
        2. group 1, region 1, group 2, region 2 => available pair
            case1. connector already assembled => TODO: region -> connector
            case2. connector have to assembled => (if None) -> assemble connector first(with region 1 or region 2)  -> case1
        3. 
        """
        #region extract all possible pair from "available_assembly"
        all_possible_pair_set = [] # list of list
        target_idx = 0
        while target_idx < len(available_assembly): # for all target in available assembly
            assembly_sequence = []
            used_point = []
            
            # add target pair to list
            target_assembly = available_assembly[target_idx]
            target_pair = target_assembly["target_pair"]
            assembly_sequence.append(target_idx)
            for idx in target_pair.keys():
                point = target_pair[idx]
                used_point.append(point)
            
            # search for nonconfilicting pair for target pair
            for assembly_idx in available_assembly.keys():
                assembly = available_assembly[assembly_idx]
                is_avaliable = True
                pair = assembly["target_pair"]
                for idx in pair.keys(): # 0, 1
                    point = pair[idx]
                    if point in used_point:
                        is_avaliable = False
                        break
                if not is_avaliable:
                    continue
                assembly_sequence.append(assembly_idx)
                
                for idx in pair.keys():
                    point = pair[idx]
                    used_point.append(point)
                
            # check assembly sequence in all possible pair set
            assembly_sequence.sort()
            target_idx += 1
            if assembly_sequence in all_possible_pair_set:
                continue
            else:
                all_possible_pair_set.append(assembly_sequence)
                self.assembly_info["assembly_sequence"].append(assembly_sequence)        
        #endregion
        
        save_dic_to_yaml(self.assembly_info, "example_assembly_info_{}.yaml".format(self.current_step))
        self.logger.info("Success to search assembly sequence")

    def simulate_instruction_step(self):
        assert self.assembly_info["assembly_sequence"]

        used_part_instance = self.assembly_info["part"]
        assembly_pairs = self.assembly_info["assembly"]
        # current "assembly_sequences" is like set of possible pair(using rule: 1 constraint / 1 assembly point)
        assembly_sequences = self.assembly_info["assembly_sequence"]
        
        #TODO: for all possible case
        for sequence_idx, sequence in enumerate(assembly_sequences):
            possible_sequence = []
            sequence_part_status = copy.deepcopy(self.part_instance_status)
            sequence_group_status = copy.deepcopy(self.group_status)

            for pair_id in sequence:
                #region create pair assembly info for assemble
                pair_assembly_info = assembly_pairs[pair_id]
                
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
                status_0 = sequence_part_status[part_name_0][part_instance_id_0]
                group_id_0 = status_0["group_id"]
                status_1 = sequence_part_status[part_name_1][part_instance_id_1]
                group_id_1 = status_1["group_id"]
                
                # 다른 그룹간 결합
                if not group_id_0 == group_id_1:
                    # 가구 부품 + 가구 부품 => 새 그룹
                    if group_id_0 in sequence_group_status.keys() and group_id_1 in sequence_group_status.keys():
                        new_group_id = len(sequence_group_status)
                    # 가구 부품 + 커넥터 => 가구 그룹 따라감
                    elif group_id_0 in sequence_group_status.keys():
                        new_group_id = group_id_0
                    elif group_id_1 in sequence_group_status.keys():
                        new_group_id = group_id_1
                    # 커넥터 + 커넥터 (있을 수 있나?)
                    else:
                        assert group_id_0 and group_id_1, "connector + connector?"
                        new_group_id = group_id_0
                    status = []
                    composed_part = []
                    if not group_id_0 == None:
                        status += sequence_group_status[group_id_0]["status"]
                        composed_part += sequence_group_status[group_id_0]["composed_part"]
                    if not group_id_1 == None:
                        status += sequence_group_status[group_id_1]["status"]
                        composed_part += sequence_group_status[group_id_1]["composed_part"]
                # 같은 그룹 간 결합                    
                else:
                    assert group_id_0 and group_id_1, "connector + connector?"
                    new_group_id = group_id_0
                    status = sequence_group_status[group_id_0]["status"]
                    composed_part = sequence_group_status[group_id_0]["composed_part"]
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
                    "status": status
                }
                is_possible = False
                self.logger.info("...Waiting for simulate assemble {}_{} and {}_{}".format(part_name_0,
                                                                                           part_instance_id_0,
                                                                                           part_name_1,
                                                                                           part_instance_id_1))
                try:
                    is_possible = self.socket_module.check_assembly_possibility(target_assembly_info)
                except:
                    self.logger.info("ERROR!")
                #endregion
                #region update status
                if is_possible:
                    self.logger.info("success to assemble {}_{} and {}_{}".format(part_name_0,
                                                                                  part_instance_id_0,
                                                                                  part_name_1,
                                                                                  part_instance_id_1))
                    # group status
                    # 새로 그룹에 추가되는 파트에 대해 수행 group_id: None
                    if group_id_0 == None:
                        composed_part.append({
                            "part_name": part_name_0,
                            "instance_id": part_instance_id_0
                        })
                    # 사용된 그룹 없애기
                    elif not group_id_0 == new_group_id:
                        sequence_group_status[group_id_0]["is_exist"] = False
                    if group_id_1 == None:
                        composed_part.append({
                            "part_name": part_name_1,
                            "instance_id": part_instance_id_1
                        })
                    elif not group_id_1 == new_group_id:
                        sequence_group_status[group_id_1]["is_exist"] = False
                    
                    # part instance status
                    for part_instance in composed_part:
                        part_name = part_instance["part_name"]
                        instance_id = part_instance["instance_id"]
                        sequence_part_status[part_name][instance_id]["group_id"] = new_group_id
                        if part_name == part_name_0:
                            sequence_part_status[part_name][instance_id]["used_assembly_points"].append(assembly_point_0)
                        elif part_name == part_name_1:
                            sequence_part_status[part_name][instance_id]["used_assembly_points"].append(assembly_point_1)
                    # 결합 추가
                    status.append(target_assembly_info["target"])
                    # 구성 그룹 정보 변경
                    if new_group_id in sequence_group_status.keys():
                        composed_group = sequence_group_status[new_group_id]["composed_group"]
                    else: # 새로운 그룹 생성
                        composed_group = sequence_group_status[group_id_0]["composed_group"] \
                            + sequence_group_status[group_id_1]["composed_group"]
                    sequence_group_status[new_group_id] = {
                        "is_exist": True,
                        "composed_part": copy.deepcopy(composed_part),
                        "status": copy.deepcopy(status),
                        "composed_group": copy.deepcopy(composed_group) 
                    }
                    # sequence 
                    possible_sequence.append(pair_id)
                else:
                    # 현재 constraints 상으로 구현이 불가능한 조립
                    self.logger.info("Fail to assemble {}_{} and {}_{}".format(part_name_0,
                                                                               part_instance_id_0,
                                                                               part_name_1,
                                                                               part_instance_id_1))
                    continue
                #endregion
    
        # prnt(self.group_status)
        # prnt(self.assembly_info)
                        
    def check_hidden_assembly(self):
        pass

    def update_group_status(self):
        pass

    def step(self):
        self.update_group_info()
        
        self.get_instruction_info()

        save_dic_to_yaml(self.part_instance_status, "example_part_instance_status_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_status, "example_group_status_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_info, "example_group_info_{}.yaml".format(self.current_step))
        self.current_step += 1
        self.instruction_info = None

    ##########################################################
    def find_assembly_region_id(self, group_id, connection_point):
        #TODO: Rayeo, Pyrep 에서 assembly region 찾기
        x, y, z = connection_point["X"], connection_point["Y"], connection_point["Z"]
        key = "{}_{}_{}_{}".format(group_id, x, y, z)
        if key not in self.assembly_region_ids: 
            self.assembly_region_ids[key] = len(self.assembly_region_ids)
        return self.assembly_region_ids[key]

    def set_order_connenction(self, components):
        component_buff = {}
        for component in components:
            order = component['order']
            component_buff[order] = component
        order_component = []
        for i in range(len(component_buff)):
            order_component.append(component_buff[i])
        return order_component

    def set_order_assembly_region(self, assembly_region_info):
        rename_list = {}
        # 같은 g-c-g / g-g-c / c-g-g 의 count 합치기
        # g-g-c / c-g-g 는 c-g-g 순서로 sorting
        target_list = [k for k in assembly_region_info.keys() if len(k.split("_"))==4]
        for key in target_list:
            key_split = key.split("_")
            reversed_key = "_".join([key_split[0], key_split[3], key_split[2], key_split[1]])
            if key in rename_list:
                rename_list[key].append(key)
            elif reversed_key in rename_list:
                rename_list[reversed_key].append(key)
            else:
                component_summary = '{}_{}_{}'.format(key_split[1][0], key_split[2][0], key_split[3][0])
                if component_summary in ('g_c_g', 'c_g_c'):
                    main_key = key
                elif component_summary in ('c_g_g'):
                    main_key = reversed_key
                if main_key not in rename_list:
                    rename_list[main_key] = []
                rename_list[main_key].append(key)        

        # g-c / c-g는 g-c 순서로 sorting
        target_list = [k for k in assembly_region_info.keys() if len(k.split("_"))==3]
        for key in target_list:
            key_split = sorted(key.split("_")[1:])
            new_key = "Assembly_{}_{}".format(key_split[1], key_split[0])
            if new_key not in rename_list:
                rename_list[new_key] = []
            rename_list[new_key].append(key)

        # re-count
        assembly_region_info_sort = {}
        for new_key, keys in rename_list.items():
            assembly_region_info_sort[new_key] = 0
            for key in keys:
                assembly_region_info_sort[new_key] += assembly_region_info[key]
        return assembly_region_info_sort

    def request_assemble_search(self, assembly_region_id, connector_id, num_assemble):
        """ 주어진 assembly region에서 connenctor로 결합 가능한 assembly pair 찾기
            Input: 
                assembly_region_id: assembly region과 1대1 매핑
                connector_id: connector_info.yaml 의 connenctor_id
                num_assemble: 결합 횟수
            Return:
                포맷 정해야 함
        """
        #TODO Raeyo, Joosoon: Assembly search input-output format 정하기
        pass

        #     # extract assembly info 
