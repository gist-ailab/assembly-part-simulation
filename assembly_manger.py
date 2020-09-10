from script.const import PartType
from script.fileApi import *
import freecad_module
from enum import Enum

"""TODO:
- when quantity decided
"""

reverse_condition = [
    [0, 1, 2], # flat_head_screw_iso
    [], # ikea_wood_pin
    [0,1,2], # pan_head_screw_iso
    [1, 2], # ikea_l_bracket
    [], # ikea_stefan_bottom
    [3,4,5,7,8,9,10,11], # ikea_stefan_long
    [0,1,2,6,7,8,9,11], # ikea_stefan_middle
    [3,4,5,7,8,9,10,11], # ikea_stefan_short
    [3,7,12], # ikea_stefan_side_left
    [0,1,2,4,5,6,8,9,10,11,13,14,15, 16, 17, 18, 19], # ikea_stefan_side_right
    
]

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

        self.assembly_path = join("./assembly", self.furniture_name)
        check_and_create_dir(self.assembly_path)
        
        self.fc_document_path = join(self.assembly_path, "freecad_documents")
        check_and_create_dir(self.fc_document_path)  

        self.group_obj_path = join(self.assembly_path, "group_obj")
        check_and_create_dir(self.group_obj_path)

        self.group_info_path = join(self.assembly_path, "group_info")
        check_and_create_dir(self.group_info_path)

        self.part_info_path = join(self.cad_path, "part_info.yaml")
        self.part_info = self.get_part_info()

        self.initialize_group_info()        
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
        for cad_dir in cad_dir_list:
            if PartType.furniture.value in cad_dir:
                part_type = PartType.furniture
            elif PartType.connector.value in cad_dir:
                part_type = PartType.connector
            else:
                print("unknown part type")
                exit()
            cad_list = get_file_list(cad_dir)
            for cad_file in cad_list:
                part_name = os.path.splitext(cad_file)[0].replace(cad_dir + "/", "")
                # if "ea)" in part_name:
                #     part_name, quantity = part_name.split("(")
                doc_name = part_name + ".FCStd"
                doc_path = join(self.fc_document_path, doc_name)
                obj_name = part_name + ".obj"
                obj_path = join(self.group_obj_path, obj_name)
                assembly_points = self.FC_module.get_assembly_points(cad_file,
                                                                     part_name,
                                                                     self.logger,
                                                                     doc_path,
                                                                     obj_path,
                                                                     condition=reverse_condition)
                part_info[part_name] = {
                    "part_id": part_id,
                    "type": part_type.value,
                    "step_file": cad_file,
                    "document": doc_path,
                    "obj_file": obj_path,
                    "assembly_points": assembly_points
                }
                part_id += 1
        save_dic_to_yaml(part_info, self.part_info_path)

        return part_info
    
    def initialize_group_info(self):
        group_info = {}
        for group_id, part_name in enumerate(self.part_info.keys()):
            obj_path = self.part_info[part_name]["obj_file"]
            doc_path = self.part_info[part_name]["document"]
            group_info[part_name] = {
                "group_id": group_id,
                "quantity": 0,
                "obj_file": obj_path,
                "doc_file": doc_path,
                "composed_part": [],
            }
        
        self.group_info = group_info
        current_group_name = "group_info_" + str(self.current_step) + ".yaml"
        current_group_path = join(self.group_info_path, current_group_name)
        save_dic_to_yaml(self.group_info, current_group_path)

    def initialize_status(self):
        pass

    def check_instruction_info(self):
        self.logger.info("wating for instruction {}...".format(self.current_step))
        current_instrution = "instruction_" + str(self.current_step) + ".yaml"
        current_instrution_path = join(self.instruction_path, current_instrution)
        if os.path.isfile(current_instrution_path):
            self.logger.info("Get instruction {} information!".format(self.current_step))
            return True
        else:
            return False    
    
    def simulate_assemble(self):
        pass

    def step(self):
        self.current_step += 1

        