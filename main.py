import argparse
from script.fileApi import get_logger

from assembly_manager import AssemblyManager

def get_args_parser():
    parser = argparse.ArgumentParser('Set IKEA Assembly Part Simulation', add_help=False)
    parser.add_argument('--furniture_name', default='STEFAN', type=str)
    return parser

# test for joosoon branch

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

    #region initialize
    # Assembly manager    
    asm_manager = AssemblyManager(logger, furniture_name)

    # initialize part information from CAD
    asm_manager.initialize_CAD_info()

    # initialize group info using part info
    asm_manager.update_group_info()

    # initialize pyrep scene
    asm_manager.initialize_pyrep_scene()
    #endregion

    #region simulate assembly
    # get instruction info 
    asm_manager.get_instruction_info()
        
    # assembly simulation
    while not asm_manager.is_end: # end sign from instruction_info
        # extract assembly info 
        asm_manager.extract_assembly_info()

        # search assembly sequence
        asm_manager.search_assemble_sequences()

        # assemble parts and calculate cost by distance taken during assembly
        asm_manager.simulate_instruction_step()
        
        #TODO 설명서에서 나오지 않은 추가적인 결합 체크
        asm_manager.check_hidden_assembly()

        asm_manager.step()
    #endregion

    logger.info("SUCCESS!")

