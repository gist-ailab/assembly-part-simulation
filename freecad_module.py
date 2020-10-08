from script import fileApi
from script import import_fcstd

import FreeCAD
import FreeCADGui
FreeCADGui.showMainWindow()
import Part
from FreeCAD import Base
import importOBJ
import Draft

import a2plib
from a2p_importpart import importPartFromFile
import a2p_constraints as a2pconst
import a2p_solversystem as solver

from scipy.spatial.transform import Rotation as R
import numpy as np
import copy

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
        self.edge_index = {
            "aligned": [],
            "opposed": []
        }
        self.is_reverse = False

    def create_circle(self):
        position = Base.Vector(self.position)
        direction = Base.Vector(self.direction)
        self.shape = Part.makeCircle(self.radius, position, direction, 0, 360)

    def visualize_circle(self, doc, name="circle"):
        FreeCAD.setActiveDocument(doc.Name)
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
                if not self.is_reverse:
                    self.edge_index["aligned"].append(ind + 1)
                    find_edge = True
                else:
                    self.edge_index["opposed"].append(ind + 1)
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
    
#endregion

#region math calculate
def get_quat_from_dcm(x, y, z):
    r = R.from_dcm(np.array([x, y, z]))
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
        circle.get_edge_index_from_shape(shape)

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

#endregion

def extract_assembly_points(step_path, step_name, doc_path, logger, part_type, condition=[]):
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

    if "wood_pin" in step_name:
        mid_circle1 = copy.deepcopy(circles[0])
        mid_circle2 = copy.deepcopy(circles[1])
        position = [val1/2 + val2/2 for val1, val2 in zip(mid_circle1.position, mid_circle2.position)]
        mid_circle1.position = position
        mid_circle2.position = position
        circles += [mid_circle1, mid_circle2]

    for idx, circle in enumerate(circles):
        if idx in condition:
            circle.reverse()
        circle.create_circle()
        circle.visualize_circle(doc)

    # extract circle holes
    circle_holes = get_circle_holes(circles)
    for hole in circle_holes:
        hole.create_hole()
        hole.visualize_hole(doc)
        hole.set_hole_type(doc, obj)

    # extract assembly point from circle holes
    assembly_points = []
    for idx, hole in enumerate(circle_holes):
        assembly_point = {
            "id": idx,
            "type": hole.type,
            "radius": hole.radius,
            "edge_index": hole.start_circle.edge_index,
            "depth": hole.depth * 0.001,
            "direction": hole.direction,
            "pose": {
                "position": npfloat_to_float(hole.start_circle.get_position_m()),
                "quaternion": npfloat_to_float(hole.start_circle.quaternion)
            }
        }
        assembly_points.append(assembly_point)

    doc.saveAs(doc_path)
    FreeCAD.closeDocument(doc.Name)
    return assembly_points

def extract_group_obj(doc_path, obj_path):
    doc = open_doc(doc_path)
    group_objs = []
    objs = doc.findObjects()
    for obj in objs:
        if "furniture" in obj.Label:
            group_objs.append(obj)
    importOBJ.export(group_objs, obj_path)

def assemble_A_and_B()

def open_doc(filepath):
    return FreeCAD.openDocument(filepath)

def save_doc_as(doc, filepath):
    doc.saveAs(filepath)

def close_doc(doc, path=None):
    FreeCAD.closeDocument(doc.Name)

