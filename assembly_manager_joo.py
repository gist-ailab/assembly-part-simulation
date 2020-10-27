from script.fileApi import *
from external_module import freecad_module, pyrep_module

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

        # external module for assembly (FreeCAD, Pyrep)
        #TODO: 래영이한테 컨펌
        self.FC_module = freecad_module
        self.PR_module = pyrep_module


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
        pass


    def check_instruction_info(self):
        """ check instruction information of current step
            return True whe both .yaml and .txt files are exist
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
                3. 
        Input:
            instruction_info 
            조립에 사용되는 group들과 connection lines
            [type]: dict
        Returns:
            assembly_region of each group
            조립에 사용하는 group instance,
            어떤 assembly region이 몇번 결합에 참여하는지
            [type]: dict
            pair: [assembly_region1, assembly_region1]
            assembly_region: 
        """
    
        # 1. select group instances
        # 이전 status에서 instruction의 instance id를 group의 instance id와 매칭
        # 새로 나온 group이면 instance id 0부터 추가
        # 기존에 있던 group일 경우, connector 정보를 바탕으로 매칭

        instance_Instruction_to_Group = {}
        groups = self.instruction_info['Group']
        for group in groups:
            InstanceInstruction = group["instance_id"]

            group_id = group["group_id"]
            connectorInstruction = group["connector"]
            InstanceGroup = self.find_group_instance_id(group_id, connectorInstruction)

            instance_Instruction_to_Group[InstanceInstruction] = {"group": group_id,
                                                                  "instnace_id": InstanceGroup}
        

        # 2. find assembly regions
        # connection lines로 표현된 assembly info를 assembly region 단위로 변환
        assembly_region_info = {}        
        self.assembly_region_ids = {}
        connections = self.instruction_info['Connection']['connections']
        for connection in connections:
            components = connection["components"]
            for component in components:
                if component['type'] != 'group': continue
                group_id = component['id']
                connection_point = component['connect_point']
                assembly_region_id = self.find_assembly_region_id(group_id, connection_point)
                if assembly_region_id not in assembly_region_info:
                    assembly_region_info[assembly_region_id] = 0
                assembly_region_info[assembly_region_id] += 1
        print(assembly_region_info)
        quit()

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
        #TODO: Rayeo, 블랜더에서 assembly region 찾기
        x, y, z = connection_point["X"], connection_point["Y"], connection_point["Z"]
        key = "{}_{}_{}_{}".format(group_id, x, y, z)
        if key not in self.assembly_region_ids: 
            self.assembly_region_ids[key] = len(self.assembly_region_ids)
        return self.assembly_region_ids[key]



    def set_order_connection_components(self, components):
        print(components)
        if len(components) == 2:
            ordered_components = {}
            for component in components:
                _type = component["type"]
                ordered_components[_type] = component
            ordered_components = [ordered_components]
        elif len(components) == 3:
            ordered_components = []
            types = [c['type'] for c in components]
            inst_ids = [c['instance_id'] for c in components if c['type']=="group"]

            orders = sorted([c['order'] for c in components])
            orders_info = {c['order']: c['type'] for c in components}

            curr_order = orders[0]
            while len(inst_ids) > 0:
                curr_type = orders_info[curr_order]
                target_type = orders_info[curr_order+1]
                next_type = orders_info[curr_order+2]
                # if target_type 

            print(types)
            print(inst_ids)
            print(orders)
            quit()

            connenct_component = [c for c in components if c['type']=="connector"][0]

        return ordered_components



    def search_assemble_sequences(self):
        pass


    def simulate_instruction_step(self):
        pass


    def update_group_status(self):
        pass


    def step(self):
        self.current_step = 1
        self.instruction_info = None
        self.is_end = True
