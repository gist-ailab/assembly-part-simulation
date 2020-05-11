import import_fcstd
import FreeCADGui

import Part

import os
from os import listdir
import os.path
from os.path import join, isfile, isdir



# file path
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))

def create_circular_edge_constraints(doc, a2p_obj1, o2p_obj2, ind1, ind2):




"""how to use a2plus
0. save FCStd file
    => from freecadApi import save_doc 
    => a2p_test.FCStd

1. add a part from external file(*.FCStd) 
    => doc = FreeCAD.ActiveDocument
    => from a2p_importpart import importPartFromFile
    => importPartFromFile(doc, "D:/workspace/Assembly-Part-Simulation/FCDocument/flat_head_screw_iso.FCStd")
        //added part is <class 'FeaturePython'>
        == a2plib.isA2pPart / a2plib.isA2pObject is True

2. select two edge for assemble
    => obj1, obj2 = FreeCAD.ActiveDocument.findObjects() 
        // obj1.Label = 'ikea_stefan_middle_001'
        // obj2.Label = 'ikea_wood_001'
        // type(obj1) = FeaturePython
        // obj1.objectType = a2pPart
        // obj1.fixedPosition = True, obj2.fixedPosition = False
            // one object should be fixed
    => sel = FreeCADGui.Selection.getSelction()
     

3. create instance of Selection class in a2plib
    => s1 = a2plib.SelectionExObject(doc, obj1, "Edge71")
    => s2 = a2plib.SelectionExObject(doc, obj2, "Edge3")
        class SelectionRecord:
        def __init__(self, docName, objName, sub):
            self.Document = FreeCAD.getDocument(docName)
            self.ObjectName = objName
            self.Object = self.Document.getObject(objName)
            self.SubElementNames = [sub]
        class SelectionExObject:
        'allows for selection gate functions to interface with classification functions below'
        def __init__(self, doc, Object, subElementName):
            self.doc = doc
            self.Object = Object
            self.ObjectName = Object.Name
            self.SubElementNames = [subElementName]  

4. add circular edge constraints
    # create constraints
        => cc = a2pconst.CircularEdgeConstraint([s1, s2])


    # solve constraints
        => import a2p_solversystem as solver
        => solsys = solver.SolverSystem()
        => solsys.solveSystem(doc)
            // True / False
"""

