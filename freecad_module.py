from script import fileApi
from script import import_fcstd
from os.path import join

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

PART_INFO = None
temp_doc_path = "./temp.FCStd"
unique_radius = []

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
                if not self.is_reverse:
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
    
    def assemble(self, obj1, obj2, edge_pair, direction, offset=0):
        constraint_two_circle(doc=self.doc, 
                                parent_obj=obj1, 
                                child_obj=obj2, 
                                parent_edge=edge_pair[0], 
                                child_edge=edge_pair[1], 
                                direction=direction, 
                                offset=offset)
    
    def save_doc(self, path):
        save_doc_as(self.doc, path)

    def reset(self):
        close_doc(self.doc)
        self.doc = open_doc(self.initial_path)

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

def constraint_two_circle(doc, parent_obj, child_obj, parent_edge, child_edge, direction, offset):
    parent_obj.fixedPosition = True
    child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Edge" + str(parent_edge))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Edge" + str(child_edge))
    cc = a2pconst.CircularEdgeConstraint([s1, s2])
    if direction:
        cc.direction = "aligned"
    else:
        cc.direction = "opposed"
    co = cc.constraintObject
    
    co.offset = offset
    
    solver.solveConstraints(doc)

def solve_system(doc):
    return solver.solveConstraints(doc)


def get_distance_between_edges(edge1, edge2):
    
    return edge1.Curve.Location.distanceToPoint(edge2.Curve.Location)

def set_obj_color(doc, obj, color):
    gui_doc = FreeCADGui.getDocument(doc.Name)
    gui_obj = gui_doc.getObject(obj.Name)
    gui_obj.LineColor = color

#endregion

def extract_assembly_points(step_path, step_name, doc_path, logger, part_type, condition=[]):
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

    for idx, circle in enumerate(circles):
        if idx in condition:
            circle.reverse()
        circle.create_circle()

    # extract circle holes
    circle_holes = get_circle_holes(circles)
    for hole in circle_holes:
        hole.create_hole()
        hole.visualize_hole(doc)
        hole.set_hole_type(doc, obj)
        
        hole.remove_hole(doc)
        hole.visualize_frame(doc)
        if hole.radius in unique_radius:
            pass
        else:
            print(hole.radius)
            unique_radius.append(hole.radius)
            unique_radius.sort()

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

def assemble_A_and_B(instance_info_a, instance_info_b, region_a=[0, 1, 2], region_b=[0, 1, 2], assembly_num=1):
    """
    TODO
    - Part A info Part B info
    long [0, 1, 2] Placement [Pos=(-93,40,0), Yaw-Pitch-Roll=(0,0,0)]
    left [0, 1, 2] Placement [Pos=(185,410.191,-10.1319), Yaw-Pitch-Roll=(90,-87.5864,90)]
    """
    class AssemblyInfo(object):
        def __init__(self, instance_info):
            self.part_name = instance_info["part_name"]
            self.used_points = instance_info["used_points"]
            self.assembly_document = instance_info["assembly_document"]
            
            self.part_info = PART_INFO[self.part_name]
            self.assembly_points = PART_INFO["assembly_points"]

        def get_part_path(self):
            return self.assembly_document
        
        def get_edge_index_(self, idx):
            return self.assembly_points[idx]


        
    class AssemblyPair(object):
        def __init__(self, info_a, info_b, region_a, region_b):
            self.info_a = info_a
            self.info_b = info_b
            self.region_a = region_a
            self.region_b = region_b
            self.point_pairs = []
            self.initialize_point_pairs()

        def initialize_point_pairs(self):
            for point_a in self.region_a:
                for point_b in self.region_b:
                    new_pair = (point_a, point_b)
                    if new_pair in self.point_pairs:
                        continue
                    self.point_pairs.append(new_pair)
            
        def get_lowest_cost_pair(self):
            min_cost = np.inf
            lowest_pair = [0, 0]
            edge_pair = [0, 0]
            for idx_a, idx_b in self.point_pairs:
                edge_a, dir_a = assembly_points_a[idx_a]["edge_index"]
                edge_b, dir_b = assembly_points_b[idx_b]["edge_index"]
                distance = get_distance_between_edges(obj_a.Shape.Edges[edge_a], obj_b.Shape.Edges[edge_b])
                if distance < min_cost:
                    min_cost = distance
                    lowest_pair = [idx_a, idx_b]  
                    edge_pair = [edge_a, edge_b]
                print(edge_a, edge_b, distance)
            return lowest_pair , edge_pair, dir_a == dir_b
    
    # 1. initialize assembly document
    assembly_doc = AssemblyDocument()

    # 2. initialize assembly parts info
    info_a = AssemblyInfo(instance_info_a)
    info_b = AssemblyInfo(instance_info_b)
    
    # 3. import part on document    
    obj_a = assembly_doc.import_part(info_a.get_part_path(), pos=(-93,40,0), ypr=(0,0,0))
    obj_b = assembly_doc.import_part(info_b.get_part_path(), pos=(185,410.191,-10.1319), ypr=(90,-87.5864,90))

    # 4. calculate all possible point pair for region pair
    point_pairs = []
    # create assembly point pairs

    
    # calculate lowest cost pair
    point_pair, edge_pair, direction = get_lowest_cost_pair()
    # assemble
    assembly_doc.assemble(obj_a, obj_b, edge_pair, direction)
    assembly_doc.save_doc_as("temp41.FCStd")    

def assemble_pair_test(pairs):
    save_root = "./pair_test"
    fileApi.check_and_create_dir(save_root)
    unique_pair = []
    doc_path = join(save_root, "initial.FCStd")
    doc = AssemblyDocument(doc_path=doc_path)

    for pair_id, pair in enumerate(pairs):
        doc.reset()
        if tuple(pair) in unique_pair:
            continue
        part1, part2, idx1, idx2, offset = pair
        save_dir = join(save_root,  part1+"_"+part2)
        fileApi.check_and_create_dir(save_dir)
        
        info1 = PART_INFO[part1]
        info2 = PART_INFO[part2]
        doc1 = info1["document"]
        doc2 = info2["document"]
        point1 = info1["assembly_points"][idx1]
        point2 = info2["assembly_points"][idx2]
        edge1 = point1["edge_index"][0]
        edge2 = point2["edge_index"][0]
        direction = point1["edge_index"][1] == point2["edge_index"][1]

        obj1 = doc.import_part(doc1)
        obj2 = doc.import_part(doc2)
        doc.assemble(obj1, obj2, [edge1, edge2], direction, offset=offset)
        doc.save_doc(join(save_dir, str(pair_id)+".FCStd"))
        unique_pair.append((part1, part2, idx1, idx2, offset))
        unique_pair.append((part2, part1, idx2, idx1, offset))
        if "pin" in part1:
            if idx1 == 0:
                unique_pair.append((part1, part2, 1, idx2, offset))
                unique_pair.append((part2, part1, idx2, 1, offset))
            else:
                unique_pair.append((part1, part2, 0, idx2, offset))
                unique_pair.append((part2, part1, idx2, 0, offset))
        elif "pin" in part2:
            if idx2 == 0:
                unique_pair.append((part1, part2, idx1, 1, offset))
                unique_pair.append((part2, part1, 1, idx1, offset))
            else:
                unique_pair.append((part1, part2, idx1, 0, offset))
                unique_pair.append((part2, part1, 0, idx1, offset))

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
    