from os import stat
from yaml import compose

from yaml.events import DocumentEndEvent
from script import import_fcstd
import FreeCAD
import FreeCADGui
FreeCADGui.showMainWindow()

import Part
from FreeCAD import Base
import importOBJ
import Mesh
import Draft

import a2plib
from a2p_importpart import importPartFromFile
import a2p_constraints as a2pconst
from a2p_solversystem import SolverSystem
solver = SolverSystem()

from script.timeout import timeout
"""document of SolverSystem()
1. solveSystem(doc, matelist=None, showFailMessage=True)
    - same as Gui Solve system Icon
    - composed by SolverSystem::solveAccuracySteps and SolverSystem::checkForUnmovedParts
    - if can not solve system(contraints mismatching) return False and show msg(if showFailMessage=True)
2.solveAccuracySteps
    - 실제로 문제를 푸는 곳
    - 문제를 풀면 True 못 풀면 False 반환
    - 이때, 물체 고정을 잘 못 시켰을 때도 True 반환(움직일 수 있는 건 다 풀었다)
3. checkForUnmovedParts
    - 안 움직인 물체를 확인하는 작업으로 물체를 잘못 움직였을 경우
    - len(self.unmovedParts) > 0 이다.
"""

from scipy.spatial.transform import Rotation as R
import numpy as np
import copy
from os.path import join
import socket
from enum import Enum
import threading
import copy
import time

from script.const import SocketType, FreeCADRequestType, PartType
from script.fileApi import *
from script.socket_utils import *


PART_INFO = None
temp_doc_path = "./test.FCStd"
unique_radius = []

# hole direction condition(matched with step name)
hole_condition = {
    "ikea_stefan_bolt_side": [0, 1, 2],
    "ikea_stefan_bracket": [1, 2],
    "ikea_stefan_pin": [],
    "pan_head_screw_iso(4ea)": [0,1,2],
    "ikea_stefan_bottom": [],
    "ikea_stefan_long": [3,4,5,7,8,9,10,11],
    "ikea_stefan_middle": [0,1,2,6,7,8,9,11],
    "ikea_stefan_short": [3,4,5,7,8,9,10,11],
    "ikea_stefan_side_left": [3,7,12],
    "ikea_stefan_side_right": [0,1,2,4,5,6,8,9,10,11,13,14,15, 16, 17, 18, 19],
}
"""STEFAN unique radius
    0 2.499999999999989 => pin
    1 2.499999999999995 => pin
    2 2.5000000000000004 => long, short for flat head penet
    3 2.7499999999999747 => side hole for flat head penet
    4 2.750000000000001 => side hole for flat head penet
    5 3.000000000000001 => braket penetration
    6 3.0000000000000027 => long, short hole for braket
    7 3.4999999999999996 => short hole for pin
    8 3.5 => braket insert
    9 4.0 => long hole for pin 
    10 4.000000000000001 => middle hole for pin
    11 4.000000000000002 => middle hole for pin
    12 4.000000000000003 => middle hole for pin
    13 4.0000000000000036 => side hole for pin
    14 5.65 => flat head
    15 6.0 => pan head
"""
# pair condition
radius_group = {
    "pin group": [0, 1, 7, 9, 10, 11, 12, 13],
    "braket group": [5, 6, 8],
    "flat_penet group": [2, 3, 4, 14],
    "pan": [15]
}
# region condition
region_condition = {
    "ikea_stefan_bottom": {
        
    },
    "ikea_stefan_long": {
        0: [0,1,2],
        1: [3,4,5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_middle": {
        0: [0, 1, 2],
        1: [3, 4, 5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_short": {
        0: [0,1,2],
        1: [3,4,5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_side_left": {
        0: [0,1,2,10],
        1: [4,5,6,12],
        2: [3,8,9,11],
        3: [7]
    },
    "ikea_stefan_side_right": {
        0: [0,1,2,10],
        1: [4,5,6,12],
        2: [3,8,9,11],
        3: [7]
    },
}
bottom_condition = [
    # hole for short
    {
        "radius": 6.1,
        "depth": 1,
        "position": Base.Vector(80, 163.685, 0),
        "direction": Base.Vector(0, 0, 1)
    },
    {
        "radius": 6.1,
        "depth": 1,
        "position": Base.Vector(-80, 163.685, 0),
        "direction": Base.Vector(0, 0, 1)
    },
    # hole for long
    {
        "radius": 6.1,
        "depth": 1,
        "position": Base.Vector(112, -163.685, 0),
        "direction": Base.Vector(0, 0, 1)
    },
    {
        "radius": 6.1,
        "depth": 1,
        "position": Base.Vector(-112, -163.685, 0),
        "direction": Base.Vector(0, 0, 1)
    },
]
bolt_condition = {
    "ikea_stefan_side_left": [0, 3, 4],
    "ikea_stefan_side_right": [0, 3, 4]
}

class AssembleDirection(Enum):
    aligned = "aligned"
    opposed = "opposed"

#region custom class
class Circle(object):
    def __init__(self, radius, edge, position, XAxis, YAxis, ZAxis):
        self.radius = radius
        self.edge = edge
        self.position = position
        self.XAxis = XAxis
        self.YAxis = YAxis
        self.direction = ZAxis
        self.quaternion = get_quat_from_dcm(self.XAxis, self.YAxis, self.direction)
        self.edge_index = 0
        self.is_reverse = False

    def create_circle(self):
        position = Base.Vector(self.position)
        direction = Base.Vector(self.direction)
        self.shape = Part.makeCircle(self.radius, position, direction, 0, 360)

    def visualize_circle(self, doc, name="circle"):
        FreeCAD.setActiveDocument(doc.Name)
        name += "_" + str(self.radius)
        try:
            Part.show(self.shape, name)
        except:
            print("first create circle")
        self.object = doc.ActiveObject

    def get_edge_index_from_shape(self, shape):
        edges = shape.Edges
        find_edge = False
        for ind, edge in enumerate(edges):
            if not check_circle_edge(edge):
                continue
            if edge.isSame(self.edge):
                circle = edge.Curve
                z_axis = [circle.Axis.x, circle.Axis.y, circle.Axis.z]
                count = 0
                for i in range(3):
                    count += z_axis[i] * self.direction[i]
                if count > 0:
                    self.edge_index = [ind + 1, "aligned"]
                    find_edge = True
                else:
                    self.edge_index = [ind + 1, "opposed"]
                    find_edge = True
        
        if not find_edge:
            print("ERROR no edge same with circle")

    def get_position_m(self):
        position = np.array(self.position) * 0.001

        return list(position)

    def reverse(self): # rotate based on y axis
        self.direction = [-1 * val for val in self.direction]
        self.XAxis = [-1* val for val in self.XAxis]
        self.quaternion = get_quat_from_dcm(self.XAxis, self.YAxis, self.direction)

class Hole():
    def __init__(self, position, direction, circle):
        self.position = position
        self.direction = direction
        self.circle_group = [circle]
        self.start_circle = circle
        self.radius_min = circle.radius
        self.radius_max = circle.radius
        self.min_value = np.inner(np.array(circle.position), np.array(self.direction))
        self.max_value = self.min_value
        self.depth = 0

    def check_circle_in_hole(self, circle):
        dif_dir = np.linalg.norm(np.array(self.direction)- np.array(circle.direction))
        if not dif_dir < 0.0001:
            return False
        if self.position == circle.position:
            return True
        dif_vec = np.array(self.position) - np.array(circle.position)
        direction = np.array(self.direction)
        parallel = check_parallel(dif_vec, direction)
        if parallel:
            return True
        else:
            return False
    
    def add_circle(self, circle):
        """add circle to circle_group

        Arguments:
            circle {Circle} -- [description]
        """
        self.circle_group.append(circle)
        dir_pos = np.inner(np.array(circle.position), np.array(self.direction))
        if dir_pos < self.min_value:
            self.start_circle = circle                
            self.min_value = dir_pos
        if dir_pos > self.max_value:
            self.max_value = dir_pos
        if circle.radius < self.radius_min:
            self.radius_min = circle.radius
        if circle.radius > self.radius_max:
            self.radius_max = circle.radius
        self.update_depth()

    def update_depth(self):
        self.depth = float(self.max_value - self.min_value)
    
    def create_hole(self):
        position = Base.Vector(self.start_circle.position)
        direction = Base.Vector(self.direction)
        radius = self.radius_min
        self.shape = Part.makeCylinder(radius, self.depth, position, direction, 360)

    def visualize_hole(self, doc, name="hole"):
        FreeCAD.setActiveDocument(doc.Name)
        try:
            Part.show(self.shape, name)
        except:
            print("first create hole")
        self.object = doc.ActiveObject

    def set_hole_type(self, doc, parent_obj):
        is_collision = check_collision(doc, parent_obj, self.object)
        if is_collision:
            self.type = "insertion"
            self.radius = self.radius_max
        else:
            self.type = "hole"
            self.radius = self.radius_min
        
        self.object.Label += self.type
    
    def remove_hole(self, doc):
        doc.removeObject(self.object.Name)

    def visualize_frame(self, doc):
        obj_O = Base.Vector(self.start_circle.position)
        xyz = get_dcm_from_quat(self.start_circle.quaternion)
        obj_axis = {
            "x": Base.Vector(xyz[0]),
            "y": Base.Vector(xyz[1]),
            "z": Base.Vector(xyz[2])
        }
        for idx, axis_name in enumerate(obj_axis.keys()):
            frame_name = "hole_axis_" + str(self.radius) + axis_name 
            frame = doc.addObject("Part::Polygon", frame_name)
            frame.Nodes = [obj_O, obj_O + obj_axis[axis_name]]
            doc.recompute()
            color = [0., 0., 0.]
            color[idx] = 1.0
            set_obj_color(doc, frame, tuple(color))

class AssemblyDocument(object):
    def __init__(self, doc_path=temp_doc_path):
        if doc_path == temp_doc_path:
            self.doc = FreeCAD.newDocument()
            self.save_doc(doc_path)
        else:
            self.doc = open_doc(doc_path)
        FreeCAD.setActiveDocument(self.doc.Name)
        FreeCADGui.setActiveDocument(self.doc.Name)

        self.gui_doc = FreeCADGui.getDocument(self.doc.Name)
        self.initial_path = doc_path
        self.current_path = doc_path
        self.used_assembly_pair = []
        self.objects_constraint = {}
    
    def import_part(self, part_path, pos=[0, 0, 0], ypr=[0,0,0]):
        obj = importPartFromFile(self.doc, part_path)
        obj.Placement.Base = FreeCAD.Vector(pos)
        obj.Placement.Rotation = FreeCAD.Rotation(ypr[0], ypr[1], ypr[2])
        self.set_view()
        return obj
    
    def check_assembly_pair(self, pair_assembly_info):
        if pair_assembly_info in self.used_assembly_pair:
            return True
        else:
            return False
    
    def add_assembly_pair(self, pair_assembly_info):
        self.used_assembly_pair.append(pair_assembly_info)

    def add_circle_constraint(self, obj1, obj2, edge_pair: tuple, direction, offset=0):
        return constraint_two_circle(doc=self.doc, parent_obj=obj1, child_obj=obj2,
                                parent_edge=edge_pair[0], child_edge=edge_pair[1],
                                direction=direction, offset=offset)

    def add_parallel_plane_constraint(self, obj1, obj2, face_pair: tuple, direction):
        return constraint_parallel_face(doc=self.doc, parent_obj=obj1, child_obj=obj2,
                                parent_face=face_pair[0], child_face=face_pair[1],
                                direction=direction)
    
    def add_coincident_plane_constraint(self, obj1, obj2, face_pair: tuple, direction, offset=0):
        contraint_coinsident_face(doc=self.doc, parent_obj=obj1, child_obj=obj2,
                                parent_edge=face_pair[0], child_edge=face_pair[1],
                                direction=direction, offset=offset)
    
    def assemble(self, obj1, obj2, edge_pair, direction, offset=0):
        self.add_circle_constraint(obj1, obj2, edge_pair, direction, offset=0)
        self.solve_system()

    def solve_system(self):
        is_solved = solver.solveAccuracySteps(self.doc, None)
        self.set_view()
        return is_solved

    def check_unmoved_parts(self):
        if len(solver.unmovedParts) > 0:
            return True
        else:
            return False

    def get_object_by_name(self, obj_name):
        return self.doc.getObject(obj_name)
    
    def remove_object(self, obj):
        self.doc.removeObject(obj.Name)

    def save_doc(self, path):
        save_doc_as(self.doc, path)
        self.current_path = path

    def show(self):
        FreeCAD.setActiveDocument(self.doc.Name)
        FreeCADGui.setActiveDocument(self.doc.Name)
        self.gui_doc = FreeCADGui.getDocument(self.doc.Name)
    
    def set_view(self):
        self.gui_doc.ActiveView.fitAll()
        self.gui_doc.ActiveView.viewIsometric()

    def reset(self):
        close_doc(self.doc)
        self.doc = open_doc(self.initial_path)
        FreeCAD.setActiveDocument(self.doc.Name)
        FreeCADGui.setActiveDocument(self.doc.Name)
        self.gui_doc = FreeCADGui.getDocument(self.doc.Name)
    
    def close(self):
        close_doc(self.doc)

#endregion

#region math calculate
def get_quat_from_dcm(x, y, z):
    r = R.from_dcm(np.array([x, y, z]))
    r = r.as_quat()
    r = list(r)
    return r

def get_dcm_from_quat(quat):
    r = R.from_quat(quat)
    r = r.as_dcm()
    r = list(r)

    return r

def get_quat_from_euler(x ,y, z):
    r = R.from_euler("xyz",[x, y, z], degrees=True)
    r = r.as_quat()
    r = list(r)
    
    return r

def check_parallel(vec1, vec2):
    epsilon = 0.001
    inner_product = np.inner(vec1, vec2)
    length_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    if length_product == 0:
        return None
    if inner_product / length_product > 1 - epsilon:
        return True
    elif inner_product / length_product < -1 + epsilon:
        return True
    else:
        return False

def npfloat_to_float(np_float_list):
    f_list = []
    for val in np_float_list:
        f_list.append(float(val))
    
    return f_list
#endregion

#region custom functions
def get_circles(obj, reverse_condition):
    """get circle wires from obj<Part::PartFeature> which has Solid Shape
    """
    shape = obj.Shape
    circle_wires = []
    for idx, f in enumerate(shape.Faces):
        wires = f.Wires
        for wire in wires:
            is_circle = True
            if not check_plane_wire(wire):
                continue
            edges = wire.Edges
            for edge in edges:
                if not check_circle_edge(edge):
                    is_circle = False
            if is_circle:
                circle_wires.append(wire)

    circles = get_unique_circle(circle_wires)
    for idx, circle in enumerate(circles):
        if idx in reverse_condition:
            circle.reverse()
        circle.get_edge_index_from_shape(obj.Shape) # may be find aligned edge
        circle.create_circle()


    return circles
def check_plane_wire(wire):
    is_plane = True
    plane_condition = 1e-3
    bbox = wire.BoundBox
    X_Length = bbox.XLength
    Y_Length = bbox.YLength
    Z_Length = bbox.ZLength
    if X_Length < plane_condition or Y_Length < plane_condition or Z_Length < plane_condition:
        pass
    else:
        is_plane = False
    
    return is_plane    
def check_circle_edge(edge):
    is_circle = True
    try:
        if(isinstance(edge.Curve, Part.Circle)):
            pass
        else:
            is_circle = False
    except:
        is_circle = False

    return is_circle
def get_unique_circle(circle_wires):
    circles = []
    unique_property = []
    for wire in circle_wires:
        circle_edges = wire.Edges
        for edge in circle_edges:
            circle = edge.Curve
            position = [circle.Center.x, circle.Center.y, circle.Center.z]
            radius = circle.Radius
            XAxis = [circle.XAxis.x, circle.XAxis.y, circle.XAxis.z]
            YAxis = [circle.YAxis.x, circle.YAxis.y, circle.YAxis.z]
            ZAxis = [circle.Axis.x, circle.Axis.y, circle.Axis.z] # == direction of circle
            pos_r = tuple(position + [radius])
            if pos_r in unique_property:
                pass
            else:
                circles.append(Circle(radius, edge, position, XAxis, YAxis, ZAxis))
                unique_property.append(pos_r)
    
    
    return circles
    
def get_circle_holes(circles):
    circle_holes = []
    for circle in circles:
        is_used = False
        for hole in circle_holes:
            if hole.check_circle_in_hole(circle):
                hole.add_circle(circle)
                is_used = True
        if not is_used:
            circle_holes.append(Hole(circle.position, circle.direction, circle))
    
    return circle_holes

def check_collision(doc, obj1, obj2):
    is_collision = False
    common_area = calculate_common_area(doc, obj1, obj2)
    if common_area > 0:
        is_collision = True
    else:
        # count = get_proximity_faces_num(obj1.Shape, obj2.Shape)
        # print(count)
        pass
    return is_collision
def calculate_common_area(doc, obj1, obj2):
    common_name = "Common"
    common = doc.addObject("Part::MultiCommon",common_name)
    common.Shapes = [obj1, obj2]
    doc.recompute()

    common_area = common.Shape.Area

    doc.removeObject("Common")
    set_obj_visibility(obj1.Name)
    set_obj_visibility(obj2.Name)
    doc.recompute()

    return common_area

def get_proximity_faces_num(shape1, shape2):
    #TODO: have inf loop issue
    count = 0
    for face_list in shape1.proximity(shape2):
        for f in face_list:
            count += 1
    
    return count

def set_obj_visibility(obj_name, visible=True):
    gui_doc = FreeCADGui.ActiveDocument
    gui_obj = gui_doc.getObject(obj_name)
    gui_obj.Visibility = visible

def set_obj_pose(obj, position, quaternion):
    obj.Placement.Base = FreeCAD.Vector(position)
    obj.Placement.Rotation = FreeCAD.Vector(quaternion)

def constraint_two_circle(doc, parent_obj, child_obj, parent_edge, child_edge, direction, offset):
    # parent_obj.fixedPosition = True
    # child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Edge" + str(parent_edge))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Edge" + str(child_edge))
    cc = a2pconst.CircularEdgeConstraint([s1, s2])
    co = cc.constraintObject
    co.directionConstraint = direction
    co.offset = offset
    return co

def constraint_parallel_face(doc, parent_obj, child_obj, parent_face, child_face, direction):
    parent_obj.fixedPosition = True
    child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Face" + str(parent_face))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Face" + str(child_face))
    cc = a2pconst.PlanesParallelConstraint([s1, s2])
    co = cc.constraintObject
    co.directionConstraint = direction
    return co

def contraint_coinsident_face(doc, parent_obj, child_obj, parent_face, child_face, direction, offset):
    parent_obj.fixedPosition = True
    child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Face" + str(parent_face))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Face" + str(child_face))
    cc = a2pconst.PlaneConstraint([s1, s2])
    co = cc.constraintObject
    co.directionConstraint = direction
    co.offset = offset

def get_distance_between_edges(edge1, edge2):
    
    return edge1.Curve.Location.distanceToPoint(edge2.Curve.Location)

def set_obj_color(doc, obj, color):
    gui_doc = FreeCADGui.getDocument(doc.Name)
    gui_obj = gui_doc.getObject(obj.Name)
    gui_obj.LineColor = color

#endregion

def extract_part_info(cad_path):
    """extract furniture's part info from cad files

    Returns:
        [type]: [description]
    """
    part_info = {}
    cad_dir_list = get_dir_list(cad_path)
    part_document_path = "./assembly/STEFAN/part_documents"
    check_and_reset_dir(part_document_path)
    obj_root_path = "./assembly/STEFAN/part_obj"
    check_and_create_dir(obj_root_path)
    part_id = 0
    cad_dir_list.sort()
    for cad_dir in cad_dir_list:
        if PartType.furniture.value in cad_dir:
            part_type = PartType.furniture
        elif PartType.connector.value in cad_dir:
            part_type = PartType.connector
        else:
            print("unknown part type")
            exit()
        cad_list = get_file_list(cad_dir)
        cad_list.sort()
        for cad_file in cad_list:
            _, part_name = os.path.split(cad_file)
            part_name = os.path.splitext(part_name)[0]
            doc_path = join(part_document_path, part_name+".FCStd")
            obj_path = join(obj_root_path, part_name+".obj")
            assembly_points = extract_assembly_points(step_path=cad_file,
                                                      step_name=part_name,
                                                      doc_path=doc_path,
                                                      obj_path=obj_path,
                                                      part_type=part_type,
                                                      )
            if part_name in region_condition.keys():
                region = region_condition[part_name]
                region_info = {}
                for region_id in region.keys():
                    region_points = region[region_id]
                    average_position = np.zeros(3)
                    for region_point_idx in region_points:
                        position = np.array(assembly_points[region_point_idx]["pose"]["position"])
                        average_position += position
                    average_position /= len(region_points)
                    region_info[region_id] = {
                        "points": region_points,
                        "position": npfloat_to_float(average_position)
                    }
            else:
                region_info = {}
            
            part_info[part_name] = {
                "part_id": part_id,
                "type": part_type.value,
                "document": doc_path,
                "obj_file": obj_path,
                "step_file": cad_file,
                "assembly_points": assembly_points,
                "region_info": copy.deepcopy(region_info)
            }
            part_id += 1
    return part_info

def extract_assembly_points(step_path, step_name, doc_path, obj_path, part_type):
    global unique_radius
    """extract assembly_points from step file

    Arguments:
        step_path {string} -- [step file path]

    Returns:
        assembly_points {list} -- [list of assembly_point]
        assembly_point {dict} -- 
        {
            "id": int
            "pose": {
                "xyz": [float list]
                "quaternion": [float list]
            }
            "is_used": False
        }
    """
    # create document
    doc_name = step_name
    doc = FreeCAD.newDocument(doc_name)

    # load step to document
    FreeCAD.setActiveDocument(doc.Name)
    Part.insert(step_path, doc.Name)    
    obj = doc.ActiveObject
    obj.Label = part_type.value
    Mesh.export([obj], obj_path)
    
    #region extract circles
    reverse_condition = hole_condition[step_name]
    
    circles = get_circles(obj, reverse_condition)

    if "pin" in step_name:
        mid_circle1 = copy.deepcopy(circles[0])
        mid_circle2 = copy.deepcopy(circles[1])
        position = [val1/2 + val2/2 for val1, val2 in zip(mid_circle1.position, mid_circle2.position)]
        mid_circle1.position = position
        mid_circle2.position = position
        circles += [mid_circle1, mid_circle2]
    
    #endregion

    # extract circle holes
    circle_holes = get_circle_holes(circles)

    # if "bolt_side" in step_name:
    #     mid_circle = copy.deepcopy(circles[-1])
    #     position = [val1/2 + val2/2 for val1, val2 in zip(circles[0].position, circles[-1].position)]
    #     mid_circle.position = position
    #     added_circles = [mid_circle, circles[-1]]
    #     circle_holes += get_circle_holes(added_circles)
        
    for hole in circle_holes:
        hole.create_hole()
        hole.visualize_hole(doc)
        hole.set_hole_type(doc, obj)
        hole.remove_hole(doc) # TODO: if not to do this error occur when assembly
        # hole.start_circle.visualize_circle(doc)
        # hole.visualize_frame(doc)
        if hole.radius in unique_radius:
            pass
        else:
            unique_radius.append(hole.radius)
            unique_radius.sort()
    
    # if "bolt_side" in step_name:
    #     circle_holes[1].radius = 7.9
    if "bracket" in step_name:
        circle_holes[1].radius = 8.0

    # extract assembly point from circle holes
    assembly_points = []
    for hole in circle_holes:
        assembly_point = {
            "type": hole.type,
            "radius": hole.radius,
            "edge_index": hole.start_circle.edge_index,
            "depth": hole.depth * 0.001,
            "direction": hole.direction,
            "pose": {
                "position": npfloat_to_float(hole.start_circle.get_position_m()),
                "quaternion": npfloat_to_float(hole.start_circle.quaternion)
            },
        }
        assembly_points.append(assembly_point)
    if "bracket" in step_name:
        assembly_points[1]["type"] = "penet"
        new_point = copy.deepcopy(assembly_points[1])
        new_point["radius"] = 6.2
        assembly_points.append(new_point)

    if step_name in bolt_condition.keys():
        point_list = bolt_condition[step_name]
        for point_idx in point_list:
            assembly_points[point_idx]["type"] = "penet"
            new_point = copy.deepcopy(assembly_points[point_idx])
            new_point["radius"] = 7.9
            assembly_points.append(new_point)

    temp = {}
    for idx, val in enumerate(assembly_points):
        temp[idx] = val
    assembly_points = temp
    doc.saveAs(doc_path)
    FreeCAD.closeDocument(doc.Name)
    return assembly_points

def open_doc(filepath):
    doc = FreeCAD.openDocument(filepath)
    # time.sleep(1)
    return doc

def save_doc_as(doc, filepath):
    doc.saveAs(filepath)

def close_doc(doc):
    FreeCAD.closeDocument(doc.Name)

def setview():
    """Rearrange View"""
    FreeCAD.Gui.SendMsgToActiveView("ViewFit")
    FreeCAD.Gui.activeDocument().activeView().viewAxometric()

def create_assembly_doc(doc_name, part_doc):
    doc = FreeCAD.newDocument(doc_name)
    obj = importPartFromFile(doc, part_doc)
    
    return doc

class FreeCADModule():
    def __init__(self, logger):
        self.logger = logger
        self.callback = {
            FreeCADRequestType.initialize_cad_info: self.initialize_cad_info,
            FreeCADRequestType.check_assembly_possibility: self.check_assembly_possibility,
            FreeCADRequestType.extract_group_obj: self.extract_group_obj
        }
        self.main_window = FreeCADGui.getMainWindow()
        self.App = FreeCAD
        self.Gui = FreeCADGui
        

        # 조립에 사용하는 변수들
        self.part_info = None
        self.furniture_parts = []
    
        self.assembly_doc_path = "./assembly_document"
        check_and_reset_dir(self.assembly_doc_path)
        self.assembly_docs = {} 
        self.assembly_doc = None
        self.assembly_obj = {}
        self.assembly_pair = []
        self.additional_assmbly_pair = []
        
    def get_callback(self, request):
        return self.callback[request]
    
    def close(self):
        while self.App.ActiveDocument:
            self.App.closeDocument(self.App.ActiveDocument.Name)
        self.main_window.close()
        self.connected_client.close()
        self.server.close()

    #region socket
    def initialize_server(self):
        self.logger.info("Initialize FreeCAD Server")
        host = SocketType.freecad.value["host"]
        port = SocketType.freecad.value["port"]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(True)
        self.host = host
        self.port = port
        try:
            self.logger.info("Waiting for FreeCAD client {}:{}".format(self.host, self.port))
            self.connected_client, addr = self.server.accept()
            self.logger.info("Connected to {}".format(addr))
        except:
            self.logger.info("FreeCAD Server Error")
        finally:
            self.server.close()
    
    def initialize_cad_info(self):
        self.logger.info("ready to extract part info")
        sendall_pickle(self.connected_client, True)
        cad_file_path = recvall_pickle(self.connected_client)
        self.logger.info("Extract part info from {}".format(cad_file_path))
        self.part_info = extract_part_info(cad_file_path)
        self._initialize_each_parts()
        self.logger.info("Success to extract part info from {}".format(cad_file_path))
        sendall_pickle(self.connected_client, self.part_info)
    
    def _initialize_each_parts(self):
        for part_name in self.part_info.keys():
            if self.part_info[part_name]["type"] == PartType.furniture.value:
                self.furniture_parts.append(part_name)
            elif self.part_info[part_name]["type"] == PartType.connector.value:
                continue
            else:
                exit()

    def check_assembly_possibility(self):
        self.logger.info("ready to check possibility")
        sendall_pickle(self.connected_client, True)
        target_assembly_info = recvall_pickle(self.connected_client)
        response = self._check_assembly_possibility(target_assembly_info)
        sendall_pickle(self.connected_client, response)

    def _check_assembly_possibility(self, target_assembly_info):
        current_assembly_info = target_assembly_info["target"] 
        status = target_assembly_info["status"] # dict
        """status format
        status = {
            "document": document_key,
            "object_info": {
                (part_name, instance_id): object_name
            }
            "assembly": same as previous version
        }
        """
        document_key = status["document"]
        object_info = status["object_info"]
        past_assembly = status["assembly"]
        used_assembly = []
        if not document_key == None:
            document = self.assembly_docs[document_key]["document"]
            document_path = self.assembly_docs[document_key]["document_path"]
            if not document_path == document.current_path:
                document = AssemblyDocument(document_path)
            used_assembly = self.assembly_docs[document_key]["used_assembly"]
            self.assembly_doc = document
        else:
            self.assembly_doc = AssemblyDocument()


        self.assembly_obj = {}
        added_object_key = []
        for past_obj_key in object_info.keys():
            object_name = object_info[past_obj_key]
            obj = self.assembly_doc.get_object_by_name(object_name)
            assert obj, "No {} in document {}".format(object_name, document_key)
            self.assembly_obj[past_obj_key] = obj
        
        # import unimported past sequence
        for past_assembly_info in past_assembly:
            past_pair = past_assembly_info["target_pair"]
            for key in past_pair.keys(): # key is 0, 1
                part_info = past_pair[key]
                part_name = part_info["part_name"]
                instance_id = part_info["instance_id"]
                obj_key = (part_name, instance_id)
                if obj_key in self.assembly_obj.keys():
                    continue
                else:
                    part_path = self.part_info[part_name]["document"]
                    obj = self.assembly_doc.import_part(part_path)
                    self.assembly_obj[(part_name, instance_id)] = obj
                    added_object_key.append((part_name, instance_id))
        
        target_pair = current_assembly_info["target_pair"]
        # check unique instance part
        for key in target_pair.keys(): # key is 0, 1
            part_info = target_pair[key]
            part_name = part_info["part_name"]
            instance_id = part_info["instance_id"]
            if (part_name, instance_id) in self.assembly_obj.keys():
                continue
            else:
                part_path = self.part_info[part_name]["document"]
                obj = self.assembly_doc.import_part(part_path)
                self.assembly_obj[(part_name, instance_id)] = obj
                added_object_key.append((part_name, instance_id))

        self.assembly_doc.show()
        self.assembly_pair = []
        self.additional_assmbly_pair = []
        for past_assembly_info in past_assembly:
            if past_assembly_info in used_assembly:
                continue
            _ = self._add_pair_constraint(past_assembly_info)
            used_assembly.append(past_assembly_info)
        
        _ = self._solve_current_constraint()

        self.assembly_doc.save_doc("test_fail_doc/test_{}.FCStd".format(get_time_stamp()))
        target_constraint = self._add_pair_constraint(current_assembly_info)
        used_assembly.append(current_assembly_info)
        is_possible = False
        is_possible = self._solve_current_constraint()
        # additional assembly
        if len(self.additional_assmbly_pair) > 0:
            is_possible = is_possible and self._additional_assembly()
        
        if is_possible:
            self.assembly_doc.save_doc("test_success_doc/test_{}.FCStd".format(get_time_stamp()))
        else:
            self.assembly_doc.save_doc("test_fail_doc/test_{}.FCStd".format(get_time_stamp()))
            self.assembly_doc.remove_object(target_constraint)
            for obj_key in added_object_key:
                added_object = self.assembly_obj.pop(obj_key)
                self.assembly_doc.remove_object(added_object)
        
        object_info = {}
        for obj_key in self.assembly_obj.keys():
            obj = self.assembly_obj[obj_key]
            name = obj.Name
            object_info[obj_key] = name


        document_key = float(np.random.rand())
        document_path = join(self.assembly_doc_path, "document{}.FCStd".format(document_key))
        self.assembly_doc.save_doc(document_path)
        self.assembly_docs[document_key] = {}
        self.assembly_docs[document_key]["document"] = self.assembly_doc
        self.assembly_docs[document_key]["document_path"] = self.assembly_doc.current_path
        self.assembly_docs[document_key]["used_assembly"] = used_assembly
        response = {
            "is_possible": is_possible,
            "status": {
                "document": document_key,
                "object_info": object_info
            }
        }

        return response
    
    def _add_pair_constraint(self, pair_assembly_info):
        target = pair_assembly_info["target_pair"]
        method = pair_assembly_info["method"]
        # assemble target       
        part_info_0 = target[0]
        part_name_0 = part_info_0["part_name"]
        instance_id_0 = part_info_0["instance_id"]
        point_idx_0 = part_info_0["assembly_point"]
        point_0 = self.part_info[part_name_0]["assembly_points"][point_idx_0]
        edge_0 = point_0["edge_index"][0]
        obj_0 = self.assembly_obj[(part_name_0, instance_id_0)]

        part_info_1 = target[1]
        part_name_1 = part_info_1["part_name"]
        instance_id_1 = part_info_1["instance_id"]
        point_idx_1 = part_info_1["assembly_point"]
        point_1 = self.part_info[part_name_1]["assembly_points"][point_idx_1]
        edge_1 = point_1["edge_index"][0]
        obj_1 = self.assembly_obj[(part_name_1, instance_id_1)]

        direction = method["direction"]
        offset = method["offset"]
        additional = method["additional"]
        if additional:
            self.additional_assmbly_pair.append(((part_name_0, instance_id_0), (part_name_1, instance_id_1), additional))


        co = self.assembly_doc.add_circle_constraint(obj_0, obj_1, [edge_0, edge_1], direction, offset)
        
        self.assembly_pair.append(((part_name_0, instance_id_0), (part_name_1, instance_id_1)))
        self.assembly_doc.add_assembly_pair(pair_assembly_info)

        return co

    def _solve_current_constraint(self):
        is_possible = True
        num_contraints = {}
        # diagoanl = {}
        fixed_obj = []
        for obj_key in self.assembly_obj.keys():
            self.assembly_obj[obj_key].fixedPosition = False
            circle_cons = []
            for cons in self.assembly_obj[obj_key].InList:
                if cons.Type == 'circularEdge':
                    circle_cons.append(cons)
            num_contraints[obj_key] = len(circle_cons)
        # for obj_key in self.assembly_obj.keys():
        #     d_lenght = self.assembly_obj[obj_key].Shape.BoundBox.DiagonalLength
        #     diagoanl[obj_key] = d_lenght

        sorted_instance = sorted(num_contraints.items(), key=(lambda x:x[1]), reverse=True)
        # sorted_instance = sorted(diagoanl.items(), key=(lambda x:x[1]))
        # print(sorted_instance)
        
        fixed_obj_key = sorted_instance[0][0]
        self.assembly_obj[fixed_obj_key].fixedPosition = True
        
        is_possible = self.assembly_doc.solve_system()
        
        return is_possible

    def _additional_assembly(self):
        for additional_assembly in self.additional_assmbly_pair:
            instance_0 = additional_assembly[0]
            instance_1 = additional_assembly[1]
            additional = additional_assembly[2]
            
            obj_0 = self.assembly_obj[instance_0]
            obj_1 = self.assembly_obj[instance_1]

            constraint_type = additional["type"]
            if constraint_type == "parallel":
                face_pair = additional["face_pair"]
                direction = additional["direction"]
                self.assembly_doc.add_parallel_plane_constraint(obj_0, obj_1, face_pair, direction)
            else:
                assert False, "Not Implemented"
        is_possible = self.assembly_doc.solve_system()
        
        return is_possible
    
    def extract_group_obj(self):
        self.logger.info("ready to extract group obj")
        sendall_pickle(self.connected_client, True)
        group_info = recvall_pickle(self.connected_client)
        group_status = group_info["group_status"]
        obj_root = group_info["obj_root"]
        check_and_reset_dir(obj_root)
        self.logger.info("Export group obj in {}".format(obj_root))
        result = self._export_group_obj(group_status, obj_root)
        self.logger.info("Success to extract group obj into {}".format(obj_root))
        sendall_pickle(self.connected_client, result)
    
    def _export_group_obj(self, group_status, obj_root):
        composed_part = group_status["composed_part"]
        status = group_status["status"]
        
        document_key = status["document"]
        
        self.assembly_obj = {}
        
        if not document_key == None:
            self.assembly_doc = self.assembly_docs[document_key]["document"]
            document_path = self.assembly_docs[document_key]["document_path"]
            if not document_path == self.assembly_doc.current_path:
                self.assembly_doc = AssemblyDocument(document_path)
            
            object_info = status["object_info"]
            for past_obj_key in object_info.keys():
                object_name = object_info[past_obj_key]
                obj = self.assembly_doc.get_object_by_name(object_name)
                assert obj, "No {} find in document {}".format(object_name, document_key)
                self.assembly_obj[past_obj_key] = obj
        else:
            self.assembly_doc = AssemblyDocument()
            assert len(composed_part) == 1, "No document??"
            part_instance = composed_part[0]
            part_name = part_instance["part_name"]
            instance_id = part_instance["instance_id"]
            document = self.part_info[part_name]["document"]
            obj = self.assembly_doc.import_part(document)
            self.assembly_obj[(part_name, instance_id)] = obj

        self.assembly_doc.show()
        is_solved = self._solve_current_constraint()
        assert is_solved, "Fail to assemble group obj"
        base_obj = []
        group_object_pose = {}
        for obj_key in self.assembly_obj.keys():
            part_name = obj_key[0]
            ins = obj_key[1]
            part_instacne = "{}_{}".format(part_name, ins)
            group_obj = self.assembly_obj[obj_key]
            # if part_name in self.additional_constraint_parts:
            #     group_obj.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0),FreeCAD.Rotation(FreeCAD.Vector(0,1,0),90))
            #     FreeCAD.ActiveDocument.recompute()
            pos = list(np.array(group_obj.Placement.Base) * 0.001)
            quat = list(group_obj.Placement.Rotation.Q)
            Mesh.export([group_obj], join(obj_root, "{}_{}.obj".format(part_name, ins)))
            pose = pos + quat
            pose = npfloat_to_float(pose)
            group_object_pose[part_instacne] = pose
            
            if part_name in self.furniture_parts:
                base_obj.append(group_obj)
        Mesh.export(base_obj, join(obj_root, "base.obj"))
        save_dic_to_yaml(group_object_pose, join(obj_root, "group_pose.yaml"))
        
        return True

    #endregion
    @staticmethod
    def assembly_pair_test(all_part_info, assembly_pair):
        unique_radius = []
        assembly_doc = AssemblyDocument()
        check_and_reset_dir("pair_test")
        
        for parent_part_name in assembly_pair.keys():
            assembly_doc.reset()
            parent_part_path = "./pair_test/" + parent_part_name + ".FCStd"
            parent_info = all_part_info[parent_part_name]
            parent_doc = parent_info["document"]
            parent_object = assembly_doc.import_part(parent_doc)
            parent_object.fixedPosition = True
            parent_pair_info = assembly_pair[parent_part_name]
            for parent_point_id in parent_pair_info.keys():
                child_list = parent_pair_info[parent_point_id]
                unique_child = []
                for child_info in child_list:
                    
                    child_part_name = child_info["part_name"]
                    if child_part_name in unique_child:
                        continue
                    else:
                        unique_child.append(child_part_name)
                    child_point_id = child_info["assembly_point"]
                    # method
                    offset = child_info["offset"]
                    direction = child_info["direction"]

                    parent_point = parent_info["assembly_points"][parent_point_id]
                    parent_edge = parent_point["edge_index"][0]
                    
                    
                    child_info = all_part_info[child_part_name]
                    child_doc = child_info["document"]
                    child_point = child_info["assembly_points"][child_point_id]
                    child_edge = child_point["edge_index"][0]
                    child_object = assembly_doc.import_part(child_doc)

                    assembly_doc.add_circle_constraint(obj1=parent_object,
                                                       obj2=child_object,
                                                       edge_pair=(parent_edge, child_edge),
                                                       direction=direction,
                                                       offset=offset)
            assembly_doc.solve_system()
            assembly_doc.save_doc(parent_part_path)

if __name__ == "__main__":
    logger = get_logger("FreeCAD_Module")    
    freecad_module = FreeCADModule(logger)
    
    # extract_part_info("./cad_file/STEFAN")
    # all_part_info = load_yaml_to_dic("./assembly/STEFAN/part_info.yaml")
    # pair_path = "./assembly/STEFAN/assembly_pair.yaml"
    # assembly_pair = load_yaml_to_dic(pair_path)
    # freecad_module.assembly_pair_test(all_part_info, assembly_pair)
    # assert False, "SUCCESS"
    
    freecad_module.initialize_server()
    while True:
        # try:
        request = recvall_pickle(freecad_module.connected_client)
        logger.info("Get request to {}".format(request))
        callback = freecad_module.get_callback(request)
        callback()
    # except Exception as e:
        # logger.info("Error occur {}".format(e))
        # break
    freecad_module.close()    
"""
#TODO: pair refine
- pin 에서 1번이 자꾸 opposed 가 됨.
- left 와 볼트 aligned -> opposed 로 변경 해야함
"""

