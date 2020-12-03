from enum import Enum, auto

class PartType(Enum):
    furniture = "furniture_part"
    connector = "connector_part"

class HoleType(Enum):
    hole = "hole"
    insertion = "insertion"
    penetration = "penetration"

class AssemblyType(Enum):
    group_connector_group = [
        {1:"group", 2:"connector", 3:"group"}
    ]
    group_connector = [
        {1:"group", 2:"connector"},
        {1:"connector", 2:"group"}
    ]
    group_group_connector = [
        {1:"group", 2:"group", 3:"connector"},
        {3:"group", 2:"group", 1:"connector"},
    ]
    @classmethod
    def find_type(cls, assemblyType):
        if assemblyType in cls.group_connector.value:
            return cls.group_connector
        elif assemblyType in cls.group_connector_group.value:
            return cls.group_connector_group
        elif assemblyType in cls.group_group_connector.value:
            return cls.group_group_connector
        else:
            assert False


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
    initialize_part_to_scene = "initialize_part_to_scene"
    update_group_to_scene = "update_group_to_scene"
    get_assembly_point = "get_assembly_point"
    update_part_status = "update_part_status"

class FreeCADRequestType():
    initialize_cad_info = "initialize_cad_info"
    check_assembly_possibility = "check_assembly_possibility"
    extract_group_obj = "extract_group_obj"

class InstructionRequestType():
    get_instruction_info = "get_instruction_info"

class SocketType(Enum):
    pyrep = {
        "host": '172.27.183.179',
        "port": 8282,
        "request_type": PyRepRequestType,
    }
    freecad = {
        "host": '172.27.183.179',
        "port": 9293,
        "reqeust_type": FreeCADRequestType,
    }
    instruction = {
        "host": '172.27.183.179',
        # "host": '172.27.183.205', # hinton
        "port": 7777,
        "reqeust_type": InstructionRequestType,
    }
    blender = {
        "host": '172.27.183.179',
        # "host": '172.27.183.205', # hinton
        "port": 7942,
        "reqeust_type": BlenderRequestType,
    }

