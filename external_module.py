import random as rd

class FreeCAD(object):
    def __init__(self):
        pass
    

class Pyrep(object):
    def __init__(self):
        pass
    
    def request_assembly_region(self, group_info, target):
        print(group_info)
        print(target)
        return rd.randint(0, 2)




freecad_module = FreeCAD()
pyrep_module = Pyrep()
