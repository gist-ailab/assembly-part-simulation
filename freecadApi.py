import import_fcstd
import FreeCAD
import FreeCADGui
import os
from os.path import join, isfile, isdir
from os import listdir
import Part
from FreeCAD import Base
from scipy.spatial.transform import Rotation as R
import numpy as np
from decimal import Decimal
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
FREECAD_DOCUMENT_PATH = join(CURRENT_PATH, "FCDocument")


if not os.path.isdir(FREECAD_DOCUMENT_PATH):
    os.mkdir(FREECAD_DOCUMENT_PATH)
else:
    pass


def float_to_exponential(float_value_list):
    ex_list = []
    for val in float_value_list:
        ex_list.append('{:.5E}'.format(Decimal(val)))
    
    return ex_list

def get_quat_from_dcm(x, y, z):
    r = R.from_dcm(np.array([x, y, z]))
    r = r.as_quat()
    r = list(r)

    return r
    
def show_shape_in_doc(shape, label):
    doc = get_active_doc()
    if doc == None:
        print("Please create active document")
        return False
    Part.show(shape)
    obj = doc.ActiveObject
    obj.Label = label

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

def create_doc(doc_name, headless=False):
    if not headless:
        FreeCADGui.showMainWindow()
    doc = FreeCAD.newDocument(doc_name)

    return doc

def save_doc(save_doc_name):
    save_doc_name += ".FCStd"
    save_doc_path = join(FREECAD_DOCUMENT_PATH, save_doc_name)
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
        
def load_step_file(path, doc_name):
    doc = get_active_doc()
    if doc == None:
        print("Please create active document")
        return False
    Part.insert(path, doc_name)
    obj = get_active_obj()

    return True

#-------------------------------------------------------------
#region extract cad info

class Circle(object):
    def __init__(self, radius, position, XAxis, YAxis, ZAxis, edge_id):
        self.radius = radius
        self.position = position
        self.XAxis = XAxis
        self.YAxis = YAxis
        self.direction = ZAxis
        self.edge_id = edge_id
        self.quaternion = get_quat_from_dcm(self.XAxis, self.YAxis, self.direction)
    
    def create_circle(self):
        position = Base.Vector(self.position)
        direction = Base.Vector(self.direction)
        
        self.shape = Part.makeCircle(self.radius, position, direction, 0, 360)
        
        return self.shape
    
    def set_name(self, name):
        self._name = name

    def visualize_frame(self):
        doc = get_active_doc()
        obj = get_object(self._name)
        obj_O = Base.Vector(self.position)
        obj_frame = []
        
        obj_frame.append(obj_O + Base.Vector(self.XAxis))
        obj_frame.append(obj_O + Base.Vector(self.YAxis))
        obj_frame.append(obj_O + Base.Vector(self.direction))
        
        for idx, axis_point in enumerate(obj_frame):
            frame_name = self._name + "_axis_" + str(idx)        
            frame = doc.addObject("Part::Polygon", frame_name)
            frame.Nodes = [obj_O, axis_point]
            doc.recompute()
            color = [0., 0., 0.]
            color[idx] = 1.0
            set_obj_color(frame_name, tuple(color))

def get_circle_wire(shape):
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
    plane_condition = 1e-3
    for idx, f in enumerate(shape.Faces):
        wires = f.Wires
        for wire in wires:
            is_circle = True
            bbox = wire.BoundBox
            X_Length = bbox.XLength
            Y_Length = bbox.YLength
            Z_Length = bbox.ZLength
            if X_Length < plane_condition or Y_Length < plane_condition or Z_Length < plane_condition:
                pass
            else:
                is_circle = False
                continue
            edges = wire.Edges
            for edge in edges:
                try:
                    if(isinstance(edge.Curve, Part.Circle)):
                        pass
                    else:
                        is_circle = False
                except:
                    is_circle = False
            if is_circle:
                circle_wires.append(wire)

    return circle_wires

def wire_to_circle(circle_wire, Edges):
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
            edge_id = Edges.index(edge)
            circle = Circle(radius, position, XAxis, YAxis, ZAxis, edge_id)
            unique_circle.append(pos_r)
            Circles.append(circle)
    
    return Circles

def get_assembly_points(step_path, step_name):
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
    assembly_points = []
    doc_name = "extract_part_info"
    doc = create_doc(doc_name, headless=False) # if headless==True, created obj has no visibility
    file_path = step_path
    while not load_step_file(file_path, doc_name):
        pass
    obj = doc.ActiveObject
    shape = obj.Shape
    Edges = shape.Edges
    print(f"Extract Object Name: {obj.Name}")
    circle_wires = get_circle_wire(shape)
    active_cirlce = []
    for idx, wire in enumerate(circle_wires):
        circle_list = wire_to_circle(wire, Edges)
        if len(circle_list) > 1:
            print("too many circle in one wire!!")
            continue
        circle = circle_list[0]
        assembly_point = {
            "id": idx,
            "Edge_id": circle.edge_id,
            "radius": circle.radius,
            "pose": {
                "position": float_to_exponential(circle.position),
                "quaternion": float_to_exponential(circle.quaternion)
            }
        }
        assembly_points.append(assembly_point)
        circle_shape = circle.create_circle()
        circle_name = "circle_edge" + "_" + str(idx)
        circle.set_name(circle_name)
        circle.visualize_frame()
        show_shape_in_doc(circle_shape, circle_name)
        active_cirlce.append(circle)

    # new_circles = check_symmetry(active_cirlce)
    # for n_idx, circle in enumerate(new_circles):
    #     assembly_point = {
    #         "id": n_idx + idx + 1,
    #         "pose": {
    #             "position": float_to_exponential(circle.position),
    #             "direction": float_to_exponential(circle.quaternion)
    #         },
    #         "is_used": False
    #     }
    #     assembly_points.append(assembly_point)
    #     circle_shape = circle.create_circle()
    #     circle_name = "circle_edge" + "_" + str(n_idx + idx + 1)
    #     show_shape_in_doc(circle_shape, circle_name)

    compound_name = step_name + "_compound"
    compound_doc_objects(compound_name)
    save_doc_name = step_name
    save_doc(save_doc_name)
    close_doc(doc_name)

    return assembly_points

#endregion

#------------------------------------------------------------
#region assembly
import a2plib
from a2p_importpart import importPartFromFile
import a2p_constraints as a2pconst
import a2p_solversystem as solver

class circular_edge_constraint(object):
    def __init__(self, doc, )

def constraint_circular_edge(doc, obj1, edge1, obj2, edge2):
    # obj1, obj2 are a2pPart
    # edge1, edge2 == "Edge71", "Edge3"
    s1 = a2plib.SelectionExObject(doc, obj1, edge1)
    s2 = a2plib.SelectionExObject(doc, obj2, edge2)
    cc = a2pconst.CircularEdgeConstraint([s1, s2])

def solve_constraints(doc):
    solsys = solver.SolverSystem()
    solsys.solveSystem(doc)

def assemble_A_and_B(partA_name, partB_name):
    doc_name = "assemble"
    # load assemble points
    # for all assemble points pairs 



#endregion