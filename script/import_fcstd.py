import sys
from enum import Enum

"""work only local python 3
"""
class ENVPATH(Enum):
    raeyo_ubuntu = ['/home/raeyo/.FreeCAD/Mod/A2plus', '/usr/share/freecad/Mod/Test', '/usr/share/freecad/Mod/Mesh', '/usr/share/freecad/Mod/Tux', '/usr/share/freecad/Mod/Measure', '/usr/share/freecad/Mod/Drawing', '/usr/share/freecad/Mod/Fem', '/usr/share/freecad/Mod/Surface', '/usr/share/freecad/Mod/Inspection', '/usr/share/freecad/Mod/Start', '/usr/share/freecad/Mod/Draft', '/usr/share/freecad/Mod/Web', '/usr/share/freecad/Mod/Idf', '/usr/share/freecad/Mod/Image', '/usr/share/freecad/Mod/Robot', '/usr/share/freecad/Mod/Sketcher', '/usr/share/freecad/Mod/MeshPart', '/usr/share/freecad/Mod/Material', '/usr/share/freecad/Mod/Raytracing', '/usr/share/freecad/Mod/Import', '/usr/share/freecad/Mod/OpenSCAD', '/usr/share/freecad/Mod/Ship', '/usr/share/freecad/Mod/Show', '/usr/share/freecad/Mod/Arch', '/usr/share/freecad/Mod/Plot', '/usr/share/freecad/Mod/ReverseEngineering', '/usr/share/freecad/Mod/TechDraw', '/usr/share/freecad/Mod/PartDesign', '/usr/share/freecad/Mod/Complete', '/usr/share/freecad/Mod/AddonManager', '/usr/share/freecad/Mod/Part', '/usr/share/freecad/Mod/Path', '/usr/share/freecad/Mod/Points', '/usr/share/freecad/Mod/Spreadsheet', '/usr/share/freecad/Mod', '/usr/lib/freecad/lib64', '/usr/lib/freecad-python3/lib', '/usr/share/freecad/Ext', '/usr/lib/freecad/bin', '/usr/lib/python36.zip', '/usr/lib/python3.6', '/usr/lib/python3.6/lib-dynload', '/home/raeyo/.local/lib/python3.6/site-packages', '/usr/local/lib/python3.6/dist-packages', '/usr/lib/python3/dist-packages', '', '/usr/lib/freecad/Macro']
    raeyo_win = ['C:/Users/KANG/AppData/Roaming/FreeCAD/Mod/A2plus', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Web', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Tux', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Test', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/TechDraw', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Surface', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Start', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Spreadsheet', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Sketcher', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Show', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Ship', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Robot', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Raytracing', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Points', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Plot', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Path', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/PartDesign', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Part', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/OpenSCAD', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/MeshPart', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Mesh', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Measure', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Material', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Inspection', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Import', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Image', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Idf', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Fem', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Drawing', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Draft', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Complete', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/Arch', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod/AddonManager', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Mod', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/lib64', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/lib', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Ext', 'D:/Dropbox/raeyo/workspace/furniture/Assembly-Part-Simulation', 'C:/Users/KANG/Anaconda3/envs/freecad/python36.zip', 'C:/Users/KANG/Anaconda3/envs/freecad/DLLs', 'C:/Users/KANG/Anaconda3/envs/freecad/lib', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/bin', 'C:/Users/KANG/Anaconda3/envs/freecad', 'C:/Users/KANG/Anaconda3/envs/freecad/lib/site-packages', 'C:/Users/KANG/Anaconda3/envs/freecad/Library/Macro']

#TODO: check before running script
FREECADPATH = ENVPATH.raeyo_ubuntu.value

for path in FREECADPATH:
    if path in sys.path:
        continue
    sys.path.append(path)

try:
    import FreeCAD
    import FreeCADGui
    FreeCADGui.showMainWindow()
    
except:
    print("Could not import FreeCAD")
