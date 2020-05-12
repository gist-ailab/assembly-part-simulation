import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import get_dir_list, get_file_list, save_dic_to_yaml
from extract_infoApi import initialize_furniture_config
import logging



CURRENT_PATH = os.path.dirname(os.path.realpath(__file__)) # same as "./"
INPUT_PATH = join(CURRENT_PATH, "input")
STEP_FILE_DIR = join(INPUT_PATH, "step_file")

#-------------------------------------------------
FURNITURE_NAME = "STEFAN"

if __name__ == "__main__":
    logger = logging.getLogger(FURNITURE_NAME)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    
    logger.info("Initialize {} information".format(FURNITURE_NAME))
    initialize_furniture_config(FURNITURE_NAME)
    