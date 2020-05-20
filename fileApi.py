import os
from os.path import join, isfile, isdir
from os import listdir
import yaml
from datetime import datetime
import time

def get_file_list(path):
    file_list = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    return file_list

def get_dir_list(path):
    dir_list = [join(path, f) for f in listdir(path) if isdir(join(path, f))]

    return dir_list

def save_dic_to_yaml(dic, yaml_path):
    with open(yaml_path, 'w') as y_file:
        _ = yaml.dump(dic, y_file, default_flow_style=False)

def load_yaml_to_dic(yaml_path):
    with open(yaml_path, 'r') as y_file:
        dic = yaml.load(y_file, Loader=yaml.FullLoader)

    return dic

def check_and_create_dir(dir_path):
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)
        return True
    else:
        return False

def get_time_stamp():
    return datetime.timestamp(datetime.now())