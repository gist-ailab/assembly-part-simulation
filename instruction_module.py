from script.socket_utils import *
from script.const import SocketType, InstructionRequestType
from script.fileApi import *

class InstructionModule():
    def __init__(self, logger):
        self.logger = logger
        self.callback = {
            InstructionRequestType.get_instruction_info: self.get_instruction_info
        }
    
    def initialize_server(self):
        self.logger.info("Initialize Instruction Server")
        host = SocketType.instruction.value["host"]
        port = SocketType.instruction.value["port"]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(True)
        self.host = host
        self.port = port
        try:
            self.logger.info("Waiting for Instruction client {}:{}".format(self.host, self.port))
            self.connected_client, addr = self.server.accept()
            self.logger.info("Connected to {}".format(addr))
        except:
            self.logger.info("Instruction Server Error")
        finally:
            self.server.close()
    
    def get_callback(self, request):
        return self.callback[request]

    def get_instruction_info(self):
        self.logger.info("ready to extract instruction info")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        current_step = request["current_step"]
        group_info = request["group_info"]
        connector_info = request["connector_info"]
        try:
            instruction_info = load_yaml_to_dic("instruction/STEFAN/example_instruction_{}.yaml".format(current_step))
        except:
            instruction_info = {}
        sendall_pickle(self.connected_client, instruction_info)

    def close(self):
        self.connected_client.close()
        self.server.close()


if __name__ == "__main__":
    logger = get_logger("Instruction_Module")
    instruction_module = InstructionModule(logger)
    instruction_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(instruction_module.connected_client)
            logger.info("Get request to {}".format(request))
            callback = instruction_module.get_callback(request)
            callback()
        except Exception as e:
            logger.info("Error occur {}".format(e))
            break
    instruction_module.close()    