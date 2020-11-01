import argparse
import logging
import time

# from assembly_manger import AssemblyManager
from assembly_manager_joo import AssemblyManager


def get_args_parser():
    parser = argparse.ArgumentParser('Set IKEA Assembly Part Simulation', add_help=False)
    parser.add_argument('--furniture_name', default='STEFAN', type=str)
    return parser

def get_logger(furniture_name):
    logger = logging.getLogger(furniture_name)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)
    logger.setLevel(level=logging.INFO)
    return logger

# test for joosoon branch
# test for raeyo branch

if __name__ == "__main__":
    """
        1. initialize part information from CAD files(*.STEP)
        2. Get Instruction Info and start assembly
        3. Create Assemlby Sequence
    """

    parser = argparse.ArgumentParser('Assembly Part Simulator', parents=[get_args_parser()])
    args = parser.parse_args()
    furniture_name = args.furniture_name
    logger = get_logger(furniture_name)

    # Assembly manager    
    asm_manager = AssemblyManager(logger, furniture_name)

    # initialize part information from CAD
    asm_manager.initialize_CAD_info()
    
    # assembly simulation
    while not asm_manager.is_end:
        # get instruction info 
        while not asm_manager.check_instruction_info(): 
            time.sleep(10)

        # extract assembly info 
        asm_manager.extract_assembly_info()

        # search assembly sequence
        asm_manager.search_assemble_sequences()

        # assemble parts and calculate cost by distance taken during assembly
        asm_manager.simulate_instruction_step()
        
        # 설명서에서 나오지 않은 추가적인 결합 체크
        asm_manager.check_hidden_assembly()

        # update group status
        asm_manager.update_group_status()
        asm_manager.step()

    # create assembly sequence

