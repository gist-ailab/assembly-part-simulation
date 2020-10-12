from enum import Enum
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

class Pose(object):
    def __init__(self, position, quaternion):
        self.position = position # [x, y, z]
        self.quaternion = quaternion # [qx, qy, qz, w]

class AssemblyPoint(object):
    def __init__(self, idx, hole_type, radius, edge_index, depth, direction, pose: Pose):
        self.id = idx
        self.hole_type = hole_type
        self.radius = radius
        self.edge_index = edge_index
        self.depth = depth
        self.direction = direction
        self.pose = pose

