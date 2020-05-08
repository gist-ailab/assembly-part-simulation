
import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import get_dir_list, get_file_list
from freecadApi import get_assembly_points


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__)) # same as "./"
FURNITURE_INFO_PATH = join(CURRENT_PATH, "furniture_info") # save furniture information directory
if not os.path.isdir(FURNITURE_INFO_PATH):
    os.mkdir(FURNITURE_INFO_PATH)
PART_TYPE = ["furniture_part", "connector_part"]


def initialize_furniture_config(furniture_name):
    yaml_name = furniture_name + ".yaml"
    step_path = join(CURRENT_PATH, "step_file", furniture_name)
    step_list = get_file_list(step_path)
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
    yaml_path = join(FURNITURE_INFO_PATH, yaml_name)
    save_dic_to_yaml(furniture_info, yaml_path)

initialize_furniture_config("STEFAN")
initialize_furniture_config("FURNITURE_NAME")


        

