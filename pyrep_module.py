from os.path import join, splitext
import socket, threading

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape

from script.fileApi import *
from script.const import SocketType, PyRepRequestType
from script.socket_utils import *

    
region_condition = {
    "ikea_stefan_bottom": {
        
    },
    "ikea_stefan_long": {
        0: [0,1,2],
        1: [3,4,5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_middle": {
        0: [0, 1, 2],
        1: [3, 4, 5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_short": {
        0: [0,1,2],
        1: [3,4,5],
        2: [6],
        3: [7]
    },
    "ikea_stefan_side_left": {
        0: [0,1,2],
        1: [4,5,6],
        2: [3,8,9],
        3: [7]
    },
    "ikea_stefan_side_right": {
        0: [0,1,2],
        1: [4,5,6],
        2: [3,8,9],
        3: [7]
    },
}

    

class GroupObject(object):
    def __init__(self, group_info):
        self.group_id = group_info["id"]
        self.obj_root = group_info["obj_root"]
        self.part_name = group_info["part_name"]
        self.import_object_to_scene()

    def import_object_to_scene(self):
        obj_list = get_file_list(self.obj_root)
        for obj_path in obj_list:
            obj_name, ext = get_file_name(obj_path)
            if not ext == ".obj":
                continue
            if obj_name == "base":
                self.base_obj = ObjObject.create_object(obj_path)
            elif "group" in obj_name:
                composed_obj_paths.append(obj_path)

class ObjObject():
    def __init__(self, obj: Shape, frame: Dummy):
        self.shape = obj
        self.frame = frame
        
    @staticmethod
    def create_object(obj_path, scaling_factor=1):
        obj_name, ext = get_file_name(obj_path)
        if not ext == ".obj":
            print("[ERROR] please check obj file {}".format(obj_path))
            exit()
        obj = Shape.import_mesh(obj_path, scaling_factor=scaling_factor)
        obj_base = Dummy.create()
        obj_base.set_parent(obj)

        return ObjObject(obj, frame)

    #region transform -> self.frame
    def get_pose(self, relative_to=None):
        self.frame.get_pose(relative_to=relative_to)    
    
    def set_pose(self, pose, relative_to=None):
        """
        :param pose: An array containing the (X,Y,Z,Qx,Qy,Qz,Qw) pose of
            the object.
        """
        self.frame.set_parent(None)
        self.shape.set_parent(self.frame)
        self.frame.set_pose(pose, relative_to=relative_to)
        self.shape.set_parent(None)
        self.frame.set_parent(self.shape)
        
    
    #endregion

    #region physics and shape property -> self.shape
    def is_dynamic(self):
        return self.shape.is_dynamic()
    def set_dynamic(self, value: bool):
        self.shape.set_dynamic(value)
    
    def is_respondable(self):
        return self.shape.is_respondable()
    def set_respondable(self, value: bool):
        self.shape.set_respondable(value)
    
    def is_collidable(self):
        return self.shape.is_collidable()
    def set_collidable(self, value: bool):
        self.shape.set_collidable(value)
    
    def is_detectable(self):
        return self.shape.is_detectable()
    def set_detectable(self, value: bool):
        self.shape.set_detectable(value)
    
    def is_renderable(self):
        return self.shape.is_renderable()
    def set_renderable(self, value: bool):
        self.shape.set_renderable(value)

    def check_collision(self, obj=None):
        return self.shape.check_collision(obj)    

    #endregion
    def remove(self):
        self.shape.remove()
        self.frame.remove()
    
def import_group_object_to_scene(obj_root, scene):
    # decompose base and each parts
    obj_list = get_file_list(obj_root)
    base_obj_path = ""
    composed_obj_paths = []
    for obj_path in obj_list:
        obj_name, ext = get_file_name(obj_path)
        if not ext == ".obj":
            continue
        if obj_name == "base":
            base_obj_path = obj_path
        elif "group" in obj_name:
            composed_obj_paths.append(obj_path)

class PyRepModule(object):
    def __init__(self, headless=False):
        self.callback = {
            PyRepRequestType.get_region: self.get_region,
            PyRepRequestType.initialize_scene: self.initialize_scene
        }
        self.pr = PyRep()
        self.pr.launch(headless=headless)
        self.pr.start()
        self.scene_th = threading.Thread(target=self.scene_step)
        self.scene_th.start()
        
    def initialize_server(self):
        print("Initialize PyRep Server")
        host = SocketType.pyrep.value["host"]
        port = SocketType.pyrep.value["port"]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(True)
        self.host = host
        self.port = port
        try:
            print("Waiting for PyRep client {}:{}".format(self.host, self.port))
            self.connected_client, addr = self.server.accept()
            print("Connected to {}".format(addr))
        except:
            print("PyRep Server Error")
        finally:
            self.server.close()

    def get_callback(self, request):
        return self.callback[request]

    def get_region(self):
        pass
    
    def initialize_scene(self):
        pass

    def import_primitive_part(self, part_name, part_info):
        part_base = Dummy.create()
        part_base.set_name(part_name + "_base")
        # import each assembly points to scene
        assembly_points = part_info["assembly_points"]
        for a_p in assembly_points:
            idx = a_p["id"]
            radius = a_p["radius"] / 1000
            depth = a_p["depth"]
            position = a_p["pose"]["position"]
            quaternion = a_p["pose"]["quaternion"]
            direction = a_p["direction"]
            assembly_point = Shape.create(PrimitiveShape.CYLINDER,
                                          size=[radius*2, radius*2, depth],
                                          respondable=False,
                                          static=True,
                                          )
            pose = position + quaternion           
            assembly_point.set_pose(pose)
            assembly_point.set_name(part_name + "_asm_point_" + str(idx))
            assembly_point.set_parent(part_base)
    
    def scene_step(self):
        try:
            while True:
                self.pr.step()
        except:
            print("pyrep error")
    
    def save_scene(self, path):
        self.pr.export_scene(path)

    def close(self):
        self.connected_client.close()
        self.server.close()
        self.pr.stop()
        self.pr.shutdown()

if __name__ == "__main__":
    pyrep_module = PyRepModule()
    pyrep_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(pyrep_module.connected_client)
            print("Get request to {}".format(request))
            callback = pyrep_module.get_callback(request)
            callback()
        except:
            break
    pyrep_module.close()    
    


    
    
    