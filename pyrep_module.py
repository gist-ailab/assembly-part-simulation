from os.path import join, splitext
import socket, threading

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape

from script.fileApi import *
from script.const import SocketType, PyRepRequestType
from script.socket_utils import *


class GroupObj():
    def __init__(self, base_obj, composed_parts):
        self.base_obj = base_obj
        self.composed_parts = composed_parts

class ObjObject():
    def __init__(self, obj: Shape, frame: Dummy):
        self.shape = obj
        self.frame = frame
        
    @staticmethod
    def create_object(obj_path, scaling_factor=0.001):
        obj_name, ext = get_file_name(obj_path)
        if not ext == ".obj":
            print("[ERROR] please check obj file {}".format(obj_path))
            exit()
        obj = Shape.import_mesh(obj_path, scaling_factor=scaling_factor)
        frame = Dummy.create()
        frame.set_parent(obj)

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
    
    def set_parent(self, parent):
        self.shape.set_parent(parent)

    def set_name(self, name):
        self.shape.set_name(name)
        self.frame.set_name("{}_frame".format(name))

    def remove(self):
        self.shape.remove()
        self.frame.remove()
    
class PyRepModule(object):
    def __init__(self, logger, headless=False):
        self.logger = logger
        self.callback = {
            PyRepRequestType.get_region: self.get_region,
            PyRepRequestType.initialize_scene: self.initialize_scene
        }
        self.pr = PyRep()
        self.pr.launch(headless=headless)
        self.pr.start()
        self.scene_th = threading.Thread(target=self.scene_binding)
        self.scene_th.start()

        # used to visualize and assembly
        self.part_info = None
        self.part_bases = {}
        self.group_info = None
        self.group_obj = {}

    def initialize_server(self):
        self.logger.info("Initialize PyRep Server")
        host = SocketType.pyrep.value["host"]
        port = SocketType.pyrep.value["port"]
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(True)
        self.host = host
        self.port = port
        try:
            self.logger.info("Waiting for PyRep client {}:{}".format(self.host, self.port))
            self.connected_client, addr = self.server.accept()
            self.logger.info("Connected to {}".format(addr))
        except:
            self.logger.info("PyRep Server Error")
        finally:
            self.server.close()

    def get_callback(self, request):
        return self.callback[request]

    def scene_binding(self):
        try:
            while True:
                self.pr.step()
        except:
            self.logger.info("pyrep error")
    
    def save_scene(self, path):
        self.pr.export_scene(path)

    def close(self):
        self.connected_client.close()
        self.server.close()
        self.pr.stop()
        self.pr.shutdown()

    #region socket function
    def get_region(self):
        pass
    
    def initialize_scene(self):
        self.logger.info("ready to initialize scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.part_info = request["part_info"]
        self.group_info = request["group_info"]
        self.logger.info("...initializing pyrep scene")
        for part_name in self.part_info.keys():
            self._import_part_info(part_name)
        for group_id in self.group_info.keys():
            self._import_group_obj(group_id)
        self.logger.info("End to initialize pyrep scene")
        sendall_pickle(self.connected_client, True)

    def _import_part_info(self, part_name):
        assert self.part_info
        self.logger.info("import part info of {}".format(part_name))
        part_base = Dummy.create()
        part_base.set_name(part_name + "_base")
        # import each assembly points to scene
        assembly_points = self.part_info[part_name]["assembly_points"]
        for idx in assembly_points.keys():
            ap = assembly_points[idx]
            radius = ap["radius"] / 1000
            depth = ap["depth"]
            position = ap["pose"]["position"]
            quaternion = ap["pose"]["quaternion"]
            direction = ap["direction"]
            assembly_point = Shape.create(PrimitiveShape.SPHERE,
                                          size=[radius]*3,
                                          respondable=False,
                                          static=True,
                                          )
            pose = position + quaternion         
            assembly_point.set_pose(pose)
            assembly_point.set_name(part_name + "_asm_point_" + str(idx))
            assembly_point.set_parent(part_base)
        self.part_bases[part_name] = part_base
    
    def _import_group_obj(self, group_id):
        assert self.group_info
        group_info = self.group_info[group_id]
        obj_root = group_info["obj_root"]
        file_list = get_file_list(obj_root)

        base_obj = None
        composed_parts = {}
        count = 0
        for file_path in file_list:
            obj_name, ext = get_file_name(file_path)
            if not ext == ".obj":
                continue

            if obj_name == "base": # import base object
                base_obj = ObjObject.create_object(file_path)
                base_obj.set_name("group_{}".format(group_id))
            else:
                part_name = obj_name
                obj = ObjObject.create_object(file_path)
                obj.set_name("group_{}_composed_part_{}".format(group_id, count))
                count += 1
                composed_parts[part_name] = obj
        assert base_obj, "No base object"
        for part_name in composed_parts.keys():
            obj = composed_parts[part_name]
            obj.set_parent(base_obj.shape)
        self.group_obj[group_id] = GroupObj(base_obj, composed_parts)

    def update_scene(self):
        pass

    #endregion
    
    
if __name__ == "__main__":
    logger = get_logger("PyRep_Module")
    pyrep_module = PyRepModule(logger)
    pyrep_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(pyrep_module.connected_client)
            self.logger.info("Get request to {}".format(request))
            callback = pyrep_module.get_callback(request)
            callback()
        except Exception as e:
            self.logger.info("Error occur {}".format(e))
            break
    pyrep_module.close()    
    


    
    
    