from script.fileApi import *
from scipy.spatial.transform import Rotation as R
import numpy as np
from decimal import Decimal
from datetime import datetime
import time
#------------------------------------------------
#region freecad library
from script import import_fcstd # add path for import FreeCAD
import FreeCAD
import FreeCADGui
FreeCADGui.showMainWindow() # FreeCADGui should be show before using
import Part
from FreeCAD import Base
import importOBJ
import Draft

import a2plib
from a2p_importpart import importPartFromFile
import a2p_constraints as a2pconst
import a2p_solversystem as solver
#eneregion

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

OUTPUT_PATH = join(CURRENT_PATH, "output")
check_and_create_dir(OUTPUT_PATH)

FREECAD_DOCUMENT_PATH = join(OUTPUT_PATH, "FCDocument")
check_and_create_dir(FREECAD_DOCUMENT_PATH)

INSTANCE_DOCUMENT_DIR = join(FREECAD_DOCUMENT_PATH, "instance_document")
check_and_create_dir(INSTANCE_DOCUMENT_DIR)

ASSEMBLY_DOCUMENT_DIR = join(FREECAD_DOCUMENT_PATH, "assembly_document")
check_and_create_dir(ASSEMBLY_DOCUMENT_DIR)

OBJ_PATH = join(OUTPUT_PATH, "obj")
check_and_create_dir(OBJ_PATH)

def float_to_exponential(float_value_list):
    ex_list = []
    for val in float_value_list:
        ex_list.append('{:.5E}'.format(Decimal(val)))
    
    return ex_list

def npfloat_to_float(np_float_list):
    f_list = []
    for val in np_float_list:
        f_list.append(float(val))
    
    return f_list

def get_dcm_from_quat(quat):
    r = R.from_quat(quat)
    r = r.as_dcm()
    r = list(r)

    return r

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

#--------------------------------------------
#region freecad basic Api

def edge_to_face(edges):
    _ = Part.Face(Part.Wire(Part.__sortEdges__(edges)))
    if _.isNull(): 
        raise RuntimeError('Failed to create face')
    FreeCAD.ActiveDocument.addObject('Part::Feature','Face').Shape= _
    del _
    
def show_shape_in_doc(shape, label):
    doc = get_active_doc()
    Part.show(shape)
    obj = doc.ActiveObject
    obj.Label = label

    return obj

def compound_doc_objects(label):
    doc = get_active_doc()
    if doc == None:
        print("Please create active document")
        return False
    object_list = doc.findObjects()
    shape_list = []
    for obj in object_list:
        shape_list.append(obj.Shape)
    doc.addObject("Part::Compound", label)
    compound = doc.ActiveObject
    compound.Links = object_list
    doc.recompute()

def export_doc_objects_to_obj(doc, save_name):
    objs = doc.findObjects()
    save_path = join(OBJ_PATH, save_name + ".obj") 
    importOBJ.export(objs, save_path)

def create_doc(doc_name):
    doc = FreeCAD.newDocument(doc_name)

    return doc

def save_doc_as(save_doc_name):
    save_doc_name += ".FCStd"
    save_doc_path = join(FREECAD_DOCUMENT_PATH, save_doc_name)
    doc = get_active_doc()
    doc.saveAs(save_doc_path)

def save_assem_doc_as(save_doc_name):
    save_doc_name += ".FCStd"
    save_doc_path = join(ASSEMBLY_DOCUMENT_DIR, save_doc_name)
    doc = get_active_doc()
    doc.saveAs(save_doc_path)

def save_instance_doc_as(save_doc_name):
    save_doc_name += ".FCStd"
    save_doc_path = join(INSTANCE_DOCUMENT_DIR, save_doc_name)
    doc = get_active_doc()
    doc.saveAs(save_doc_path)

def close_doc(close_doc_name):
    FreeCAD.closeDocument(close_doc_name)

def get_active_doc():
    
    return FreeCAD.ActiveDocument

def get_active_obj():
    doc = get_active_doc()
    
    return doc.ActiveObject

def get_object(obj_name):
    doc = get_active_doc()
    
    return doc.getObject(obj_name)

def get_object_by_label(obj_label):
    doc = get_active_doc()
    
    return doc.getObjectsByLabel(obj_label)[0]

def set_obj_visibility(obj_name, visible=True):
    gui_doc = FreeCADGui.ActiveDocument
    gui_obj = gui_doc.getObject(obj_name)
    gui_obj.Visibility = visible

def set_obj_color(obj_name, color=(1., 1., 1.)):
    """set object color
    color is tuple of float (0~1)
    """ 
    gui_doc = FreeCADGui.ActiveDocument
    gui_obj = gui_doc.getObject(obj_name)
    gui_obj.LineColor = color
    
def copy_shape_to_doc(shape, label):
    doc = get_active_doc()
    if doc == None:
        print("Please create active document")
        return False
    copied_shape = shape.copy()
    show_shape_in_doc(copied_shape, label)
        
def load_step_file(path, doc_name, obj_name):
    doc = get_active_doc()
    if doc == None:
        print("Please create active document")
        return False
    path = relative_path_to_abs_path(path)
    print(doc_name)
    Part.insert(path, doc_name)
    obj = get_active_obj()
    obj.Label = obj_name

    return True

def open_doc(doc_path):
    FreeCAD.open(doc_path)
    doc = FreeCAD.ActiveDocument

    return doc

def rotate_obj(obj, angle, position, axis):
    Draft.rotate(obj, angle, position, axis=axis, copy=False)

#endregion

#-------------------------------------------------------------
#region extract cad info Api

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
        
    def create_circle(self, circle_name):
        position = Base.Vector(self.position)
        direction = Base.Vector(self.direction)
        circle_name += "_"
        circle_name += str(self.radius)
        self.name = circle_name
        self.shape = Part.makeCircle(self.radius, position, direction, 0, 360)
        self.object = show_shape_in_doc(self.shape, circle_name)

    def visualize_circle_frame(self):
        doc = get_active_doc()
        obj_O = Base.Vector(self.position)
        obj_axis = {
            "x": Base.Vector(self.XAxis),
            "y": Base.Vector(self.YAxis),
            "z": Base.Vector(self.direction)
        }
        _visualize_frame(self.name, obj_O, obj_axis)

    def visualize_circle_frame_quat(self):
        doc = get_active_doc()
        obj_O = Base.Vector(self.position)
        xyz = get_dcm_from_quat(self.quaternion)
        obj_axis = {
            "x": Base.Vector(xyz[0]),
            "y": Base.Vector(xyz[1]),
            "z": Base.Vector(xyz[2])
        }
        _visualize_frame(self.name, obj_O, obj_axis)

    def update_frame(self):
        circle = self.object.Shape.Curve
        self.position = [circle.Center.x, circle.Center.y, circle.Center.z]
        self.XAxis = [circle.XAxis.x, circle.XAxis.y, circle.XAxis.z]
        self.YAxis = [circle.YAxis.x, circle.YAxis.y, circle.YAxis.z]
        self.direction = [circle.Axis.x, circle.Axis.y, circle.Axis.z]
        self.quaternion = get_quat_from_dcm(self.XAxis, self.YAxis, self.direction)

    def get_edge_index_from_shape(self, shape):
        edges = shape.Edges
        find_edge = False
        for ind, edge in enumerate(edges):
            if not _check_circle_edge(edge):
                continue
            if edge.isSame(self.edge):
                if not self.is_reverse:
                    self.edge_index["aligned"].append(ind + 1)
                    find_edge = True
                else:
                    self.edge_index["opposed"].append(ind + 1)
                    find_edge = True
            #       
            # circle = edge.Curve
            # position = [circle.Center.x, circle.Center.y, circle.Center.z]
            # axis = [circle.Axis.x, circle.Axis.y, circle.Axis.z]
            # radius = circle.Radius
            # if self.position == position and self.radius == radius:
            #     if check_parallel(np.array(self.direction), np.array(axis)):
            #         if self.direction == axis:
            #             self.edge_index["aligned"].append(ind + 1)
            #             find_edge = True
            #         else:
            #             self.edge_index["opposed"].append(ind + 1)
            #             find_edge = True
            #         if find_edge:
            #             break
        if not find_edge:
            print("ERROR no edge same with circle")
    def get_position_m(self):
        position = np.array(self.position) * 0.001

        return list(position)

    def reverse(self):
        self.is_reverse = True
        rotate_obj(self.object, 180.0, Base.Vector(self.position), Base.Vector(self.XAxis))
        self.update_frame()

class Hole():
    def __init__(self, position, direction, circle):
        self.doc = get_active_doc()
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
    
    def create_hole(self, hole_name):
        position = Base.Vector(self.start_circle.position)
        direction = Base.Vector(self.direction)
        radius = self.radius_min
        self.name = hole_name
        self.shape = Part.makeCylinder(radius, self.depth, position, direction, 360)
        self.object = show_shape_in_doc(self.shape, hole_name)

    def get_hole_type(self, parent_obj):
        area = _get_common_area(self.doc, self.object, parent_obj)
        if area > 0:
            self.type = "insertion"
            self.radius = self.radius_max
        else:
            self.type = "hole"
            self.radius = self.radius_min
        self.object.Label += self.type
        

    
    def remove_hole(self):
        doc = get_active_doc()
        doc.removeObject(self.object.Name)

def _visualize_frame(obj_name, obj_O, obj_axis):
    """visualize coordinate of object
    
    Arguments:
        obj_name {[type]} -- [description]
        obj_O {[type]} -- [description]
        obj_axis {[type]} -- [description]
    """
    doc = get_active_doc()
    for idx, axis_name in enumerate(obj_axis.keys()):
        frame_name = obj_name + "_axis_" + axis_name
        frame = doc.addObject("Part::Polygon", frame_name)
        frame.Nodes = [obj_O, obj_O + obj_axis[axis_name]]
        doc.recompute()
        color = [0., 0., 0.]
        color[idx] = 1.0
        set_obj_color(frame_name, tuple(color))

def _get_circle_wire(shape):
    """get only circle wires from FreeCAD shape

    Arguments:
        shape {Part.Shape} -- [Shape of object]

    how to get circle:
        - check edges in wire, if no circle edge exits -> is not circle wire
        - check bound box of wire, if no 0 lenght axis -> is not circle wire
        
    Returns:
        circle_wires {list} -- [circle wires in shape]
    """
    circle_wires = []
    for idx, f in enumerate(shape.Faces):
        wires = f.Wires
        for wire in wires:
            is_circle = True
            if not _check_plane_wire(wire):
                continue
            edges = wire.Edges
            for edge in edges:
                if not _check_circle_edge(edge):
                    is_circle = False
            if is_circle:
                circle_wires.append(wire)

    return circle_wires

def _check_plane_wire(wire):
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

def _check_circle_edge(edge):
    is_circle = True
    try:
        if(isinstance(edge.Curve, Part.Circle)):
            pass
        else:
            is_circle = False
    except:
        is_circle = False

    return is_circle

def _wire_to_circle(circle_wire, Edges):
    """wire to class(Circle)
    
    - check each edges in wire
    - get circle information from each circle edges

    Arguments:
        circle_wire {[Part::Wire]} -- [wire constructed by only circles]

    Returns:
        Circles[list] -- [Circles in wire]
    """
    edges = circle_wire.Edges
    unique_circle = []
    
    Circles = []
    for edge in edges:
        circle = edge.Curve
        position = [circle.Center.x, circle.Center.y, circle.Center.z]
        radius = circle.Radius
        XAxis = [circle.XAxis.x, circle.XAxis.y, circle.XAxis.z]
        YAxis = [circle.YAxis.x, circle.YAxis.y, circle.YAxis.z]
        ZAxis = [circle.Axis.x, circle.Axis.y, circle.Axis.z] # == direction of circle
        pos_r = tuple(position + [radius])
        if pos_r in unique_circle:
            pass
        else:
            circle = Circle(radius, edge, position, XAxis, YAxis, ZAxis)
            unique_circle.append(pos_r)
            Circles.append(circle)
    if len(Circles) > 1:
        return None

    return Circles[0]

def _visualize_world_coordinate(frame_name="world"):
    obj_name = frame_name
    obj_O = Base.Vector(0., 0., 0.)
    obj_axis = {
        "x": Base.Vector(1, 0, 0),
        "y": Base.Vector(0, 1, 0),
        "z": Base.Vector(0, 0, 1)
    }
    _visualize_frame(obj_name, obj_O, obj_axis)

def _get_hole_from_circle(circle):
    position = circle.position
    direction = circle.direction

def get_assembly_points(step_path, step_name, logger, doc_path, obj_path, condition=None):
    """get assembly_points from step file

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
    doc_name = step_name
    doc = create_doc(doc_name)
    doc_name = doc.Name #Issue document name sometimes have 1 in the end of name
    file_path = step_path
    obj_name = step_name
    load_step_file(file_path, doc_name, obj_name)

    FreeCADGui.updateGui( )
    FreeCADGui.SendMsgToActiveView("ViewFit")
    obj = doc.ActiveObject
    importOBJ.export(obj, obj_path)
    shape = obj.Shape
    Edges = shape.Edges
    logger.debug(f"Extract Object Name: {obj.Name}")
    circle_wires = _get_circle_wire(shape)
    assembly_holes = []
    #region find circles from cad file
    for idx, wire in enumerate(circle_wires):
        circle = _wire_to_circle(wire, Edges)
        circle_name = "circle_edge" + "_" + str(idx)
        circle.create_circle(circle_name)
        # check reverse condition
        if type(condition) == list:
            if idx in condition:
                circle.reverse()
        is_used = False
        for h in assembly_holes:
            if h.check_circle_in_hole(circle):
                h.add_circle(circle)
                is_used = True
        if not is_used:
            hole = Hole(circle.position, circle.direction, circle)
            assembly_holes.append(hole)
    #endregion
    
    for idx, hole in enumerate(assembly_holes):
        hole.start_circle.get_edge_index_from_shape(shape)
        hole_name = "assembly_point" + "_" + str(idx)
        hole.create_hole(hole_name)
        doc.recompute()
        hole.get_hole_type(obj)
        # hole.remove_hole()
    
    assembly_points = []
    for idx, hole in enumerate(assembly_holes):
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
        # hole.start_circle.visualize_circle_frame_quat()

    doc.saveAs(doc_path)
    close_doc(doc.Name)


    return assembly_points

#endregion

#------------------------------------------------------------
#region assembly Api
class Constraint(object):
    def __init__(self, assembly_point1, assembly_point2):
        self.assembly_point1 = assembly_point1
        self.assembly_point2 = assembly_point2

def initialize_assembly_docs(doc_name):
    doc = create_doc(doc_name)
    part_doc = join(INSTANCE_DOCUMENT_DIR, doc_name + ".FCStd")
    importPartFromFile(doc, part_doc)
    save_assem_doc_as(doc_name)
    obj = get_active_obj()
    close_doc(doc_name)

def _constraint_circular_edge(doc, parent_obj, child_obj, parent_edge, child_edge, direction):
    """add circular edge constraint in document

    Arguments:
        doc {FreeCAD Document} -- [document that assembly part in]
        parent_obj {a2pPart} -- [Part that import by a2pimport function]
        child_obj {a2pPart} -- [Part that import by a2pimport function]
        parent_edge {[string]} -- [Edge{index}]
        child_edge {[string]} -- [Edge{index}]
    
    Conetents:
        class SelectionExObject:
            'allows for selection gate functions to interface with classification functions below'
            def __init__(self, doc, Object, subElementName):
                self.doc = doc
                self.Object = Object
                self.ObjectName = Object.Name
                self.SubElementNames = [subElementName]  
        class CircularEdgeConstraint(BasicConstraint):
            def __init__(self,selection):
                BasicConstraint.__init__(self, selection)
                self.typeInfo = 'circularEdge'
                self.constraintBaseName = 'circularEdge'
                self.iconPath = ':/icons/a2p_CircularEdgeConstraint.svg'
                self.create(selection)
    """
    parent_obj.fixedPosition = True
    child_obj.fixedPosition = False
    s1 = a2plib.SelectionExObject(doc, parent_obj, "Edge" + str(parent_edge))
    s2 = a2plib.SelectionExObject(doc, child_obj, "Edge" + str(child_edge))
    cc = a2pconst.CircularEdgeConstraint([s1, s2])
    if direction:
        cc.direction = "aligned"
    else:
        cc.direction = "opposed"

    return cc.constraintObject

def assemble_parts(part_a_info, part_b_info, part_a_doc, part_b_doc, assembly_pairs):
    """assemle two parts

    Arguments:
        assemble_doc{[string]} -- [instance PATH of assemble document]
        parent_doc {[string]} -- [instance PATH of parent document]
        child_doc {[string]} -- [instance PATH of child document]
    """
    doc, parent = _initialize_assembly(part_a_doc, part_b_doc)
    solsys = solver.SolverSystem()
    # solsys.solveSystem(doc, showFailMessage=False)
    solsys.solveAccuracySteps(doc)
    part_names = list(part_a_info.keys()) + list(part_b_info.keys())
    parts_dic = _get_parts_dic(doc, part_names)
    constraint_num = 0
    init_doc_name = "assmebly_" +  str(get_time_stamp())
    # save_assem_doc_as(init_doc_name)
    # close_doc(init_doc_name)
    proper_doc = init_doc_name
    
    #region add constraint
    assembly_point_pairs = []
    for pair in assembly_pairs:
        parent_name, parent_point_idx = pair[parent]
        child_name, child_point_idx = pair[1 - parent]
        parent_obj = parts_dic[parent_name]
        child_obj = parts_dic[child_name]
        if parent_obj == None or child_obj == None:
            print("ERROR")
        if parent == 0:
            parent_point_info = _get_assembly_point(part_a_info, parent_name, parent_point_idx)
            child_point_info = _get_assembly_point(part_b_info, child_name, child_point_idx)
            parent_dir, parent_edge = _extract_edge_info(parent_point_info)
            child_dir, child_edge = _extract_edge_info(child_point_info)
        else:
            parent_point_info = _get_assembly_point(part_b_info, parent_name, parent_point_idx)
            child_point_info = _get_assembly_point(part_a_info, child_name, child_point_idx)
            parent_dir, parent_edge = _extract_edge_info(parent_point_info)
            child_dir, child_edge = _extract_edge_info(child_point_info)
        # check possible assembly
        if not _check_assembly_points(parent_point_info, child_point_info):
            continue

        
        direction = parent_dir == child_dir
        cc = _constraint_circular_edge(doc=doc,
                                       parent_obj=parent_obj,
                                       child_obj=child_obj,
                                       parent_edge=parent_edge,
                                       child_edge=child_edge,
                                       direction=direction)
        # solve = solsys.solveSystem(doc, showFailMessage=False)
        solve = solsys.solveAccuracySteps(doc)
        # calculate score
        if not solve:
            continue
        else:
            if _check_collision(doc, parent_obj, child_obj):
                doc.removeObject(cc.Name)
                continue
            assembly_point_pairs.append(pair)
            doc_name = "assmebly_" +  str(get_time_stamp())
            save_assem_doc_as(doc_name)
            proper_doc = doc_name
    #endregion
    export_doc_objects_to_obj(doc, proper_doc)
    close_doc(doc.Name)

    return parent, proper_doc, assembly_point_pairs

def _get_parts_dic(doc, part_names):
    parts_dic = {}
    for part_name in part_names:
        object_name = "b_" + part_name + "_001_"
        parts_dic[part_name] = doc.getObject(object_name)
    
    return parts_dic

def _get_assembly_point(part_info, part_name, part_point_idx):
    assembly_point = part_info[part_name][part_point_idx]
    
    return assembly_point

def _extract_edge_info(assembly_point):
    edge_info = assembly_point["edge_index"]
    for direction in edge_info.keys():
        if len(edge_info[direction]) > 0:
            return direction, edge_info[direction][0]
    print("ERROR")
    return None

def _initialize_assembly(part_a_doc, part_b_doc):
    time_stamp = get_time_stamp()
    doc_name = "assmebly_" +  str(time_stamp)
    doc = create_doc(doc_name)
    save_assem_doc_as(doc_name)
    
    part_a_doc_path = join(ASSEMBLY_DOCUMENT_DIR, part_a_doc + ".FCStd")
    part_b_doc_path = join(ASSEMBLY_DOCUMENT_DIR, part_b_doc + ".FCStd")
    doc_a = open_doc(part_a_doc_path)
    doc_b = open_doc(part_b_doc_path)
    objs_a = doc_a.findObjects()
    objs_b = doc_b.findObjects()
    area_a = _get_objs_area(objs_a)
    area_b = _get_objs_area(objs_b)
    _copy_objects_in_docs(doc, objs_a + objs_b)
    
    close_doc(doc_a.Name)
    close_doc(doc_b.Name)

    parts_in_doc = [obj for obj in doc.findObjects() if a2plib.isA2pObject(obj)]
    
    if area_a < area_b:
        parent = 1
    else:
        parent = 0

    return doc, parent
    
def _copy_objects_in_docs(doc, objs):
    """copy object from other doc 
    """
    for obj in objs:
        doc.copyObject(obj)

def _get_objs_area(objs):
    area = 0
    for obj in objs:
        try:
            area += obj.Shape.Area
        except:
            pass

    return area

def _get_common_area(doc, obj1, obj2):
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

# --------------------------------------------------rule--------------------------------------------------
def _check_collision(doc, obj1, obj2):
    is_collision = False
    
    common_area = _get_common_area(doc, obj1, obj2)
    if common_area > 0:
        is_collision = True
    else:
        count = _get_proximity_faces_num(obj1.Shape, obj2.Shape)
        print("face: {}".format(count))
        # if count > 10:
        #     is_collision = True

    return is_collision

def _get_proximity_faces_num(shape1, shape2):
    count = 0
    for face_list in shape1.proximity(shape2):
        for f in face_list:
            count += 1
    
    return count

def _check_assembly_points(parent_point_info, child_point_info):
    parent_type = parent_point_info["type"]
    child_type = child_point_info["type"]        
    
    print(parent_type, child_type)
    
    if parent_type == child_type:
        return False
    else:
        pass
    
    parent_radius = parent_point_info["radius"] 
    child_radius = child_point_info["radius"]
    dif = abs(parent_radius - child_radius) 
    print(dif)

    if dif > 0.5:
        return False
    else:
        pass
    
    return True



#endregion