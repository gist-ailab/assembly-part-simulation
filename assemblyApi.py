import os
from fileApi import *
from freecadApi import assemble_parts
import logging



CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = join(CURRENT_PATH, "input")

INSTRUCTION_DIR = join(INPUT_PATH, "instruction")
check_and_create_dir(INSTRUCTION_DIR)
OUTPUT_PATH = join(CURRENT_PATH, "output")
check_and_create_dir(OUTPUT_PATH)
STATUS_DIR = join(OUTPUT_PATH, "assembly_status")
check_and_create_dir(STATUS_DIR)
SEQUENCE_DIR = join(OUTPUT_PATH, "assembly_sequence")
check_and_create_dir(SEQUENCE_DIR)

#----------------------------------------------------
FURNITURE_INFO_DIR = join(OUTPUT_PATH, "furniture_info") # save furniture information directory
INSTANCE_INFO_DIR = join(OUTPUT_PATH, "instance_info") # save furniture instance directory

#-----------------------------------------------------
class Assembly_Process(object):
    def __init__(self, furniture_name, instruction_step, logger):
        
        self._furniture_name = furniture_name
        self._instruction_step = instruction_step
        self._logger = logger

        self._initial_status_name = "initial_status.yaml"
        self._last_status_name = "final.yaml"

        self._logger.info(f"Initialize assembly process.\n 
                            Furniture Name: {furniture_name}\n  
                            Instruction Step: {instruction_step}")
        if self._instruction_step == 1:
            self._initialize_furniture_dir()
        else:
            self._furniture_status_dir = join(STATUS_DIR, self._furniture_name)
            self._furniture_sequence_dir = join(SEQUENCE_DIR, self._furniture_name)

        self._initialize_extracted_info()
        self._initialize_assembly_status()
        self._initialize_assembly_sequence()
        self._initialize_instruction_info()
        """
        self._furniture_info
        self._instance_info
        self._current_status_dir
        self._initial_status
        self._current_status
        self._sequence_path
        self._assembly_sequence
        """
    #region initialize and save and load files---------------------------------------
    def _initialize_furniture_dir(self):
        self._furniture_status_dir = join(STATUS_DIR, self._furniture_name)
        check_and_create_dir(self._furniture_status_dir)

    def _initialize_extracted_info(self):
        # assembly points information for each part name
        furniture_info_path = join(FURNITURE_INFO_DIR, self._furniture_name + ".yaml")
        self._furniture_info = load_yaml_to_dic(furniture_info_path)
        # matching each instance to its part name
        instance_info_path = join(INSTANCE_INFO_DIR, self._furniture_name + ".yaml")
        self._instance_info = load_yaml_to_dic(instance_info_path)

    def _initialize_assembly_status(self):
        self._current_status_dir = join(self._furniture_status_dir, str(_instruction_step))
        if not check_and_create_dir(self._current_status_dir):
            self._logger.warning(f"assembly for instruction {self._instruction_step} already exist")
        if _instruction_step == 1:
            self._initial_status = self._get_initial_part_status()
        else:
            self._initial_status = self._get_previous_assembly_status()
        self._logger.info("Start assembly with Status")
        for instance_name in self._initial_status.keys():
            print("\t" + instance_name)
            for child in self._initial_status[instance_name]["child"].keys():
                print("\t"*2 + "-" + child)
    
    def _get_initial_part_status(self):
        initial_status = {}
        for instance_name in self._instance_info.keys():
            part_name = self._instance_info[instance_name]
            part_info = self._furniture_info[part_name]
            quantity = part_info["quantity"]
            assembly_point_num = len(part_info["assembly_points"])
            initial_status[instance_name] = {
                "document": instance_name,
                "child": {},
                "unused_points": list(range(assembly_point_num)),
            }

        return initial_status

    def _get_previous_assembly_status(self):
        previous_instruction = str(_instruction_step - 1) 
        previous_status_dir = join(_furniture_status_dir, previous_instruction)
        previous_final_status = join(previous_status_dir, self._last_status_name)
        status = load_yaml_to_dic(previous_final_status)

        return status

    def _initialize_assembly_sequence(self):
        self._sequence_path = join(SEQUENCE_DIR, self._furniture_name + ".yaml")
        if self._instruction_step == 1:
            self._assembly_sequence = []
            self._save_sequence()
        else:
            self._assembly_sequence = self._load_sequence()

    def _add_assembly_to_sequence(self):
        assembly_point_pairs = self._current_assembly["pairs"]
        unique_part_pair = {}
        for pair in assembly_point_pairs:
            part_pair = [pair[0][0], pair[1][0]]
            if not part_pair in unique_part_pair.keys():
                unique_part_pair[part_pair] = []
            point_pair = [pair[0][1], pair[1][1]]
            unique_part_pair[part_pair].append(point_pair)
        unit_assemblies = []
        for unique_pair in unique_part_pair.keys():
            unit_assembly = {
                    "assembly_parts": unique_pair,
                    "assembly_point_pairs": unique_part_pair[unique_pair]
                }
            unit_assemblies.append(unit_assembly)
        assembly = {
            "assembly_id": len(self._assembly_sequence) + 1,
            "assembly_part_pairs": self._current_assembly["parts"],
            "assembly_skill": "unknown",
            "unit_assemblies": unit_assemblies,
            "assembly_status": self._current_assembly["status"],
            "assembly_desired_status": self._current_status,
        }

    def _save_status(self, status_name=None):
        if status_name == None:
            status_name = "status" + str(get_time_stamp()) + ".yaml"
        yaml_path = join(self._curret_status_dir, status_name)
        save_dic_to_yaml(self._current_status, yaml_path)

    def _load_sequence(self):
        return load_yaml_to_dic(self._sequence_path)

    def _save_sequence(self):
        save_dic_to_yaml(self._assembly_sequence, self._sequence_path)
    
    def _initialize_instruction_info(self):
        instruction = "instruction_" + str(_instruction_step) + ".yaml"
        yaml_path = join(INSTRUCTION_DIR, _furniture_name, instruction)
        try:
            self._instruction_info = load_yaml_to_dic(yaml_path)
        except:
            logger.warning("fail to load instruction")
    
    #endregion-----------------------------------------------------------------------

    #region assembly algorithm
    def _get_assemble_info(instance_name):
        """get assembly points and document of part_instance
        1. get document name from current status
        2. get assembly points info from furniture_info
            parent:
                id_0:
                    point_info_dic
                id_1:
                    point_info_dic
                id_3:
                    point_info_dic
            child1:
                id_0:
                    point_info_dic
                ...
        Arguments:
            instance_name {string} -- [instance name of part]
        """
        # 1. get document name from current status
        part_doc = self._current_status[instance_name]["document"]

        # 2. get assembly points info from furniture_info
        # 2.1 get all assemblyable point index
        assemblyable_points = {}
        instance_info = self._current_status[instance_name]
        assemblyable_points[instance_name] = instance_info["unused_points"]
        child_list = self._current_status[instance_name]["child"].keys()
        for child_instance in child_list:
            child_info = instance_info["child"][child_instance]
            assemblyable_points[child_instance] = child_info["unused_points"]
        # 2.2 extract each assembly points detail info from furniture info
        for instance_name in assemblyable_points.keys():
            points_info = {}
            part_name = self._instance_info[instance_name]["part_name"] # instance는 instance 정보 중 변하지 않는 정보
            assembly_points = self._furniture_info[part_name]["assembly_points"]
            
            for point_idx in assemblyable_points[instance_name]:
                key = "id_" + str(point_idx)
                points_info[key] = assembly_points[point_idx]
            assemblyable_points[instance_name] = points_info
        
        return assembly_points, part_doc
    
    def _get_assembly_part_sequence(self):
        assembly_parts = self._instruction_info.keys()
        pass

        return list(assembly_parts)

    def _assemble_part(self):
        """try to assemble A and B and return result
        success to assemble => return True
        fail to assemble => return False
        """
        part_A = self._current_assembly["parent"]
        part_B = self._current_assembly["child"]
        self._logger.info(f"Try {part_A} + {part_B}")
        part_a_assembly_points, part_a_doc = self._get_assemble_info(part_a_name)
        part_b_assembly_points, part_b_doc = self._get_assemble_info(part_b_name)
        point_pairs = _get_point_pairs(part_a_assembly_points, part_b_assembly_points)

        if len(point_pairs) > 0:
            parent_idx, result_doc, assembly_point_pairs = assemble_parts(part_a_assembly_points, 
                                                                          part_b_assembly_points,
                                                                          part_a_doc, part_b_doc, 
                                                                          point_pairs)
            if len(assembly_point_pairs) > 0:
                self._current_assembly["result"] = result_doc
                self._current_assembly["pairs"] = assembly_point_pairs
                if parent_idx == 0:
                    pass
                else:
                    self._current_assembly["parent"] = part_B
                    self._current_assembly["child"] = part_A
                
                return True
            else:
                self._logger.info(f"{part_A} and {part_B} has no assembly points")
                
                return False
        
        else:
            self._logger.info(f"{part_A} and {part_B} are same part")
            
            return False
        
    def _update_status(self):
        used_info = self._get_used_point(self._current_assembly["pairs"])
        parent = self._current_assembly["parent"]
        child = self._current_assembly["child"]
        result_document = self._current_assembly["result"]
        self._remove_used_point(parent, child, used_info)
        new_status = {}
        for previous_parent in self._current_status.keys():
            if previous_parent == child:
                continue
            else:
                new_status[previous_parent] = self._current_status[previous_parent]
            if previous_parent == parent:
                child_status = {
                    "unused_points": self._current_status[child]["unused_points"]
                }
                new_status[parent]["child"][child] = child_status
                child_child = self._current_status[child]["child"]
                new_status[parent]["child"].update(child_child) 
                new_status[parent]["document"] = result_document
            else:
                pass

    def _remove_used_point(self, parent, child, used_info):
        new_status = self._current_status
        parent_childs = new_status[parent]["child"]
        child_childs = new_status[child]["child"]
        for instance_name in used_info.keys():
            used_idx_list = used_info[instance_name]
            if instance_name == parent:
                for used_idx in used_idx_list:
                    new_status[instance_name]["unused_points"].remove(used_idx)
            elif instance_name == child:
                for used_idx in used_idx_list:
                    new_status[instance_name]["unused_points"].remove(used_idx)
            else:
                if instance_name in parent_childs:
                    for idx in used_idx_list:
                        new_status[parent][instance_name]["unused_points"].remove(used_idx)    
                else:
                    for idx in used_idx_list:
                        new_status[child][instance_name]["unused_points"].remove(used_idx)
        self._current_status = new_status
    
    @staticmethod
    def _get_point_pairs(assembly_points_a, assembly_points_b):
        """
        return:
            assembly_pairs {list of tuple}
                [((part_in_a, point_key), (part_in_b, point_key)), ...]
        """
        assembly_points_a_list = []
        assembly_points_b_list = []
        for p_a in assembly_points_a.keys():
            for ap_a in assembly_points_a[p_a].keys():
                assembly_points_a_list.append((p_a, ap_a))
        for p_b in assembly_points_b.keys():
            for ap_b in assembly_points_b[p_b].keys():
                assembly_points_b_list.append((p_b, ap_b))
        
        assembly_pairs = []
        for ap_a in assembly_points_a_list:
            for ap_b in assembly_points_b_list:
                if not self._is_same_part(p_a, p_b):
                    assembly_pairs.append((ap_a, ap_b))
            
        return assembly_pairs
    
    @staticmethod
    def _get_used_point(assembly_point_pairs):
        """get used point index from assemble point pairs

        Arguments:
            assembly_point_pairs
                [(("part_name", "id_index"), ("part2_name", "point_idx")), (), ...]
        """
        used_info = {}
        for pair in assembly_point_pairs:
            part_a_name = pair[0][0]
            part_a_used_id = int(pair[0][1].replace("id_", ""))
            part_b_name = pair[1][0]
            part_b_used_id = int(pair[1][1].replace("id_", ""))
            if part_a_name in used_info.keys():
                used_info[part_a_name].append(part_a_used_id)
            else:
                used_info[part_a_name] = [part_a_used_id]
            if part_b_name in used_info.keys():
                used_info[part_b_name].append(part_b_used_id)
            else:
                used_info[part_b_name] = [part_b_used_id]

        return used_info

    @staticmethod
    def _get_only_status(status):
        only_status = {}
        for part_name in status.keys():
            only_status[part_name] = {}
            for child_name in status[part_name]["child"].keys():
                only_status[part_name][child_name] = {}

        return only_status

    def _is_same_part(self, part_a, part_b):
        
        return self._instance_info[part_a] == self._instance_info[part_b]

    def start_assemble(self):
        logger.info("Start to assemble")
        self._current_status = self._initial_status
        part_sequence = self._get_assembly_part_sequence()
        part_A = part_sequence[0]
        for part_B in part_sequence[1:]:
            self._current_assembly = {
                "parts": [part_A, part_B],
                "parent": part_A,
                "child": part_B,
                "pairs": [],
                "result": "unknown",
                "status": self._current_status,
            }
            if not self._assemble_part():
                parts_sequence += [part_B]
                continue
            else:
                self._update_status()
                part_A = self._current_assembly["parent"]
            
            #region save sequence
            _save_assemblies_sequence(_current_assembly_sequence, unit_assemblies):
            #endregion

    #endregion
