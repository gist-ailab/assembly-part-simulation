import yaml
import os
from os.path import join, isfile, isdir
from os import listdir
from freecadApi import get_assembly_points


CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
FURNITURE_INFO_PATH = join(CURRENT_PATH, "furniture_info")
PART_INFO_PATH = join(CURRENT_PATH, "part_info")
PART_TYPE = ["furniture_part", "connector_part"]
if not os.path.isdir(FURNITURE_INFO_PATH):
    os.mkdir(FURNITURE_INFO_PATH)
if not os.path.isdir(PART_INFO_PATH):
    os.mkdir(PART_INFO_PATH)


def get_file_list(path):
    file_list = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    return file_list

def get_dir_list(path):
    dir_list = [join(path, f) for f in listdir(path) if isdir(join(path, f))]

    return dir_list


def save_dic_to_yaml(dic, yaml_path):
    with open(yaml_path, 'w') as y_file:
        _ = yaml.dump(dic, y_file, default_flow_style=False)

def initialize_furniture_config(furniture_name, step_path):
    yaml_name = furniture_name + ".yaml"
    furniture_step_path = join(step_path, furniture_name)
    step_list = get_file_list(furniture_step_path)
    step_list.sort()
    furniture_info = {}
    for class_id, step_file in enumerate(step_list):
        step_name = os.path.splitext(step_file)[0]
        part_name = step_name.replace(furniture_step_path + '/', "")
        part_type = None
        quantity = 0        
        if step_name.find("ea)") == -1:
            part_type = PART_TYPE[0]
            quantity = 1
        else:
            part_type = PART_TYPE[1]
            part_name, quantity = part_name.split("(")
            quantity = quantity.replace("ea)", "")
        
        furniture_info[part_name] = {
            "class_id": class_id,
            "type": part_type,
            "model_file": step_file.replace(CURRENT_PATH, "."),
            "quantity": int(quantity)
        }
    yaml_path = join(FURNITURE_INFO_PATH, yaml_name)
    save_dic_to_yaml(furniture_info, yaml_path)
    initialize_part_info(furniture_name, furniture_info)

def initialize_part_info(furniture_name, furniture_info):
    part_info_dir = join(PART_INFO_PATH, furniture_name + "_part_info")
    if not os.path.isdir(part_info_dir):
        os.mkdir(part_info_dir)
    else:
        pass
    for part_name in furniture_info.keys():
        quantity = furniture_info[part_name]["quantity"]
        step_path =furniture_info[part_name]["model_file"]
        assembly_points = get_assembly_points(step_path, part_name)
        for idx in range(quantity):
            part_info_yaml = part_name + "_" + str(idx) + ".yaml"
            part_info = {
                "type": part_name,
                "assembly_points": assembly_points,
                "assembly_targets": [],
            }
            yaml_path = join(part_info_dir, part_info_yaml)
            save_dic_to_yaml(part_info, yaml_path)

    




initialize_furniture_config("STEFAN", join(CURRENT_PATH, "step_file"))


        

