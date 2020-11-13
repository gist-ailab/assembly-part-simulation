from script.socket_utils import *
from script.const import SocketType, InstructionRequestType
from script.fileApi import *

class InstructionModule():
    def __init__(self):
        self.callback = {
            InstructionRequestType.get_instruction_info: self.get_instruction_info
        }
    
    def initialize_server(self):
        print("Initialize Instruction Server")
        host = SocketType.instruction.value["host"]
        port = SocketType.instruction.value["port"]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(True)
        self.host = host
        self.port = port
        try:
            print("Waiting for Instruction client {}:{}".format(self.host, self.port))
            self.connected_client, addr = self.server.accept()
            print("Connected to {}".format(addr))
        except:
            print("Instruction Server Error")
        finally:
            self.server.close()
    
    def get_callback(self, request):
        return self.callback[request]

    def get_instruction_info(self):
        print("ready to extract instruction info")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        group_info = request["group_info"]
        connector_info = request["connector_info"]

        instruction_info = load_yaml_to_dic("instruction/STEFAN/instruction_1.yaml")
        sendall_pickle(self.connected_client, instruction_info)

    def close(self):
        self.connected_client.close()
        self.server.close()


if __name__ == "__main__":
    instruction_module = InstructionModule()
    instruction_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(instruction_module.connected_client)
            print("Get request to {}".format(request))
            callback = instruction_module.get_callback(request)
            callback()
        except:
            break
    instruction_module.close()    