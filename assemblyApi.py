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
#----------------------------------------------------
FURNITURE_INFO_DIR = join(OUTPUT_PATH, "furniture_info") # save furniture information directory
INSTANCE_INFO_DIR = join(OUTPUT_PATH, "instance_info") # save furniture instance directory

#-----------------------------------------------------
_furniture_name = "furniture_name"
_furniture_info = {}
_instance_info = {}
_instruction_step = 1 
_instruction_info = {}
_furniture_status_dir = "output/assembly_status/furniture_name/instruction_step/"
_current_instruction_dir = _furniture_status_dir + "instruction_step/"
_initial_status = {}
_intermidiate_dir = _current_instruction_dir + "intermidiate"
_final_dir = _current_instruction_dir + "final"
_current_status = {}

def start_assemble(furniture_name, instruction_step, logger):
    global _current_status
    logger.info(f"Start to assemble {furniture_name} instruction {instruction_step}")
    _initialize_assembly_status(furniture_name, instruction_step, logger)
    _load_instruction_info(logger)
    
    for status_idx, start_status_key in enumerate(_initial_status.keys()):
        _current_status = _initial_status[start_status_key]
        parts_sequence = _get_parts_sequence(logger)
        part_A = parts_sequence[0]
        
        for seq_idx, part_B in enumerate(parts_sequence[1:]):
            #TODO:
            parent_part, child_parts, result_document, used_info = _assemble_part_A_B(part_A, part_B)
            if parent_part == part_A:
                child_part = part_B
            else:
                child_part = part_A
            if not len(child_parts) > 0:
                logger.warning("no assemble result")
            if len(used_info) > 0:
                for used_part in used_info.keys():
                    used_idx_list = used_info[used_part]
                    if used_part == part_A or used_part == part_B:
                        for idx in used_idx_list:
                            _current_status[used_part]["unused_points"].remove(idx)
                    else:
                        if used_part in _current_status[part_A]["child"]:
                            for idx in used_idx_list:
                                _current_status[part_A]["child"][used_part]["unused_points"].remove(idx)
                        elif used_part in _current_status[part_B]["child"]:
                            for idx in used_idx_list:
                                _current_status[part_B]["child"][used_part]["unused_points"].remove(idx)
                        else:
                            logger.warning("used part not in current status")
            new_status = {}
            for previous_parent in _current_status.keys():
                # remove child part from key(parent) of status
                if previous_parent == child_part:
                    continue
                else:
                    new_status[previous_parent] = _current_status[previous_parent]
                
                if previous_parent == parent_part:
                    child_status = {
                        "unused_points": _current_status[child_part]["unused_points"]
                    }
                    new_status[parent_part]["child"][child_part] = child_status
                    child_child = _current_status[child_part]["child"]
                    new_status[parent_part]["child"].update(child_child) 
                    new_status[parent_part]["document"] = result_document
                else:
                    pass
            new_status_yaml = "status_" + str(status_idx) + "_seq_" + str(seq_idx) + ".yaml"
            new_status_path = join(_intermidiate_dir, new_status_yaml)
            save_dic_to_yaml(new_status, new_status_path)
            _current_status = new_status
            part_A = parent_part
            #endregion

def _assemble_part_A_B(part_a_name, part_b_name):
    """
    part_a_name: instance name of part
    """
    part_a_assembly_points, part_a_doc = _get_assemble_info(part_a_name)
    part_b_assembly_points, part_b_doc = _get_assemble_info(part_b_name)
    
    point_pairs = _get_point_pairs(part_a_assembly_points, part_b_assembly_points)
    parent_idx, result_doc, assembly_point_pairs = assemble_parts(part_a_assembly_points, 
                                                                    part_b_assembly_points,
                                                                    part_a_doc, part_b_doc, 
                                                                    point_pairs)
    child_parts = []
    if parent_idx == 0:
        parent_part = part_a_name
        child_parts = list(part_b_assembly_points.keys())
    else:
        parent_part = part_b_name
        child_parts = list(part_a_assembly_points.keys())

    used_info = _get_used_point(assembly_point_pairs)
    return parent_part, child_parts, result_doc, used_info

def _get_point_pairs(assembly_points_a, assembly_points_b):
    """
    return:
        assembly_pairs {list of tuple}
            [((part_in_a, point_key), (part_in_b, point_key)), ...]
    """
    assembly_pairs = []
    assembly_points_a_list = []
    assembly_points_b_list = []
    for p_a in assembly_points_a.keys():
        for ap_a in assembly_points_a[p_a].keys():
            assembly_points_a_list.append((p_a, ap_a))
    for p_b in assembly_points_b.keys():
        for ap_b in assembly_points_b[p_b].keys():
            assembly_points_b_list.append((p_b, ap_b))
    for ap_a in assembly_points_a_list:
        for ap_b in assembly_points_b_list:
            if not _is_same_part(p_a, p_b):
                assembly_pairs.append((ap_a, ap_b))
        
    return assembly_pairs
#---------------------------------------------------------
#region assembly_rule
def _is_same_part(part_a, part_b):
    type_a = part_a.split("_")[:-1]
    type_b = part_b.split("_")[:-1]
    
    return type_a == type_b


#endregion
def _get_used_point(assemble_point_pairs):
    """get used point index from assemble point pairs

    Arguments:
        assemble_point_pairs
            [(("part_name", "id_index"), ("part2_name", "point_idx")), (), ...]
    """
    used_info = {}
    for pair in assemble_point_pairs:
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
    part_doc = _current_status[instance_name]["document"]
    
    assembly_points = {}
    instance_info = _current_status[instance_name]
    assembly_points[instance_name] = instance_info["unused_points"]
    child_list = _current_status[instance_name]["child"].keys()
    for child_instance in child_list:
        assembly_points[child_instance] = instance_info["child"][child_instance]["unused_points"]
    for assembly_instance in assembly_points.keys():
        points_info = {}
        part_name = _instance_info[assembly_instance]["part"]
        points_candidate = _furniture_info[part_name]["assembly_points"]
        for point_idx in assembly_points[assembly_instance]:
            key = "id_" + str(point_idx)
            points_info[key] = points_candidate[point_idx]
        assembly_points[assembly_instance] = points_info
    
    return assembly_points, part_doc

def _initialize_assembly_status(furniture_name, instruction_step, logger):
    global _furniture_name, _instruction_step, _initial_status
    logger.info(f"Initialize assembly status")
    _furniture_name = furniture_name
    _initialize_extracted_info(logger)
    _instruction_step = instruction_step
    _initialize_assemble_dir(logger)
    try:
        previous_status_list = _get_previous_assemble_status_list(logger)    
    except:
        logger.warning("Fail to load previous status")
        return None
    for idx, pre_status in enumerate(previous_status_list):
        status_name = "status_" + str(idx)
        _initial_status[status_name] = pre_status
    yaml_name = "initial_status.yaml"
    yaml_path = join(_current_instruction_dir, yaml_name)
    save_dic_to_yaml(_initial_status, yaml_path)

def _initialize_extracted_info(logger):
    global _furniture_info, _instance_info
    furniture_info_path = join(FURNITURE_INFO_DIR, _furniture_name + ".yaml")
    _furniture_info = load_yaml_to_dic(furniture_info_path)
    instance_info_path = join(INSTANCE_INFO_DIR, _furniture_name + ".yaml")
    _instance_info = load_yaml_to_dic(instance_info_path)

def _initialize_assemble_dir(logger):
    global _furniture_status_dir, _current_instruction_dir, _intermidiate_dir, _final_dir
    _furniture_status_dir = join(STATUS_DIR, _furniture_name)
    if _instruction_step == 1:
        check_and_create_dir(_furniture_status_dir)
    _current_instruction_dir = join(_furniture_status_dir, "instruction_" + str(_instruction_step))
    try:
        check_and_create_dir(_current_instruction_dir)
    except:
        logger.warning("Current instruction step assemble already exist!")
    _intermidiate_dir = join(_current_instruction_dir, "intermidiate")
    check_and_create_dir(_intermidiate_dir)
    _final_dir = join(_current_instruction_dir, "final")    
    check_and_create_dir(_final_dir)

def _get_previous_assemble_status_list(logger):
    """get previous status for current insturction step

    Arguments:
        furniture_name {[type]} -- [description]
        _instruction_step {[type]} -- [description]

    Returns:
        [list of dict] -- [previous statuses]
    """
    status_list = []
    if _instruction_step == 1: # start assemble
        status = _get_initial_part_status()
        status_list.append(status)
    else:
        previous_instruction = "instruction_" + str(_instruction_step - 1) 
        previous_instruction_dir = join(_furniture_status_dir, previous_instruction)
        previous_status_dir = join(previous_instruction_dir, "final")
        status_file_list = get_file_list(previous_status_dir)
        for status in status_file_list:
            status_list.append(load_yaml_to_dic(status))

    return status_list
    
def _get_initial_part_status():
    initial_status = {}
    for part_name in _furniture_info.keys():
        quantity = _furniture_info[part_name]["quantity"]
        assembly_point_num = len(_furniture_info[part_name]["assembly_points"])
        for q in range(quantity):
            instance_name = part_name + "_" + str(q)
            doc_name = instance_name + ".FCStd"
            instance_info = {
                "child": {},
                "unused_points": list(range(assembly_point_num)),
                "document": doc_name,
                "assembly_sequence": []
            }
            initial_status[instance_name] = instance_info 

    return initial_status

def _get_parts_sequence(logger):
    """get part sequence for assembly from current status and instruction
    return:
        part_sequence {list[string]} -- [part_1, part_2, part_3...]
    """
    logger.info("get assembly sequence from instruction info")
    assemble_parts = _instruction_info.keys()
    part_sequence = []
    for part_name in assemble_parts:
        quantity = _instruction_info[part_name]["quantity"]
        for idx in range(quantity):
            instance_part = _get_instance(idx, part_name, _current_status)
            if instance_part == None:
                logger.warning("fail to find parent part")
            part_sequence.append(instance_part)
    
    #TODO: sort sequence
    
    return part_sequence

def _get_instance(pass_num, part_name, status):
    parent_list = status.keys()
    for parent in parent_list:
        if part_name in parent:
            if pass_num == 0:
                return parent
            else:
                pass_num -= 1
    
    return None

def _load_instruction_info(logger):
    global _instruction_info
    instruction = "instruction_" + str(_instruction_step) + ".yaml"
    yaml_path = join(INSTRUCTION_DIR, _furniture_name, instruction)
    try:
        _instruction_info = load_yaml_to_dic(yaml_path)
    except:
        logger.warning("fail to load instruction")

def _check_same_status(status_1, status_2):
    
    return status_1 == status_2

def _get_parent_list(status):

    return status.keys()
