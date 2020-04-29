import import_fcstd
import FreeCADGui
import Part
import a2plib
import os
from os import listdir
import os.path
from os.path import join, isfile, isdir



# file path
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
STEP_DIR = join(CURRENT_PATH, "step_file")



class assemble_document(object):

    def __init__(self, stage_num, stage_objects):
        FreeCADGui.showMainWindow()
        self.project = "assembly_" + str(stage_num)
        self.status = 0
        self.doc = FreeCAD.newDocument("status_{}".format(self.status))
        FreeCADGui.ActiveDocument
        self.stage_objects = stage_objects
        self.load_obj_file_to_doc(stage_objects)
        

    def load_obj_file_to_doc(self, stage_objects):
        for obj_path, obj_num in stage_objects:
            for i in range(obj_num):
                doc.load_step_file(obj_path)
        
        temp_shape = Part.Shape()
        temp_shape.read(path)
        
        self.shapes.append(temp_shape)


    def get_pf_list(self):
        return self.doc.findObjects()

    def get_shapes(self):
        return self.shapes

    def save(self):
        try:
            os.mkdir(join(CURRENT_PATH, "Stage_{}".format()))
        except FileExistsError:
            pass
        save_doc_name = join(CURRENT_PATH, self.name, )
        self.doc.saveAs(save_doc_name)

class assemble_object(object):

    def __init__(self, obj_path):
        self.shape = Part.Shape().read(obj_path)
        
if __name__ == "__main__":
    # get stage infomation from assembly instruction
    """ example for stage 1
    chair braket(4ea).STEP: 4
    chair part3.STEP: 1
    chair part4.STEP: 1
    + pose data
    """
    stage_num = 0
    stage_objects = [("chair braket(4ea).STEP", 4),
                     ("chair part3.STEP", 1),
                     ("chair part3.STEP", 1)]
    # initialize document
    doc = assemble_document(stage_num, stage_objects)

    


