from script.fileApi import *
from external_module import freecad_module, pyrep_module
# test for branch

class AssemblyManager(object):
    """ 
    Functions
        1. Initialize furniture part CAD info.
        2. Get instruction info and extract assembly info
        3. Assemble parts with assembly region
        4. Create assembly sequence
    """
    def __init__(self, logger, furniture_name, instruction_root="./instruction", assembly_root='./assembly'):
        self.logger = logger
        self.furniture_name = furniture_name
        self.assembly_root = assembly_root

        # external module for assembly (FreeCAD, Pyrep)
        #TODO: 래영이한테 컨펌
        self.FC_module = freecad_module
        self.PR_module = pyrep_module
        self.assembly_region_ids = {}   # assembly region을 임시로 지정하기 위함 dict
        
        self.group_info_path = join(assembly_root, self.furniture_name, 'group_info')
        self.group_instance_info_path = join(assembly_root, self.furniture_name, 'group_instance_info')
        self.instruction_path = join(instruction_root, self.furniture_name)
        self.is_end = False

        # initialize instruction info for each step
        self.current_step = 1
        self.instruction_info = None
        self.assembly_info = None

        # PDDL


            

    def initialize_CAD_info(self):
        part_info_path = join(self.assembly_root, self.furniture_name, "part_info.yaml")
        if check_file(part_info_path):
            self.part_info = load_yaml_to_dic(part_info_path)
        else:
            #TODO: use freecad module to extract info
            self.part_info = load_yaml_to_dic(part_info_path)

    def check_instruction_info(self):
        """ check instruction information of current step
            return True when both .yaml and .txt files are exist
        """

        self.logger.info("... wating for instruction of [step {}]".format(self.current_step))

        current_instrution = "instruction_{}.yaml".format(self.current_step)
        current_instrution_path = join(self.instruction_path, current_instrution)

        current_checkfile = "instruction_{}.txt".format(self.current_step)
        current_checkfile_path = join(self.instruction_path, current_checkfile)
        
        if os.path.isfile(current_instrution_path) and os.path.isfile(current_checkfile_path):
            self.logger.info("Get instruction of [step {}] information !".format(self.current_step))
            self.instruction_info = load_yaml_to_dic(current_instrution_path)

            instance_info = join(self.group_instance_info_path, "group_instnace_info_{}.yaml".format(self.current_step-1))
            self.instance_info = load_yaml_to_dic(instance_info)
            if self.instance_info is None:
                self.instance_info = {}
            return True
        else:
            return False



    def extract_assembly_info(self):
        """ extract assembly information including assembly regions
                1. 현재 step의 instruction에 인식된 group의 instances를 인식 (이전 status 정보 참조)
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

        self.instance_Instruction_to_Group = {}
        groups = self.instruction_info['Group']
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

        # group-connector결합과 group-group결합을 분리
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

        # group-group 결합 수행

        # 중복 sequence 병합





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

    def simulate_instruction_step(self):
        pass

    def check_hidden_assembly(self):
        pass

    def update_group_status(self):
        pass

    def step(self):
        self.current_step = 1
        self.instruction_info = None
        self.is_end = True
