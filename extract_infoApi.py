import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import get_dir_list, get_file_list, save_dic_to_yaml
from freecadApi import get_assembly_points
import logging

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__)) # same as "./"
INPUT_PATH = join(CURRENT_PATH, "input")
OUTPUT_PATH = join(CURRENT_PATH, "output")
if not os.path.isdir(OUTPUT_PATH):
    os.mkdir(OUTPUT_PATH)
FURNITURE_INFO_DIR = join(OUTPUT_PATH, "furniture_info") # save furniture information directory
if not os.path.isdir(FURNITURE_INFO_DIR):
    os.mkdir(FURNITURE_INFO_DIR)
STATUS_DIR = join(OUTPUT_PATH, "assembly_status")
if not os.path.isdir(STATUS_DIR):
    os.mkdir(STATUS_DIR)
PART_TYPE = ["furniture_part", "connector_part"]


def initialize_furniture_config(furniture_name):
    """initialize furniture information
        1. extract assembly points for each parts
        2. save furniture info for each parts in furniture_name.yaml
        3. initialize assembly status file
    Arguments:
        furniture_name {[type]} -- [description]
    """
    logger = logging.getLogger(furniture_name)
    # initialize furniture info
    yaml_name = furniture_name + ".yaml"
    step_path = join(INPUT_PATH, "step_file", furniture_name)
    try:
        step_list = get_file_list(step_path)
    except:
        logger.warning("Fail to load input step files")
    step_list.sort()
    furniture_info = {}
    for class_id, step_file in enumerate(step_list):
        step_name = os.path.splitext(step_file)[0]
        part_name = step_name.replace(step_path + '/', "")
        part_type = None
        quantity = 0        
        if step_name.find("ea)") == -1:
            part_type = PART_TYPE[0]
            quantity = 1
        else:
            part_type = PART_TYPE[1]
            part_name, quantity = part_name.split("(")
            quantity = quantity.replace("ea)", "")
        assembly_points = get_assembly_points(step_file, part_name)
        
        furniture_info[part_name] = {
            "class_id": class_id,
            "type": part_type,
            "model_file": step_file.replace(CURRENT_PATH, "."),
            "quantity": int(quantity),
            "assembly_points": assembly_points
        }
    yaml_path = join(FURNITURE_INFO_DIR, yaml_name)
    save_dic_to_yaml(furniture_info, yaml_path)
    # initialize assembly_status
    assembly_status = {}
    furniture_status_dir = join(STATUS_DIR, furniture_name)
    if not os.path.isdir(furniture_status_dir):
        os.mkdir(furniture_status_dir)
    for part_name in furniture_info.keys():
        quantity = furniture_info[part_name]["quantity"]
        for q in range(quantity):
            instance = part_name + "_" + str(q)
            assembly_status[instance] = {}
    yaml_path = join(furniture_status_dir, "initial_status.yaml")
    save_dic_to_yaml(assembly_status, yaml_path)
    



        

