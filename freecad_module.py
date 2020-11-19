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
        0: [0,1,2],
        1: [4,5,6],
        2: [3,8,9],
        3: [7]
    },
    "ikea_stefan_side_right": {
        0: [0,1,2],
        1: [4,5,6],
        2: [3,8,9],
        3: [7]
    },
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

    def reverse(self):
        self.direction = [-1 * val for val in self.direction]
        self.XAxis = [-1* val for val in self.XAxis]

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
        self.doc = FreeCAD.newDocument()
        self.initial_path = doc_path
        save_doc_as(self.doc, doc_path)

    def import_part(self, part_path, pos=[0, 0, 0], ypr=[0,0,0]):
        obj = importPartFromFile(self.doc, part_path)
        obj.Placement.Base = FreeCAD.Vector(pos)
        obj.Placement.Rotation = FreeCAD.Rotation(ypr[0], ypr[1], ypr[2])
        return obj
    
    def add_circle_constraint(self, obj1, obj2, edge_pair, direction, offset=0):
        constraint_two_circle(doc=self.doc, parent_obj=obj1, child_obj=obj2,
                                parent_edge=edge_pair[0], child_edge=edge_pair[1],
                                direction=direction, offset=offset)
    
    def assemble(self, obj1, obj2, edge_pair, direction, offset=0):
        self.add_circle_constraint(obj1, obj2, edge_pair, direction, offset=0)
        self.solve_system()

    def solve_system(self):
        is_solved = solver.solveAccuracySteps(self.doc, None)
        return is_solved

    def check_unmoved_parts(self):
        if len(solver.unmovedParts) > 0:
            return True
        else:
            return False

    def save_doc(self, path):
        save_doc_as(self.doc, path)

    def reset(self):
        close_doc(self.doc)
        self.doc = open_doc(self.initial_path)

    def close(self):
        close_doc(self.doc.Name)

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
def get_circles(obj):
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

    for circle in circles:
        circle.get_edge_index_from_shape(obj.Shape)

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
    parent_obj.fixedPosition = True
    child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Edge" + str(parent_edge))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Edge" + str(child_edge))
    cc = a2pconst.CircularEdgeConstraint([s1, s2])
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
            assembly_points = extract_assembly_points(step_path=cad_file,
                                                      step_name=part_name,
                                                      doc_path=doc_path,
                                                      part_type=part_type,
                                                      )
            if part_name in region_condition.keys():
                region = region_condition[part_name]
            else:
                region = {}
            part_info[part_name] = {
                "part_id": part_id,
                "type": part_type.value,
                "document": doc_path,
                "step_file": cad_file,
                "assembly_points": assembly_points,
                "region": region
            }
            part_id += 1

    return part_info

def extract_assembly_points(step_path, step_name, doc_path, part_type):
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
    
    # extract circles
    circles = get_circles(obj)

    if "pin" in step_name:
        mid_circle1 = copy.deepcopy(circles[0])
        mid_circle2 = copy.deepcopy(circles[1])
        position = [val1/2 + val2/2 for val1, val2 in zip(mid_circle1.position, mid_circle2.position)]
        mid_circle1.position = position
        mid_circle2.position = position
        circles += [mid_circle1, mid_circle2]

    reverse_condition = hole_condition[step_name]
    for idx, circle in enumerate(circles):
        if idx in reverse_condition:
            circle.reverse()
        circle.create_circle()

    # extract circle holes
    circle_holes = get_circle_holes(circles)
    for hole in circle_holes:
        hole.create_hole()
        hole.visualize_hole(doc)
        hole.set_hole_type(doc, obj)
        
        hole.remove_hole(doc)
        # hole.visualize_frame(doc)
        if hole.radius in unique_radius:
            pass
        else:
            unique_radius.append(hole.radius)
            unique_radius.sort()

    # extract assembly point from circle holes
    assembly_points = {}
    for idx, hole in enumerate(circle_holes):
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
        assembly_points[idx] = assembly_point
    doc.saveAs(doc_path)
    FreeCAD.closeDocument(doc.Name)
    return assembly_points

def open_doc(filepath):
    return FreeCAD.openDocument(filepath)

def save_doc_as(doc, filepath):
    doc.saveAs(filepath)

def close_doc(doc):
    FreeCAD.closeDocument(doc.Name)

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
        self.th = threading.Thread(target=self.binding)
        self.th.start()

        # 조립에 사용하는 변수들
        self.part_info = None
        self.furniture_parts = []
    
        self.assembly_doc = None
        self.assembly_obj = {}
        self.assembly_pair = []
        
    def get_callback(self, request):
        return self.callback[request]

    def binding(self):
        try:
            while True:
                self.Gui.updateGui()
                self.main_window.update()
        except Exception as e:
            self.logger.info("freecad server error {}".format(e))

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
        is_possible = self._check_assembly_possibility(target_assembly_info)
        sendall_pickle(self.connected_client, is_possible)

    def _check_assembly_possibility(self, target_assembly_info):
        self.assembly_doc = AssemblyDocument()
        current_assembly_info = target_assembly_info["target"] 
        status = target_assembly_info["status"] # list
        
        target_pair = current_assembly_info["target_pair"]
        method = current_assembly_info["method"]
        
        unique_instance = []
        # check unique instance part
        for key in target_pair.keys(): # key is 0, 1
            part_info = target_pair[key]
            part_name = part_info["part_name"]
            instance_id = part_info["instance_id"]
            if (part_name, instance_id) in unique_instance:
                continue
            else:
                unique_instance.append((part_name, instance_id))
        for past_assembly_info in status:
            past_pair = past_assembly_info["target_pair"]
            past_method = past_assembly_info["method"]
            for key in past_pair.keys(): # key is 0, 1
                part_info = past_pair[key]
                part_name = part_info["part_name"]
                instance_id = part_info["instance_id"]
                if (part_name, instance_id) in unique_instance:
                    continue
                else:
                    unique_instance.append((part_name, instance_id))
        
        self.assembly_obj = {}
        # import unique instance to scene
        for part_name, ins in unique_instance:
            part_path = self.part_info[part_name]["document"]
            obj = self.assembly_doc.import_part(part_path)
            self.assembly_obj[(part_name, ins)] = obj
        
        self.assembly_pair = []
        # create previous constraint
        for past_assembly_info in status:
            self._add_pair_constraint(past_assembly_info)
        self._add_pair_constraint(current_assembly_info)

        is_possible = self._solve_current_constraint()
        
        return is_possible
    
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

        self.assembly_doc.add_circle_constraint(obj_0, obj_1, [edge_0, edge_1], direction, offset)
        self.assembly_pair.append(((part_name_0, instance_id_0), (part_name_1, instance_id_1)))

    def _solve_current_constraint(self):
        # to assemble each pair one part fix and other part free
        for obj_key in self.assembly_obj.keys():
            self.assembly_obj[obj_key].fixedPosition = False
        _ = self.assembly_doc.solve_system()
        is_possible = True
        solved_pair_count = 0
        while self.assembly_doc.check_unmoved_parts() and solved_pair_count < len(self.assembly_pair):
            used_part = []
            fixed_part = []
            unfixed_part = []
            for pair in self.assembly_pair[solved_pair_count:]:
                instance_0 = pair[0]
                instance_1 = pair[1]
                if instance_0 in used_part and instance_1 in used_part:
                    # check fixed and unfixed            
                    if instance_0 in fixed_part:
                        if instance_1 in fixed_part:
                            # ERROR both instance are fixed
                            break
                        else:
                            # 0 is fixed, 1 is unfixed
                            pass
                    else: # instance_0 is unfixed
                        if instance_1 in fixed_part:
                            # 0 is unfixed, 1 is fixed
                            pass
                        else:
                            # ERROR both instance are unfixed
                            break
                elif instance_0 in used_part: 
                    if instance_0 in fixed_part: # fix, unfixed
                        self.assembly_obj[instance_1].fixedPosition = False
                        unfixed_part.append(instance_1)
                        used_part.append(instance_1)
                    else: # unfix, fix
                        self.assembly_obj[instance_1].fixedPosition = True
                        fixed_part.append(instance_1)
                        used_part.append(instance_1)
                elif instance_1 in used_part:
                    if instance_1 in fixed_part: # unfix, fix
                        self.assembly_obj[instance_0].fixedPosition = False
                        unfixed_part.append(instance_0)
                        used_part.append(instance_0)
                    else: # fix, unfix
                        self.assembly_obj[instance_0].fixedPosition = True
                        fixed_part.append(instance_0)
                        used_part.append(instance_0)
                else: # fix, unfix
                    self.assembly_obj[instance_0].fixedPosition = True
                    fixed_part.append(instance_0)
                    used_part.append(instance_0)
                    self.assembly_obj[instance_1].fixedPosition = False
                    unfixed_part.append(instance_1)
                    used_part.append(instance_1)
                solved_pair_count += 1
            is_possible = self.assembly_doc.solve_system()

        return is_possible

    def extract_group_obj(self):
        self.logger.info("ready to extract group obj")
        sendall_pickle(self.connected_client, True)
        group_info = recvall_pickle(self.connected_client)
        group_status = group_info["group_status"]
        obj_root = group_info["obj_root"]
        self.logger.info("Export group obj in {}".format(obj_root))
        result = self._export_group_obj(group_status, obj_root)
        self.logger.info("Success to extract group obj into {}".format(obj_root))
        sendall_pickle(self.connected_client, result)
    
    def _export_group_obj(self, group_status, obj_root):
        composed_part = group_status["composed_part"]
        status = group_status["status"]
        self.assembly_doc = AssemblyDocument()
        self.assembly_obj = {}
        # import all parts to document
        for part_info in composed_part:
            part_name = part_info["part_name"]
            ins = part_info["instance_id"]
            part_path = self.part_info[part_name]["document"]
            obj = self.assembly_doc.import_part(part_path)
            self.assembly_obj[(part_name, ins)] = obj
        
        self.assembly_pair = []
        # assemble to current state
        for assembly_info in status:
            self._add_pair_constraint(assembly_info)
        is_solved = self._solve_current_constraint()
        assert is_solved, "Fail to assemble group obj"
        
        base_obj = []
        for obj_key in self.assembly_obj.keys():
            part_name = obj_key[0]
            if part_name in self.furniture_parts:
                group_obj = self.assembly_obj[obj_key]
                Mesh.export([group_obj], join(obj_root, "{}.obj".format(part_name)))
                base_obj.append(group_obj)
        Mesh.export(base_obj, join(obj_root, "base.obj"))
        
        return True

    #endregion

    def assembly_pair_test(self):
        assembly_doc = AssemblyDocument()
        check_and_create_dir("pairtest")
        for part_name in self.assembly_pair.keys():
            part_path = "./pairtest/" + part_name
            check_and_create_dir(part_path)
            part_info = self.assembly_pair[part_name]
            for point_id in part_info.keys():
                pair_list = part_info[point_id]
                for pair_info in pair_list:
                    assembly_doc.reset()
                    pair_name = pair_info["part_name"]
                    offset = pair_info["offset"]
                    assembly_point = pair_info["assembly_point"]
                    direction = pair_info["direction"]
                    info_1 = self.part_info[part_name]
                    info_2 = self.part_info[pair_name]
                    doc_1 = info_1["document"]
                    doc_2 = info_2["document"]
                    point_1 = info_1["assembly_points"][point_id]
                    point_2 = info_2["assembly_points"][assembly_point]
                    edge1 = point_1["edge_index"][0]
                    edge2 = point_2["edge_index"][0]

                    obj1 = assembly_doc.import_part(doc_1)
                    obj2 = assembly_doc.import_part(doc_2)
                    assembly_doc.assemble(obj1, obj2, [edge1, edge2], direction, offset=offset)
                    assembly_doc.save_doc(join(part_path, "{}_{}_{}".format(point_id, pair_name, assembly_point) + ".FCStd"))
                    

if __name__ == "__main__":
    logger = get_logger("FreeCAD_Module")    
    freecad_module = FreeCADModule(logger)
    freecad_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(freecad_module.connected_client)
            logger.info("Get request to {}".format(request))
            callback = freecad_module.get_callback(request)
            callback()
        except Exception as e:
            logger.info("Error occur {}".format(e))
            break
    freecad_module.close()    
"""
#TODO: pair refine
- pin 에서 1번이 자꾸 opposed 가 됨.
- left 와 볼트 aligned -> opposed 로 변경 해야함
"""

