from script.const import PartType, AssemblyType, AssemblyPair
from script.fileApi import *
from enum import Enum
from socket_module import SocketModule

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
        
        self.socket_module = SocketModule()
        
        # 내부에서 사용하는 데이터(저장은 선택)
        self.part_info_path = join(self.assembly_path, "part_info.yaml")
        self.assembly_pair_path = join(self.assembly_path, "assembly_pair.yaml")
        self.refined_pair_path = "./assembly_pair_refined.yaml"
        
        self.part_info = None
        self.assemlby_pair = None
        self.furniture_parts, self.connector_parts = [], [] # save part_name

        # 매 스탭 마다 바뀌는 정보
        self.current_step = 0
        self.group_info = None
        self.group_info_path = join(self.group_info_root, "group_info_{}.yaml".format(self.current_step))
        self.instruction_info = None
        
        # 조립 마다 바뀌는 정보
        self.part_instance_status = {}
        self.group_status = {}

        self.using_part = {} # 현재 단계에서 조립에 사용되는 파트 인스턴스

        '''
        self.assembly_pairs = self.get_assembly_pairs()
        self.FC_module.assemble_pair_test(self.assembly_pairs["pair"])

        self.initialize_group_info()
        self.initialize_connector_info()
        self.instance_info = {}
        self.instance_info_path = join(self.assembly_path, "intance_info.yaml")
        '''
    
    def initialize_CAD_info(self):
        self.part_info = self.socket_module.initialize_cad_info(self.cad_path)
        save_dic_to_yaml(self.part_info, self.part_info_path)
        # self.part_info = load_yaml_to_dic(self.part_info_path)

        # self._initialize_assembly_pair()
        # save_dic_to_yaml(self.assembly_pair, self.assembly_pair_path)
        self.assembly_pair = load_yaml_to_dic(self.refined_pair_path)

        self._initialize_part_instance_status()
        self._initialize_each_parts()
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
                    # "group_id": 0
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

    def _initialize_group_status(self):
        # furniture part 를 베이스로 하여 그룹을 생성
        for group_id, part_name in enumerate(self.furniture_parts):
            group_status = {
                "composed_part": [{
                    "part_name": part_name,
                    "instance_id": 0
                }],
                "status": []
            }
            self.group_status[group_id] = group_status
        # save_dic_to_yaml(self.group_status, "example_group_status.yaml")

    def update_group_info(self):
        # update group info using group status
        group_info = {}
        for group_id in self.group_status.keys():
            obj_root = join(self.group_obj_path, "group_{}".format(group_id))
            check_and_create_dir(obj_root)
            group_status = self.group_status[group_id]
            self.socket_module.extract_group_obj(group_status, obj_root)
            group_info[group_id] = {
                "obj_file": join(obj_root, "base.obj"),
                "obj_root": obj_root,
                "composed_group": [group_id]
            }
        self.group_info = group_info
        self.group_info_path = join(self.group_info_root, "group_info_{}.yaml".format(self.current_step))
        save_dic_to_yaml(self.group_info, self.group_info_path)
        
    def get_instruction_info(self):
        self.logger.info("... wating for instruction of [step {}]".format(self.current_step))
        self.instruction_info = self.socket_module.get_instruction_info(self.group_info)
        self.logger.info("Get instruction of [step {}] information !".format(self.current_step))
    
    #############################################################완료선
    
    def extract_assembly_info(self):
        """ extract assembly information including assembly regions
                1. 현재 step의 instruction에 인식된 group -> instances를 인식 (이전 status 정보 참조)
                2. for each group instances, select all target assembly regions
                3. count which assembly regions has to be assembled with connenctor
        Input:
            instruction_info 
            조립에 사용되는 group들과 connection lines
            [type]: dict
        Returns:
            assembly_region_info
            어떤 assembly region끼리 어떤 connenctor로 몇번 결합하는지
            assembly region와 connenctor를 조립되는 순서로 key
            [type]: dict
            key: AssemblyRegion_ConnectorID_AssemblyRegion
            value: the number of count 
        """
    
        # 1. select group instances
        # 이전 status에서 instruction의 instance id를 group의 instance id와 매칭
        # 새로 나온 group이면 instance id 0부터 추가
        # 기존에 있던 group일 경우, connector 정보를 바탕으로 매칭
        used_groups = self.instruction_info['Group']
        connectors = self.instruction_info['Connector']
        for used_group_info in used_groups:
            group_id = group_info["group_id"]
            group_status = self.group_status[group_id]


            pose = group_info["pose"]
            

            connector = group_info["connector"]
            

        

        self.instance_Instruction_to_Group = {}
        for group in groups:
            InstanceInstruction = group["instance_id"]

            group_id = group["group_id"]
            connectorInstruction = group["connector"]
            InstanceGroup = self.find_group_instance_id(group_id, connectorInstruction)

            self.instance_Instruction_to_Group[InstanceInstruction] = {"group": group_id,
                                                                       "instnace_id": InstanceGroup}
        

        # 2. find assembly regions
        # connection lines로 표현된 assembly info를 assembly region 단위로 변환
        # assembly region과 결합하는 connector를 Assembly_g#_c#_g# 단위로 count
        assembly_region_info = {}
        connections = self.instruction_info['Connection']['connections']
        for connection in connections:
            components = connection["components"]
            components = self.set_order_connenction(components)
            key = 'Assembly'
            for component in components:
                if component['type'] == 'group':
                    group_id = component['id']
                    connection_point = component['connect_point']
                    assembly_region_id = self.find_assembly_region_id(group_id, connection_point)
                    key += '_g{}'.format(assembly_region_id)
                else:
                    key += '_c{}'.format(component['id'])
            if key not in assembly_region_info:
                assembly_region_info[key] = 0    
            assembly_region_info[key] += 1

        # rename assembly region keys
        # 같은 g-c-g / g-g-c의 count 합치기
        # g-c / c-g는 g-c 순서로 sorting
        self.assembly_region_info = self.set_order_assembly_region(assembly_region_info)

    

    def search_assemble_sequences(self):
        """ 가능한 Assembly sequence를 탐색
            1. Group-Connector를 우선 조립 후, 남은 Group-Connector-Group를 조립
            2. Assembly region안에서 결합이 가능한 Assembly pair를 바탕으로 경우의 수 탐색
            3. 중복된 sequence 병합

        Input:
            assembly_region_info
        Returns:
            assembly_region_info
            [type]: dict
        """

        # group-connector와 group-group 분리
        assemble_connector = []
        assemble_group = []
        for assemble in self.assembly_region_info:
            components = assemble.split('_')[1:]
            component_summary = [c[0] for c in components]
            component_summary = '_'.join(component_summary)
            if component_summary == 'g_c':
                assemble_connector.append(assemble)
            elif component_summary in ['g_c_g', 'c_g_g']:
                assemble_group.append(assemble)
    
        # group-connector 결합 수행
        for assemble in assemble_connector:
            _, assembly_region, connector = assemble.split('_')
            assembly_region = assembly_region[1:]
            connector = connector[1:]
            num_assemble = self.assembly_region_info[assemble]
            print(assemble, assembly_region, connector, num_assemble)
            
            #TODO Raeyo, Joosoon: Assembly search input-output format 정하기
            assemblies = self.request_assemble_search(assembly_region, connector, num_assemble)
        quit()

    def simulate_instruction_step(self):
        pass

    def check_hidden_assembly(self):
        pass

    def update_group_status(self):
        pass

    def step(self):
        self.current_step += 1
        self.instruction_info = None

    #############################################################
    def initialize_connector_info(self):
        connector_info = {}
        for connector_id, part_name in enumerate(self.connector_parts):
            doc_path = self.part_info[part_name]["document"]
            connector_name = part_name
            connector_info[connector_name] = {
                "connector_id": connector_id,
                "quantity": 0,
            }
        self.connector_info = connector_info
        connector_info_path = join(self.assembly_path, "connector_info.yaml")
        save_dic_to_yaml(self.connector_info, connector_info_path)

    def initialize_status(self):
        #TODO: for assembly sequence
        pass

    def check_instruction_info(self):
        self.logger.info("wating for instruction {}...".format(self.current_step))
        
        current_instrution = "instruction_" + str(self.current_step) + ".yaml"
        current_instrution_path = join(self.instruction_path, current_instrution)
        if os.path.isfile(current_instrution_path):
            self.logger.info("Get instruction {} information!".format(self.current_step))
            self.instruction_info = load_yaml_to_dic(current_instrution_path)
            return True
        else:
            return False    
    
    def is_exist_instance(self, args=None):
        #TODO(js):
        is_exist = False

        return is_exist
    
    def create_new_instance(self, part_name):
        # 1. Define instance name
        count = 0
        instance_name = part_name + "_" + str(count)
        while instance_name in self.instance_info.keys():
            count += 1
            instance_name = part_name + "_" + str(count)
        # 2. Create assembly document
        part_info = self.part_info[part_name]
        part_doc = part_info["document"]
        self.instance_info[instance_name] = {
            "assembly_document": part_doc,
            "part_name": part_name,
            "used_points": [],
        }
        self.status[instance_name] = {}

    def group_to_instance(self):
        #TODO(js): group info -> instance info
        used_group_info = self.instruction_info["Group"] # list of used group info
        for group_info in used_group_info:
            group_pose = group_info["pose"]
            group_id = group_info["group_id"]    
            if self.is_exist_instance():
                pass
            else:
                self.create_new_instance(group_name)

    def group_to_instance_test(self):
        # for instruction_1
        """
        # furniture part (from group_info)
        id: 1 "ikea_stefan_long"
        id: 3 "ikea_stefan_short"
        id: 4 "ikea_stefan_side_left"
        id: 2 "ikea_stefan_middle"
        
        # connector part (from connector info)
        id: 2 "ikea_wood_pin(14ea)"
        """
        used_group = [self.furniture_parts[1], self.furniture_parts[3], self.furniture_parts[4], self.furniture_parts[2]]
        used_connector = [(self.connector_parts[2], 14)]
        for part_name in used_group:
            self.create_new_instance(part_name)
        for part_name, num in used_connector:
            for i in range(num):
                self.create_new_instance(part_name)

    def get_instruction_assembly_sequence(self):
        #TODO(js)
        pass

    def get_instruction_assembly_test(self):

        assemblies = [
            {
                "assembly_type": AssemblyType.group_connector_group,
                "assembly_parts": ["ikea_stefan_side_left_0", ("ikea_wood_pin(14ea)", 2), "ikea_stefan_short_0"]
            },
            {
                "assembly_type": AssemblyType.group_connector_group,
                "assembly_parts": ["ikea_stefan_side_left_0", ("ikea_wood_pin(14ea)", 2), "ikea_stefan_long_0"]
            },
            {
                "assembly_type": AssemblyType.group_connector_group,
                "assembly_parts": ["ikea_stefan_side_left_0", ("ikea_wood_pin(14ea)", 3), "ikea_stefan_middle_0"]
            },
            #TODO: group_connector type assembly
        ]
        return assemblies

    def simulate_instruction_step(self):
        """
        #TODO(js):
        1. group info -> instance info
        2. get group assembly(connection) sequence from instruction
        3. assemble with region pair
        """
        self.group_to_instance_test()
        for key in self.instance_info.keys():
            print(key, self.instance_info[key])
        save_dic_to_yaml(self.instance_info, self.instance_info_path)
        assemblies = self.get_instruction_assembly_test()
        for assembly in assemblies:
            assemble_type = assembly["assembly_type"]
            if assemble_type == AssemblyType.group_connector_group:
                self.simulate_group_assembly(assembly)
            elif assemble_type == AssemblyType.group_connector:
                self.simulate_connector_assembly(assembly)
        self.FC_module.assemble_A_and_B(self.instance_info["ikea_stefan_long_0"],
                                        self.instance_info["ikea_stefan_side_left_0"])
        pass

    def simulate_group_assembly(self, assembly):
        assemble_parts = assembly["assembly_parts"]
        group1 = assemble_parts[0] # instance name
        group2 = assemble_parts[2] # instance name
        
        connector_name, connector_num = assemble_parts[1] # part name 
        connecotr_instances = [] # -> instance name
        count = 0
        instance_name = connector_name + "_" + str(count)
        for i in range(connector_num):
            while instance_name in self.status.keys():
                count += 1
                instance_name = connector_name + "_" + str(count)
            connecotr_instances.append(instance_name)
        pass
        # 1. assemble connector to group 1 - region x
        # 2. assemble group 1(assembled with connector) - region x with group 2

    def simulate_connector_assembly(self, assembly):
        print(assembly)

    def step(self):
        self.current_step += 1


    ##########################################################
    def find_group_instance_id(self, group_id, connector_info):
        if group_id not in self.instance_info:
            self.instance_info[group_id] = {
                                            "instance_id": 0,
                                            "connector": connector_info
                                            }
            instance_id = 0
        else:
            #TODO: joosoon, connector 정보를 바탕으로 group instance 매칭하기
            pass
        return instance_id

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

    