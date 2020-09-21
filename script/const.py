from enum import Enum

import os

print(__file__)

#------------------------------------------------------------------------------------
class PartType(Enum):
    furniture = "furniture_part"
    connector = "connector_part"

class FilePath(Enum):
    part_info = ""

class PartInfo(object):
    def __init__(self, part_name, part_type, part_id, model_file, quantity):
        self.name = part_name
        self.type = part_type
        self.id = part_id
        self.model_file = model_file
        self.quantity = quantity
        self.assembly_points = []

class HoleType(Enum):
    hole = 0
    insertion = 1

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

