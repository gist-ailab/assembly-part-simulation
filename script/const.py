from enum import Enum, auto
import os


#------------------------------------------------------------------------------------
class PartType(Enum):
    furniture = "furniture_part"
    connector = "connector_part"

class HoleType(Enum):
    hole = "hole"
    insertion = "insertion"
    penetration = "penetration"

class AssemblyType(Enum):
    group_group = 0
    group_connector_group = 1
    group_connector = 2

class GroupAssembly():
    def __init__(self, assembly_type, assembly_parts):
        self.assembly_type = assembly_type
        self.assembly_parts = assembly_parts    

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

class AssemblyPair(object):
    def __init__(self, part1, part2, point1, point2, offset=0):
        self.part_name1 = part1
        self.part_name2 = part2
        self.assembly_point1 = point1
        self.assembly_point2 = point2
        self.direction = True
        self.offset = offset

class PyRepRequestType(Enum):
    initialize_scene = auto
    get_region = auto

class FreeCADRequestType(Enum):
    initialize_cad_info = auto
class SocketType(Enum):
    pyrep = {
        "host": '127.0.0.1',
        "port": 8282,
        "request_type": PyRepRequestType,
    }
    freecad = {
        "host": '127.0.0.1',
        "port": 9292,
        "reqeust_type": FreeCADRequestType,
    }


