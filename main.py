import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import get_dir_list, get_file_list, save_dic_to_yaml
from extract_infoApi import initialize_furniture_config, load_instruction_info, initialize_assembly_status
import logging



CURRENT_PATH = os.path.dirname(os.path.realpath(__file__)) # same as "./"
INPUT_PATH = join(CURRENT_PATH, "input")
STEP_FILE_DIR = join(INPUT_PATH, "step_file")

#-------------------------------------------------
FURNITURE_NAME = "STEFAN"

if __name__ == "__main__":
    #---------------------------------------
    #region logger
    
    logger = logging.getLogger(FURNITURE_NAME)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel(level=logging.INFO)
    
    #endregion
    
    #---------------------------------------
    #region initialize
    
    initialize_furniture_config(FURNITURE_NAME, logger)

    #endregion

    #---------------------------------------
    #region assembly for each instruction
    
    instruction_step = 1
    initialize_assembly_status(FURNITURE_NAME, instruction_step, logger)
    instruction = load_instruction_info(instruction_step=instruction_step)
    for part_name in instrcution.keys():
        quantity = instruction[part_name]["quantity"] 
        for idx in range(quantity):
            instance_name = part_name + "_" + str(idx)
            print(instance_name)

    #endregion

    #---------------------------------------
    #region extract assembly sequence


    #endregion
    