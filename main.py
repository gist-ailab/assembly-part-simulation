import logging
import time

from assembly_manger import AssemblyManager

def get_logger(furniture_name):
    logger = logging.getLogger(furniture_name)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel(level=logging.INFO)
    
    return logger

if __name__ == "__main__":
    """
        1. initialize part information from CAD files(*.STEP)
        2. Get Instruction Info and start assembly
        3. Create Assemlby Sequence
    """
    furniture_name = "STEFAN"
    # furniture_name = "meshes_IITP"
    logger = get_logger(furniture_name)
    
    asm_manager = AssemblyManager(logger, furniture_name)
    # assembly simulation
    while not asm_manager.is_end:
        while not asm_manager.check_instruction_info(): 
            time.sleep(2)

        asm_manager.simulate_instruction_step()
        asm_manager.step()

    # create assembly sequence


    """meshes_IITP unique radius
        0 2.0000000000000053
        1 2.499999999999995
        2 2.5000000000000004
        3 2.7499999999999747
        4 2.750000000000001
        5 3.000000000000001
        6 3.0000000000000027
        7 3.4999999999999996
        8 3.5
        9 4.0
        10 4.000000000000001
        11 4.000000000000002
        12 4.000000000000003
        13 4.0000000000000036
        14 5.65
        15 6.0
    """

