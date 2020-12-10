import sys
from enum import Enum

class ENVPATH:
    raeyo_ubuntu = ['/home/raeyo/anaconda3/envs/freecad/Mod/Sketcher', '/home/raeyo/anaconda3/envs/freecad/Mod/Complete', '/home/raeyo/anaconda3/envs/freecad/Mod/Part', '/home/raeyo/anaconda3/envs/freecad/Mod/TechDraw', '/home/raeyo/anaconda3/envs/freecad/Mod/Fem', '/home/raeyo/anaconda3/envs/freecad/Mod/Draft', '/home/raeyo/anaconda3/envs/freecad/Mod/Web', '/home/raeyo/anaconda3/envs/freecad/Mod/Test', '/home/raeyo/anaconda3/envs/freecad/Mod/Inspection', '/home/raeyo/anaconda3/envs/freecad/Mod/Measure', '/home/raeyo/anaconda3/envs/freecad/Mod/Material', '/home/raeyo/anaconda3/envs/freecad/Mod/Path', '/home/raeyo/anaconda3/envs/freecad/Mod/Points', '/home/raeyo/anaconda3/envs/freecad/Mod/A2plus', '/home/raeyo/anaconda3/envs/freecad/Mod/Show', '/home/raeyo/anaconda3/envs/freecad/Mod/Arch', '/home/raeyo/anaconda3/envs/freecad/Mod/MeshPart', '/home/raeyo/anaconda3/envs/freecad/Mod/Surface', '/home/raeyo/anaconda3/envs/freecad/Mod/Drawing', '/home/raeyo/anaconda3/envs/freecad/Mod/AddonManager', '/home/raeyo/anaconda3/envs/freecad/Mod/Raytracing', '/home/raeyo/anaconda3/envs/freecad/Mod/PartDesign', '/home/raeyo/anaconda3/envs/freecad/Mod/Robot', '/home/raeyo/anaconda3/envs/freecad/Mod/Import', '/home/raeyo/anaconda3/envs/freecad/Mod/Tux', '/home/raeyo/anaconda3/envs/freecad/Mod/Spreadsheet', '/home/raeyo/anaconda3/envs/freecad/Mod/OpenSCAD', '/home/raeyo/anaconda3/envs/freecad/Mod/Image', '/home/raeyo/anaconda3/envs/freecad/Mod/Idf', '/home/raeyo/anaconda3/envs/freecad/Mod/Start', '/home/raeyo/anaconda3/envs/freecad/Mod/ReverseEngineering', '/home/raeyo/anaconda3/envs/freecad/Mod/Mesh', '/home/raeyo/anaconda3/envs/freecad/Mod', '/home/raeyo/anaconda3/envs/freecad/lib64', '/home/raeyo/anaconda3/envs/freecad/lib', '/home/raeyo/anaconda3/envs/freecad/Ext', '', '/home/raeyo/anaconda3/envs/freecad/lib/python37.zip', '/home/raeyo/anaconda3/envs/freecad/lib/python3.7', '/home/raeyo/anaconda3/envs/freecad/lib/python3.7/lib-dynload', '/home/raeyo/anaconda3/envs/freecad/lib/python3.7/site-packages', '', '/home/raeyo/anaconda3/envs/freecad/Macro']
    raeyo_win = ['C:/Users/KANG/AppData/Roaming/FreeCAD/Mod/A2plus', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Web', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Tux', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Test', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/TechDraw', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Surface', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Start', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Spreadsheet', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Sketcher', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Show', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Ship', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Robot', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Raytracing', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Points', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Plot', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Path', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/PartDesign', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Part', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/OpenSCAD', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/MeshPart', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Mesh', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Measure', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Material', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Inspection', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Import', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Image', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Idf', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Fem', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Drawing', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Draft', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Complete', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Arch', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/AddonManager', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/lib64', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/lib', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Ext', 'D:/Dropbox/raeyo/workspace/furniture/Assembly-Part-Simulation', 'C:/Users/KANG/Anaconda3/envs/freecad/python36.zip', 'C:/Users/KANG/Anaconda3/envs/freecad/DLLs', 'C:/Users/KANG/Anaconda3/envs/freecad/lib', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/bin', 'C:/Users/KANG/Anaconda3/envs/freecad', 'C:/Users/KANG/Anaconda3/envs/freecad/lib/site-packages', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Macro']
    joo = ['C:/Users/joo/anaconda3/envs/py36/Library/Mod/Web', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Tux', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Test', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/TechDraw', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Surface', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Start', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Spreadsheet', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Sketcher', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Show', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Ship', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Robot', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Raytracing', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Points', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Plot', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Path', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/PartDesign', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Part', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/OpenSCAD', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/MeshPart', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Mesh', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Measure', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Material', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Inspection', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Import', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Image', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Idf', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Fem', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Drawing', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Draft', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Complete', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/Arch', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod/AddonManager', 'C:/Users/joo/anaconda3/envs/py36/Library/Mod', 'C:/Users/joo/anaconda3/envs/py36/Library/lib64', 'C:/Users/joo/anaconda3/envs/py36/Library/lib', 'C:/Users/joo/anaconda3/envs/py36/Library/Ext', 'C:/Users/joo', 'C:/Users/joo/anaconda3/envs/py36/python36.zip', 'C:/Users/joo/anaconda3/envs/py36/DLLs', 'C:/Users/joo/anaconda3/envs/py36/lib', 'C:/Users/joo/anaconda3/envs/py36/Library/bin', 'C:/Users/joo/anaconda3/envs/py36', 'C:/Users/joo/anaconda3/envs/py36/lib/site-packages', 'C:/Users/joo/anaconda3/envs/py36/Library/Macro']
    dyros = ['/home/dyros/.FreeCAD/Mod/A2plus', '/home/dyros/anaconda3/envs/freecad/Mod/Test', '/home/dyros/anaconda3/envs/freecad/Mod/Mesh', '/home/dyros/anaconda3/envs/freecad/Mod/Part', '/home/dyros/anaconda3/envs/freecad/Mod/Measure', '/home/dyros/anaconda3/envs/freecad/Mod/Points', '/home/dyros/anaconda3/envs/freecad/Mod/Import', '/home/dyros/anaconda3/envs/freecad/Mod/Inspection', '/home/dyros/anaconda3/envs/freecad/Mod/Image', '/home/dyros/anaconda3/envs/freecad/Mod/Complete', '/home/dyros/anaconda3/envs/freecad/Mod/PartDesign', '/home/dyros/anaconda3/envs/freecad/Mod/Fem', '/home/dyros/anaconda3/envs/freecad/Mod/Material', '/home/dyros/anaconda3/envs/freecad/Mod/Drawing', '/home/dyros/anaconda3/envs/freecad/Mod/Web', '/home/dyros/anaconda3/envs/freecad/Mod/MeshPart', '/home/dyros/anaconda3/envs/freecad/Mod/Start', '/home/dyros/anaconda3/envs/freecad/Mod/Show', '/home/dyros/anaconda3/envs/freecad/Mod/Idf', '/home/dyros/anaconda3/envs/freecad/Mod/Path', '/home/dyros/anaconda3/envs/freecad/Mod/Sketcher', '/home/dyros/anaconda3/envs/freecad/Mod/Raytracing', '/home/dyros/anaconda3/envs/freecad/Mod/Tux', '/home/dyros/anaconda3/envs/freecad/Mod/ReverseEngineering', '/home/dyros/anaconda3/envs/freecad/Mod/AddonManager', '/home/dyros/anaconda3/envs/freecad/Mod/Spreadsheet', '/home/dyros/anaconda3/envs/freecad/Mod/TechDraw', '/home/dyros/anaconda3/envs/freecad/Mod/Draft', '/home/dyros/anaconda3/envs/freecad/Mod/Surface', '/home/dyros/anaconda3/envs/freecad/Mod/Arch', '/home/dyros/anaconda3/envs/freecad/Mod/OpenSCAD', '/home/dyros/anaconda3/envs/freecad/Mod/Robot', '/home/dyros/anaconda3/envs/freecad/Mod', '/home/dyros/anaconda3/envs/freecad/lib64', '/home/dyros/anaconda3/envs/freecad/lib', '/home/dyros/anaconda3/envs/freecad/Ext', '', '/home/dyros/anaconda3/envs/freecad/lib/python37.zip', '/home/dyros/anaconda3/envs/freecad/lib/python3.7', '/home/dyros/anaconda3/envs/freecad/lib/python3.7/lib-dynload', '/home/dyros/anaconda3/envs/freecad/lib/python3.7/site-packages', '/home/dyros/.FreeCAD/Macro/', '/home/dyros/anaconda3/envs/freecad/Macro'] 
    extra = ["sys.path of FreeCAD python console"]


#TODO: check before running script
# FREECADPATH = ENVPATH.raeyo_ubuntu
FREECADPATH = ENVPATH.dyros

for path in FREECADPATH:
    if path in sys.path:
        continue
    sys.path.append(path)

try:
    import FreeCAD
    import FreeCADGui
    
except:
    print("Could not import FreeCAD")

if __name__ == "__main__":
    import time
    FreeCADGui.showMainWindow()
    doc = FreeCAD.newDocument()
    FreeCAD.ActiveDocument = FreeCAD.getDocument(doc.Name)
    FreeCADGui.ActiveDocument = FreeCADGui.getDocument(doc.Name)
    view = FreeCADGui.ActiveDocument.ActiveView
    mw = FreeCADGui.getMainWindow()
    print(mw)
    loop()

    
    while True:
        view.fitAll()