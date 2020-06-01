import os
from os.path import join, isfile, isdir
from os import listdir
from fileApi import get_dir_list, get_file_list, save_dic_to_yaml
from extract_infoApi import initialize_furniture_config
from assemblyApi import Assembly_Manager

import logging

#-------------------------------------------------
FURNITURE_NAME = "STEFAN"
instruction_step = 1

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
    
    #---------------------------------------------------
    #region initialize
    # initialize_furniture_config(FURNITURE_NAME, logger)

    #endregion

    #---------------------------------------------------
    #region assembly for each instruction
    assem = Assembly_Manager(FURNITURE_NAME, instruction_step, logger)
    assem.start_assemble()

    #endregion

    #---------------------------------------
    #region extract assembly sequence


    #endregion
    