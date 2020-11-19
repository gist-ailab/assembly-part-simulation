from enum import Enum, auto

class PartType(Enum):
    furniture = "furniture_part"
    connector = "connector_part"

class HoleType(Enum):
    hole = "hole"
    insertion = "insertion"
    penetration = "penetration"

class AssemblyType:
    group_group = "group_group"
    group_connector_group = "group_connector_group"
    group_connector = "group_connector"

class AssemblyPoint(object):
    def __init__(self, idx, hole_type, radius, edge_index, depth, direction, position, quaternion):
        self.id = idx
        self.hole_type = hole_type
        self.radius = radius
        self.edge_index = edge_index
        self.depth = depth
        self.direction = direction
        self.position = position
        self.quaternion = quaternion

class PyRepRequestType():
    initialize_scene = "initialize_scene"
    initialize_instruction_scene = "initialize_instruction_scene"
    update_instruction_scene = "update_instruction_scene"

class FreeCADRequestType():
    initialize_cad_info = "initialize_cad_info"
    check_assembly_possibility = "check_assembly_possibility"
    extract_group_obj = "extract_group_obj"

class InstructionRequestType():
    get_instruction_info = "get_instruction_info"

class SocketType(Enum):
    pyrep = {
        "host": '127.0.0.1',
        "port": 8282,
        "request_type": PyRepRequestType,
    }
    freecad = {
        "host": '127.0.0.1',
        "port": 9293,
        "reqeust_type": FreeCADRequestType,
    }
    instruction = {
        "host": '127.0.0.1',
        "port": 7777,
        "reqeust_type": InstructionRequestType,
    }
