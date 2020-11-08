from script.const import PartType, AssemblyType, AssemblyPair
from script.fileApi import *
import freecad_module
from enum import Enum

"""TODO:
- when quantity decided
"""

reverse_condition = [
    [0, 1, 2], # flat_head_screw_iso
    [1, 2], # ikea_l_bracket
    [], # ikea_wood_pin
    [0,1,2], # pan_head_screw_iso
    [], # ikea_stefan_bottom
    [3,4,5,7,8,9,10,11], # ikea_stefan_long
    [0,1,2,6,7,8,9,11], # ikea_stefan_middle
    [3,4,5,7,8,9,10,11], # ikea_stefan_short
    [3,7,12], # ikea_stefan_side_left
    [0,1,2,4,5,6,8,9,10,11,13,14,15, 16, 17, 18, 19], # ikea_stefan_side_right
]

"""STEFAN unique radius
    0 2.499999999999989 => pin
    1 2.499999999999995 => pin
    2 2.5000000000000004 => long, short for flat head penet
    3 2.7499999999999747 => side hole for flat head penet
    4 2.750000000000001 => side hole for flat head penet
    5 3.000000000000001 => braket penetration
    6 3.0000000000000027 => long, short hole for braket
    7 3.4999999999999996 => short hole for pin
    8 3.5 => braket insert
    9 4.0 => long hole for pin 
    10 4.000000000000001 => middle hole for pin
    11 4.000000000000002 => middle hole for pin
    12 4.000000000000003 => middle hole for pin
    13 4.0000000000000036 => side hole for pin
    14 5.65 => flat head
    15 6.0 => pan head
    
    pin group [0, 1, 7, 9, 10, 11, 12, 13]
    braket group [5, 8]
    flat_penet group [2, 3, 4, 14]
    pan [15]
"""
radius_group = {
    "pin group": [0, 1, 7, 9, 10, 11, 12, 13],
    "braket group": [5, 8],
    "flat_penet group": [2, 3, 4, 14],
    "pan": [15]
}

class AssemblyManager(object):
    """
    get CAD and instruction data to assemble furniture
    
        CAD from join(cad_root, furniture_name)
        Instruction from join(instruction_root, furniture_name)

    simulating assembly until instruction end
    
    Assembly Manager 
        - link Instruction Module with other Modules
            - communicate by file save and load
        - file load and save
        
    FreeCAD Module
        - extract assemlby points
        - assemble 2 parts
        - extract intermidiate parts

    """
    def __init__(self, logger, furniture_name, cad_root="./cad_file", instruction_root="./instruction"):
        self.logger = logger
        self.furniture_name = furniture_name
        self.cad_path = join(cad_root, self.furniture_name)
        self.instruction_path = join(instruction_root, self.furniture_name)
        self.FC_module = freecad_module
        self.current_step = 0 # current instruction step
        self.is_end = False

        #region initialize folder
        # 조립 폴더 생성
        check_and_create_dir("./assembly")
        self.assembly_path = join("./assembly", self.furniture_name)
        check_and_create_dir(self.assembly_path)
        # Part Document 폴더 생성
        self.part_document_path = join(self.assembly_path, "part_documents")
        check_and_create_dir(self.part_document_path)  
        # Group(*.obj) 폴더 생성
        self.group_obj_path = join(self.assembly_path, "group_obj")
        check_and_create_dir(self.group_obj_path)
        # Group info 폴더 생성
        self.group_info_path = join(self.assembly_path, "group_info")
        check_and_create_dir(self.group_info_path)
        # assembly Document 폴더 생성
        self.assembly_document_path = join(self.assembly_path, "assembly_documents")
        check_and_create_dir(self.assembly_document_path)  
        #endregion

        self.furniture_parts, self.connector_parts = [], [] # save part_name
        self.part_info_path = join(self.assembly_path, "part_info.yaml")
        self.part_info = self.get_part_info()
        self.FC_module.PART_INFO = self.part_info
        self.initialize_each_parts() # check part type

        self.assembly_pairs = self.get_assembly_pairs()
        self.FC_module.assemble_pair_test(self.assembly_pairs["pair"])

        self.initialize_group_info()
        self.initialize_connector_info()
        self.instance_info = {}
        self.instance_info_path = join(self.assembly_path, "intance_info.yaml")
        self.status = {}
        self.current_step += 1

    def get_part_info(self):
        if check_file(self.part_info_path):
            return load_yaml_to_dic(self.part_info_path)

        else: #extract part info from cad files
            return self.extract_part_info()

    def extract_part_info(self):
        """extract furniture's part info from cad files

        Returns:
            [type]: [description]
        """
        part_info = {}
        cad_dir_list = get_dir_list(self.cad_path)
        
        part_id = 0
        cad_dir_list.sort()
        for cad_dir in cad_dir_list:
            if PartType.furniture.value in cad_dir:
                part_type = PartType.furniture
            elif PartType.connector.value in cad_dir:
                part_type = PartType.connector
            else:
                print("unknown part type")
                exit()
            cad_list = get_file_list(cad_dir)
            cad_list.sort()
            for cad_file in cad_list:
                _, part_name = os.path.split(cad_file)
                part_name = os.path.splitext(part_name)[0]
                doc_path = join(self.part_document_path, part_name+".FCStd")
                assembly_points = self.FC_module.extract_assembly_points(step_path=cad_file,
                                                                         step_name=part_name,
                                                                         doc_path=doc_path,
                                                                         part_type=part_type,
                                                                         logger=self.logger)
                part_info[part_name] = {
                    "part_id": part_id,
                    "type": part_type.value,
                    "document": doc_path,
                    "step_file": cad_file,
                    "assembly_points": assembly_points
                }
                part_id += 1

        save_dic_to_yaml(part_info, self.part_info_path)

        return part_info
    
    def initialize_each_parts(self):
        for part_name in self.part_info.keys():
            if self.part_info[part_name]["type"] == PartType.furniture.value:
                self.furniture_parts.append(part_name)
            elif self.part_info[part_name]["type"] == PartType.connector.value:
                self.connector_parts.append(part_name)
            else:
                self.logger.error("type is not matching!")
                exit()

    def get_assembly_pairs(self):
        """part info 를 바탕으로 가능한 모든 assembly pairs 를 출력
        """
        def get_group(radius):
            idx = unique_radius.index(radius)
            for group in radius_group.keys():
                if idx in radius_group[group]:
                    return group
        assembly_pairs = {}
        if check_file("./pairs.yaml"):
            return load_yaml_to_dic("./pairs.yaml")
        
        unique_radius = []
        for part in self.part_info.keys():
            points = self.part_info[part]["assembly_points"]
            for point in points:
                radius = point["radius"]
                if radius in unique_radius:
                    pass
                else:
                    unique_radius.append(radius)
        unique_radius.sort()
        count = 0
        for part1 in self.part_info.keys():
            for part2 in self.part_info.keys():
                info1 = self.part_info[part1]
                info2 = self.part_info[part2]
                points1 = info1["assembly_points"]
                points2 = info2["assembly_points"]
                for point1 in points1:
                    for point2 in points2:
                        if point1["type"] == point2["type"]:
                            continue
                        if get_group(point1["radius"]) == get_group(point2["radius"]):
                            offset = 0
                            if get_group(point1["radius"]) == "pin group":
                                offset = 15 # 0.015
                            new_pair = {
                                "part1": [part1, point1["id"]],
                                "part2": [part2, point2["id"]],
                                "offset": offset
                            }
                            assembly_pairs["pair_" + str(count)] = new_pair
                            count += 1
        save_dic_to_yaml(assembly_pairs, "./pairs.yaml")
        return assembly_pairs

    def initialize_group_info(self):
        group_info = {}
        for group_id, part_name in enumerate(self.furniture_parts):
            doc_path = self.part_info[part_name]["document"]
            obj_path = join(self.group_obj_path, part_name + ".obj")
            self.FC_module.extract_group_obj(doc_path, obj_path)
            group_name = part_name
            group_info[group_name] = {
                "group_id": group_id,
                "quantity": 0,
                "obj_file": obj_path,
                "composed_part": [],
            }
        self.group_info = group_info
        current_group_name = "group_info_" + str(self.current_step) + ".yaml"
        current_group_path = join(self.group_info_path, current_group_name)
        save_dic_to_yaml(self.group_info, current_group_path)

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
