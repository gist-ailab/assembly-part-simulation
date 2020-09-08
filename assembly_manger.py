from script.const import PartType
from script.fileApi import *
import freecad_module

"""TODO:
- when quantity decided
"""

reverse_condition = [
    [0, 1, 2], # flat_head_screw_iso
    [1, 2], # ikea_l_bracket
    [], # ikea_stefan_bottom
    [3,4,5,7,8,9,10,11], # ikea_stefan_long
    [0,1,2,6,7,8,9,11], # ikea_stefan_middle
    [3,4,5,7,8,9,10,11], # ikea_stefan_short
    [3,7,12], # ikea_stefan_side_left
    [0,1,2,4,5,6,8,9,10,11,13,14,15, 16, 17, 18, 19], # ikea_stefan_side_right
    [], # ikea_wood_pin
    [0,1,2] # pan_head_screw_iso
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

        self.part_info_path = join(self.cad_path, "part_info.yaml")
        self.part_info = self.get_part_info()
        
        self.assembly_path = join("./assembly", self.furniture_name)
        check_and_create_dir(self.assembly_path)
        
        self.furniture_info_path = join(self.assembly_path, "furniture_info.yaml")
        self.initialize_furniture_info()
        
        # initialize status
        self.current_step = 1 # current instruction step
        self.current_status = self.initialize_status()
        
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
        for cad_dir in cad_dir_list:
            if PartType.furniture.value in cad_dir:
                part_type = PartType.furniture
            elif PartType.connector.value in cad_dir:
                part_type = PartType.connector
            else:
                print("unknown part type")
                exit()
            cad_list = get_file_list(cad_dir)
            for class_id, cad_file in enumerate(cad_list):
                part_name = os.path.splitext(cad_file)[0].replace(cad_dir + "/", "")
                if "ea)" in part_name:
                    part_name, quantity = part_name.split("(")
                    quantity = int(quantity.replace("ea)", ""))
                else:
                    quantity = 1
                assembly_points = self.FC_module.get_assembly_points(cad_file,
                                                                     part_name,
                                                                     quantity,
                                                                     self.logger,
                                                                     condition=None)
                part_info[part_name] = {
                    "class_id": class_id,
                    "type": part_type.value,
                    "model_file": cad_file,
                    "quantity": quantity,
                    "assembly_points": assembly_points
                }
        save_dic_to_yaml(part_info, self.part_info_path)

        return part_info
    
    def initialize_furniture_info(self):
        furniture_info = {}
        for part_name in self.part_info.keys():
            quantity = self.part_info[part_name]["quantity"]
            for i in range(quantity):
                instance_name = part_name + "_" + str(quantity)
                furniture_info[instance_name] = self.part_info[part_name]
        
        self.furniture_info = furniture_info
        save_dic_to_yaml(self.furniture_info, self.furniture_info_path)
        
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

        
