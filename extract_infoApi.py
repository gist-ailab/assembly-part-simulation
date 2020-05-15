import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import *
from freecadApi import get_assembly_points
import logging

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__)) # same as "./"
INPUT_PATH = join(CURRENT_PATH, "input")
OUTPUT_PATH = join(CURRENT_PATH, "output")
check_and_create_dir(OUTPUT_PATH)
FURNITURE_INFO_DIR = join(OUTPUT_PATH, "furniture_info") # save furniture information directory
check_and_create_dir(FURNITURE_INFO_DIR)
PART_INFO_DIR = join(OUTPUT_PATH, "part_info") # save furniture instance directory
check_and_create_dir(PART_INFO_DIR)
TRANSFER_INFO_DIR = join(CURRENT_PATH, "transfer_data")
check_and_create_dir(TRANSFER_INFO_DIR)

PART_TYPE = ["furniture_part", "connector_part"]

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
check_reverse = True

#----------------------------------------------
#region extract from CAD files

def initialize_furniture_info(furniture_name, logger):
    logger.info("Initialize {} furniture information".format(furniture_name))
    yaml_name = furniture_name + ".yaml"
    
    step_path = join(INPUT_PATH, "step_file", furniture_name)
    try:
        step_list = get_file_list(step_path)
    except:
        logger.warning("Fail to load input step files")
    # extract cad info
    step_list.sort()
    furniture_info = get_furniture_info(step_list, logger)
    yaml_path = join(FURNITURE_INFO_DIR, yaml_name)
    save_dic_to_yaml(furniture_info, yaml_path)
    
def get_furniture_info(step_list, logger):
    logger.debug("extract furniture information")
    furniture_info = {}
    for class_id, step_file in enumerate(step_list):
        step_name = os.path.splitext(step_file)[0]
        part_name = step_name.split('/')[-1]
        part_type = None
        quantity = 0        
        if step_name.find("ea)") == -1:
            part_type = PART_TYPE[0]
            quantity = 1
        else:
            part_type = PART_TYPE[1]
            part_name, quantity = part_name.split("(")
            quantity = quantity.replace("ea)", "")
        if check_reverse:
            cd = reverse_condition[class_id]
        else:
            cd = None
        assembly_points = get_assembly_points(step_file, part_name, logger, condition=cd)
        furniture_info[part_name] = {
            "class_id": class_id,
            "type": part_type,
            "model_file": step_file.replace(CURRENT_PATH, "."),
            "quantity": int(quantity),
            "assembly_points": assembly_points
        }

    return furniture_info

def initialize_part_info(furniture_name, logger):
    logger.info("Initialize {} part instance information".format(furniture_name))
    yaml_name = furniture_name + ".yaml"
    
    furniture_info_path = join(FURNITURE_INFO_DIR, furniture_name + ".yaml")
    furniture_info = load_yaml_to_dic(furniture_info_path)
    
    part_info = get_part_info(furniture_info)
    yaml_path = join(PART_INFO_DIR, yaml_name)
    save_dic_to_yaml(part_info, yaml_path)

def get_part_info(furniture_info):
    part_info = {}

    for part_name in furniture_info.keys():
        quantity = furniture_info[part_name]["quantity"]
        for q in range(quantity):
            instance_name = part_name + "_" + str(q)
            instance_info = {
                "type": part_name,
            }
            part_info[instance_name] = instance_info 

    return part_info

def get_initial_part_status(furniture_name):
    yaml_name = furniture_name + ".yaml"
    furniture_info_path = join(FURNITURE_INFO_DIR, furniture_name + ".yaml")
    furniture_info = load_yaml_to_dic(furniture_info_path)
    
    initial_status = {}

    for part_name in furniture_info.keys():
        quantity = furniture_info[part_name]["quantity"]
        for q in range(quantity):
            instance_name = part_name + "_" + str(q)
            instance_info = {}
            initial_status[instance_name] = instance_info 

    return initial_status

def initialize_furniture_config(furniture_name, logger):
    """initialize furniture information
        1. extract assembly points for each parts
        2. save furniture info for each parts in furniture_name.yaml
        3. initialize assembly status file
    Arguments:
        furniture_name {[type]} -- [description]
    """
    # initialize furniture info
    initialize_furniture_info(furniture_name, logger)    
    # initialize part instance
    initialize_part_info(furniture_name, logger)
    

#endregion