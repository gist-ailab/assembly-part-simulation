import os
from fileApi import *
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
PART_INFO_DIR = join(OUTPUT_PATH, "part_info") # save furniture instance directory
FREECAD_DOCUMENT_PATH = join(OUTPUT_PATH, "FCDocument")

def _load_instruction_info(furniture_name, instruction_step=1):
    instruction = "instruction_" + str(instruction_step) + ".yaml"
    yaml_path = join(INSTRUCTION_DIR, furniture_name, instruction)
    try:
        instruction_info = load_yaml_to_dic(yaml_path)
    except:
        return None

    return instruction_info

def _get_previous_assemble_status_list(furniture_name, instruction_step):
    """get previous status for current insturction step

    Arguments:
        furniture_name {[type]} -- [description]
        instruction_step {[type]} -- [description]

    Returns:
        [list of dict] -- [previous statuses]
    """
    status_list = []
    if instruction_step == 1: # start assemble
        initial_status = _get_initial_part_status(furniture_name)
        status_list.append(initial_status)
    else:
        previous_instruction = "instruction_" + str(instruction_step - 1) 
        previous_instruction_dir = join(STATUS_DIR, furniture_name, previous_instruction)
        previous_status_dir = join(previous_instruction_dir, "final")
        status_file_list = get_file_list(previous_status_dir)
        for status in status_file_list:
            status_list.append(load_yaml_to_dic(status))

    return status_list

def _get_initial_part_status(furniture_name):
    furniture_info_path = join(FURNITURE_INFO_DIR, furniture_name + ".yaml")
    furniture_info = load_yaml_to_dic(furniture_info_path)
    
    initial_status = {}

    for part_name in furniture_info.keys():
        quantity = furniture_info[part_name]["quantity"]
        for q in range(quantity):
            instance_name = part_name + "_" + str(q)
            doc_name = part_name + ".FCStd"
            instance_info = {
                "child": [],
                "document": doc_name
            }
            initial_status[instance_name] = instance_info 

    return initial_status

def initialize_assembly_status(furniture_name, instruction_step, logger):
    logger.info(f"Initialize before instruction {instruction_step} assembly")
    furniture_status_dir = join(STATUS_DIR, furniture_name)
    if instruction_step == 1:
        check_and_create_dir(furniture_status_dir)

    current_status_dir = join(furniture_status_dir, "instruction_" + str(instruction_step))
    try:
        check_and_create_dir(current_status_dir)
    except:
        logger.warning("Current instruction step already assemlbed!")
    intermidiate_dir = join(current_status_dir, "intermidiate")
    check_and_create_dir(intermidiate_dir)
    final_dir = join(current_status_dir, "final")    
    check_and_create_dir(final_dir)

    try:
        previous_status_list = _get_previous_assemble_status_list(furniture_name, instruction_step)    
    except:
        logger.warning("Fail to load previous status")
        return None
    initial_status = {}
    for idx, pre_status in enumerate(previous_status_list):
        status_name = "status_" + str(idx)
        initial_status[status_name] = pre_status

    yaml_name = "initial_status.yaml"
    yaml_path = join(current_status_dir, yaml_name)
    save_dic_to_yaml(initial_status, yaml_path)    

def start_assemble(furniture_name, instruction_step, logger):
    logger.info(f"Start to assemble instruction {instruction_step}")
    instruction_info = _load_instruction_info(furniture_name, instruction_step)
    if instruction_info == None:
        logger.warning(f"No instruction {instruction_step}")
        return None
    parts_sequence = get_part_sequence(instruction_info) # 파트 조립 순서 
    assemlbe_parts(parts_sequence)

def assemble_part(furniture_name, part_a_name, part_b_name):
    part_a_info = _get_part_info(furniture_name, part_a_name)

def _get_part_info(furniture_name, part_name):
    parts_info_path = join(PART_INFO_DIR, furniture_name + ".yaml")
    parts_info = load_yaml_to_dic(parts_info_path)
    part_type = parts_info[part_name]["type"]
    


def _check_same_status(status_1, status_2):
    
    return status_1 == status_2

def _get_parent_list(status):

    return status.keys()
