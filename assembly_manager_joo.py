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
            return True
        else:
            return False



    def extract_assembly_info(self):
        """ extract assembly information including assembly regions
                1. select group instances
                2. for each group instances, select all target assembly regions
                3. 
        Input:
            instruction_info 
            [type]: dict
        Returns:
            assembly_region of each group
            [type]: dict
            pair: [assembly_region1, assembly_region1]
            assembly_region: 
        """
        instance_info_instance = {}
        for group in self.instruction_info['Group']:
            instance_id = group["instance_id"]
            group_id = group["group_id"]
            instance_info_instance[instance_id] = {'group_id': group_id, "instance_id": instance_id}


        # select group instances
        # 이전 status에서 instruction의 instance id를 group의 instance id와 매칭
        instance_info_group = join(self.group_instance_info_path, "group_instnace_info_{}.yaml".format(self.current_step-1))
        instance_info_group = load_yaml_to_dic(instance_info_group)
        if instance_info_group is None: instance_info_group = {}

        inst_image2group = {}
        group_info = load_yaml_to_dic(self.instruction_info['group_info'])
        groups = self.instruction_info['Group']
        for group in groups:
            instance_id_instruction = group['instance_id']
            group_id = group['group_id']
            if group_id not in instance_info_group:
                instance_id_group = 0
                instance_info_group[group_id] = {}
                instance_info_group[group_id][instance_id_group] = {"instance_id" : instance_id_group,
                                                                    "obj_file": None,
                                                                    "connector": None}
            else:
                #TODO: search algorithm for group instances
                instance_id_group = instance_info[group_id]
            inst_image2group[instance_id_instruction] = instance_id_group
            instance_info_instance[instance_id_instruction]["group_instance_id"] = instance_id_group



        """ select assembly regions
            connection lines로 표현된 assembly info를 assembly region 단위로 변환
        """
        assembly_region_info = {}
        connections = self.instruction_info['Connection']['connections']
        for connection in connections:
            components = connection["components"]
            ordered_components = self.set_order_connection_components(components)

            print(ordered_components)
            continue
            
            for component in components:
                if component["type"] != 'group': continue
                print(component["type"], component['id'])
                group_id = component['id']
                region_id = self.PR_module.request_assembly_region(group_info=group_info[group_id], 
                                                                   target=component["connect_point"])
                connecntor_id = 1

                # count usage of assembly region
                if region_id not in assembly_region_info:
                    assembly_region_info[region_id] = {}
                if connecntor_id not in assembly_region_info[region_id]:
                    assembly_region_info[region_id][connecntor_id] = 0             
                assembly_region_info[region_id][connecntor_id] += 1                
        print(assembly_region_info)
        quit()

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
                if target_type 

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
