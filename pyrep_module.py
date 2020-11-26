from os.path import join, splitext
import socket, threading

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape
from pyrep.objects.camera import Camera

from script.fileApi import *
from script.const import SocketType, PyRepRequestType
from script.socket_utils import *


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

class GroupObj():
    def __init__(self, base_obj: ObjObject, composed_parts):
        self.base_obj = base_obj
        self.composed_parts = composed_parts

    def get_region_id(self, location, part_bases):
        assert part_bases
        target_region_id = None
        min_distance = np.inf
        temp_dummy = Dummy.create()
        # relative to bounding box center
        temp_dummy.set_position(location, relative_to=self.base_obj.shape)
        connection_pos = np.array(temp_dummy.get_position())
        for part_instance in self.composed_parts:
            part_name = part_instance["part_name"]
            part_object = self.composed_parts[part_instance]
            part_base = part_bases[part_name]["base"]
            regions = part_bases[part_name]["region"]
            part_base.set_pose(part_object.frame.get_pose())

            for region_id in regions.keys():
                region_dummy = regions[region_id]
                pos = np.array(region_dummy.get_position())
                distance = np.linalg.norm(connection_pos - pos)
                if distance < min_distance:
                    min_distance = distance
                    target_region_id = region_id
        
        temp_dummy.remove()

        return target_region_id
            

    def remove(self):
        self.base_obj.remove()
        for part in self.composed_parts:
            part.remove()

class PyRepModule(object):
    def __init__(self, logger, headless=False):
        self.logger = logger
        self.callback = {
            PyRepRequestType.initialize_part_to_scene: self.initialize_part_to_scene,
            PyRepRequestType.update_group_to_scene: self.update_group_to_scene,
            PyRepRequestType.get_region_id: self.get_region_id
        }
        self.pr = PyRep()
        self.pr.launch("scene/demo.ttt", headless=headless)
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
    def initialize_part_to_scene(self):
        self.logger.info("ready to initialize part to scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.part_info = request["part_info"]
        self.logger.info("...initializing pyrep scene")
        for part_name in self.part_info.keys():
            self._import_part_info(part_name)
        self.logger.info("End to initialize pyrep scene")
        sendall_pickle(self.connected_client, True)

    def _import_part_info(self, part_name):
        assert self.part_info
        self.logger.info("import part info of {}".format(part_name))
        part_base = Dummy.create()
        part_base.set_name(part_name + "_base")
        # import each assembly points to scene
        # assembly_points = self.part_info[part_name]["assembly_points"]
        # for idx in assembly_points.keys():
        #     ap = assembly_points[idx]
        #     radius = ap["radius"] / 1000
        #     depth = ap["depth"]
        #     position = ap["pose"]["position"]
        #     quaternion = ap["pose"]["quaternion"]
        #     direction = ap["direction"]
        #     assembly_point = Shape.create(PrimitiveShape.SPHERE,
        #                                   size=[radius]*3,
        #                                   respondable=False,
        #                                   static=True,
        #                                   )
        #     pose = position + quaternion         
        #     assembly_point.set_pose(pose)
        #     assembly_point.set_name(part_name + "_asm_point_" + str(idx))
        #     assembly_point.set_parent(part_base)
        region_info = self.part_info[part_name]["region_info"]
        region_dummys = {}
        for region_id in region_info.keys():
            position = region_info[region_id]["position"]
            region_dummy = Dummy.create()
            region_dummy.set_name("{}_region_{}".format(part_name, region_id))
            region_dummy.set_parent(part_base)
            region_dummy.set_position(position, relative_to=part_base)
            region_dummys[region_id] = region_dummy
        self.part_bases[part_name] = {
            "base": part_base,
            "region": region_dummys
        }
    
    def update_group_to_scene(self):
        self.group_info = {}
        self.logger.info("ready to update group to scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.group_info = request["group_info"]
        self.logger.info("...updating group to scene")
        
        for group_id in self.group_info.keys():
            self._update_group_obj(group_id)
        self.logger.info("End to initialize pyrep scene")
        sendall_pickle(self.connected_client, True)
    
    def _update_group_obj(self, group_id):
        assert self.group_info
        if group_id in self.group_obj.keys():
            self.group_obj[group_id].remove()
        
        group_info = self.group_info[group_id]
        obj_root = group_info["obj_root"]
        file_list = get_file_list(obj_root)
        base_obj = None
        composed_parts = {}
        for file_path in file_list:
            obj_name, ext = get_file_name(file_path)
            if not ext == ".obj":
                continue

            if obj_name == "base": # import base object
                base_obj = ObjObject.create_object(file_path)
                base_obj.set_name("group_{}".format(group_id))
            else: # ikea_stefan_bottom_0
                instance_id = obj_name.split("_")[-1]
                part_name = obj_name.replace("_{}".format(instance_id), "")
                part_instance = {
                    "part_name": part_name,
                    "instance_id": instance_id
                }
                obj = ObjObject.create_object(file_path)
                obj.set_name("group_{}_{}_{}".format(group_id, part_name, instance_id))
                composed_parts[part_instance] = obj
        assert base_obj, "No base object"
        for part_instance in composed_parts.keys():
            obj = composed_parts[part_instance]
            obj.set_parent(base_obj.shape)
        self.group_obj[group_id] = GroupObj(base_obj, composed_parts)

    def get_region_id(self):
        self.logger.info("ready to get group region from scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        group_id = request["group_id"]
        region_loc = request["connection_loc"]
        #TODO:
        self.logger.info("...get group region from scene")
        target_group = self.group_obj[group_id]
        target_group.get_region_id(region_loc, self.part_bases)
        """
        get group object using "group_id"
        get nearest region id from "region_loc"
        """
        self.logger.info("End to get group region from pyrep scene")
        
        region_id = 0
        while True:
            self.pr.step()
        sendall_pickle(self.connected_client, region_id)

    #endregion
    
    
if __name__ == "__main__":
    logger = get_logger("PyRep_Module")
    pyrep_module = PyRepModule(logger)
    pyrep_module.initialize_server()
    while True:
        try:
            request = recvall_pickle(pyrep_module.connected_client)
            logger.info("Get request to {}".format(request))
            callback = pyrep_module.get_callback(request)
            callback()
        except Exception as e:
            logger.info("Error occur {}".format(e))
            break
    pyrep_module.close()    
    


    
    
    