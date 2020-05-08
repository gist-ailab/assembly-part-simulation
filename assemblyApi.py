import import_fcstd
import FreeCADGui

import Part
import a2plib
import a2p_constraints as a2pconst
import os
from os import listdir
import os.path
from os.path import join, isfile, isdir



# file path
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
STATUS_PATH = join(CURRENT_PATH, "assembly_status")
if not os.path.isdir(STATUS_PATH):
    os.mkdir(STATUS_PATH)


"""how to use a2plus
0. save FCStd file
1. add a part from external file(*.FCStd) 
    - added part is <class 'FeaturePython'>
        == a2plib.isA2pPart / a2plib.isA2pObject is True

2. select two edge for assemble
    - sel = FreeCADGui.Selection.GetSelction()
    - sel.addSelection(obj, ["Edge2",position]) ex. edge3, edge14

3. create instance of Selection class in a2plib
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
s1 = a2plib.SelectionExObject(doc, long, "Edge14")
s2 = a2plib.SelectionExObject(doc, braket, "Edge3")ehdgoanfhr oqjalkqornetks lakfmrhekfgheh gksmald lqhdngkalsdkfj02840293840923840slkdjflskdjowieuroiwlskdjfnv           


ehdgoanfhkr oqnlskdjflaksdjf

4. add circular edge constraints
cc = a2pconst.CircularEdgeConstraint([s1, s2])
class CircularEdgeConstraint(BasicConstraint):
    def __init__(self,selection):
        BasicConstraint.__init__(self, selection)
        self.typeInfo = 'circularEdge'
        self.constraintBaseName = 'circularEdge'
        self.iconPath = ':/icons/a2p_CircularEdgeConstraint.svg'
        self.create(selection)
        
    def calcInitialValues(self):
        c = self.constraintObject
        circleEdge1 = getObjectEdgeFromName(self.ob1, c.SubElement1)
        circleEdge2 = getObjectEdgeFromName(self.ob2, c.SubElement2)
        axis1 = circleEdge1.Curve.Axis
        axis2 = circleEdge2.Curve.Axis
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            self.direction = "aligned"
        else:
            self.direction = "opposed"
        self.offset = 0.0
        self.lockRotation = False

    @staticmethod
    def recalculateMatingDirection(c):
        ob1 = c.Document.getObject(c.Object1)
        ob2 = c.Document.getObject(c.Object2)
        circleEdge1 = getObjectEdgeFromName(ob1, c.SubElement1)
        circleEdge2 = getObjectEdgeFromName(ob2, c.SubElement2)
        axis1 = circleEdge1.Curve.Axis
        axis2 = circleEdge2.Curve.Axis
        angle = math.degrees(axis1.getAngle(axis2))
        if angle <= 90.0:
            direction = "aligned"
        else:
            direction = "opposed"
        if c.directionConstraint != direction:
            c.offset = -c.offset
        c.directionConstraint = direction    

    @staticmethod
    def getToolTip():
        return \
'''
Add a circularEdge constraint between two parts
selection-hint:
1.) select circular edge on first importPart
2.) select circular edge on other importPart
Button gets active after
correct selection.
'''

    @staticmethod
    def isValidSelection(selection):
        validSelection = False
        if len(selection) == 2:
            s1, s2 = selection
            if s1.ObjectName != s2.ObjectName:
                if CircularEdgeSelected(s1) and CircularEdgeSelected(s2):
                    validSelection = True
        return validSelection
"""
