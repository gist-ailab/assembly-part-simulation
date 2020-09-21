from script import fileApi
from script import import_fcstd



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

