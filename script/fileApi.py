import os
from os.path import join, isfile, isdir, splitext
from os import listdir
import yaml
from datetime import datetime
import logging
import shutil
import json

def get_logger(module_name):
    logger = logging.getLogger(module_name)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel(level=logging.INFO)
    return logger

def get_file_list(path):
    file_list = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    return file_list

def get_dir_list(path):
    dir_list = [join(path, f) for f in listdir(path) if isdir(join(path, f))]

    return dir_list

def get_file_name(path):
    file_path, ext = splitext(path)
    return file_path.split("/")[-1], ext

def save_dic_to_yaml(dic, yaml_path):
    with open(yaml_path, 'w') as y_file:
        _ = yaml.dump(dic, y_file, default_flow_style=False)

def load_yaml_to_dic(yaml_path):
    with open(yaml_path, 'r') as y_file:
        dic = yaml.load(y_file, Loader=yaml.FullLoader)
    return dic

def load_json_to_dic(json_path):
    with open(json_path, 'r') as j_file:
        dic = json.load(j_file)
    return dic

def check_and_create_dir(dir_path):
    if not check_dir(dir_path):
        os.mkdir(dir_path)
        return True
    else:
        return False

def check_and_reset_dir(dir_path):
    if check_dir(dir_path):
        shutil.rmtree(dir_path)
        os.mkdir(dir_path)
        return True
    else:
        os.mkdir(dir_path)
        return False

def check_dir(dir_path):
    return os.path.isdir(dir_path)

def check_file(file_path):
    return os.path.isfile(file_path)

def get_time_stamp():
    return datetime.timestamp(datetime.now())

def relative_path_to_abs_path(rel_path):
    os.path.abspath(rel_path)
    return os.path.abspath(rel_path)
    