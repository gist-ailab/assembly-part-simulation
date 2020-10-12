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
    logger = get_logger(furniture_name)
    
    asm_manager = AssemblyManager(logger, furniture_name)
    # assembly simulation
    while not asm_manager.is_end:
        while not asm_manager.check_instruction_info(): 
            time.sleep(2)

        asm_manager.simulate_instruction_step()
        asm_manager.step()

    # create assembly sequence

