from os.path import join, splitext
import socket, threading
import time

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape
from pyrep.objects.camera import Camera

from script.fileApi import *
from script.const import SocketType, PyRepRequestType
from script.socket_utils import *


class ObjObject():
    def __init__(self, obj: Shape, frame: Dummy, instruction_frame: Dummy):
        self.shape = obj
        self.frame = frame
        self.instruction_frame = instruction_frame
        
    @staticmethod
    def create_object(obj_path, scaling_factor=0.001):
        obj_name, ext = get_file_name(obj_path)
        if not ext == ".obj":
            print("[ERROR] please check obj file {}".format(obj_path))
            exit()
        obj = Shape.import_mesh(obj_path, scaling_factor=scaling_factor)
        frame = Dummy.create()
        frame.set_parent(obj)
        instruction_frame = Dummy.create()
        instruction_frame.set_position([0,0,0], relative_to=obj)
        instruction_frame.set_parent(obj)
        
        return ObjObject(obj, frame, instruction_frame)

    #region transform -> self.frame
    def get_pose(self, relative_to):
        self.shape.get_pose(relative_to=relative_to)    
    
    def set_pose(self, pose, relative_to=None):
        assert False, "Not Implemented"
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
        self.instruction_frame.set_name("{}_manual".format(name))

    def remove(self):
        self.shape.remove()
        self.frame.remove()
        self.instruction_frame.remove()

class GroupObject():
    def __init__(self, base_obj: ObjObject, composed_parts):
        """Group

        Args:
            base_obj (ObjObject): [description]
            composed_parts: (list of composed_part)
                composed_part = {
                "part_name": string
                "instance_id: int
                "object": ObjObject
                }
        """
        self.base_obj = base_obj
        self.composed_parts = composed_parts 

    def get_region_id(self, location, primitive_parts):
        assert primitive_parts
        target_region_id = None
        min_distance = np.inf
        temp_dummy = Dummy.create()
        # relative to bounding box center
        temp_dummy.set_position(location, relative_to=self.base_obj.instruction_frame)
        connection_pos = np.array(temp_dummy.get_position())
        for composed_part in self.composed_parts:
            composed_part_name = composed_part["part_name"]
            instance_id = composed_part["instance_id"]
            composed_part_object = composed_part["object"]

            primitive_part_object = primitive_parts[composed_part_name]["object"]
            points = primitive_parts[composed_part_name]["points"]
            regions = primitive_parts[composed_part_name]["regions"]
            primitive_part_object.set_pose(composed_part_object.shape.get_pose())

            for region_id in regions.keys():
                region_dummy = regions[region_id]
                pos = np.array(region_dummy.get_position())
                distance = np.linalg.norm(connection_pos - pos)
                if distance < min_distance:
                    min_distance = distance
                    target_region_id = region_id
        
        temp_dummy.remove()

        return target_region_id
            
    def get_assembly_point(self,location, primitive_parts, part_status):
        assert primitive_parts
        target_assembly_point = {
            "part_name": None,
            "instance_id": None,
            "assembly_point": None,
        }
        min_distance = np.inf
        temp_dummy = Dummy.create()
        temp_dummy.set_name("connection_loc")
        # relative to bounding box center
        temp_dummy.set_position(location, relative_to=self.base_obj.instruction_frame)
        connection_pos = np.array(temp_dummy.get_position())
        for composed_part in self.composed_parts:
            composed_part_name = composed_part["part_name"]
            instance_id = composed_part["instance_id"]
            composed_part_object = composed_part["object"]

            primitive_part_object = primitive_parts[composed_part_name]["object"]
            points = primitive_parts[composed_part_name]["points"]
            regions = primitive_parts[composed_part_name]["regions"]
            
            primitive_part_object.set_pose(composed_part_object.get_pose())

            available_points = points.keys()
            #TODO: used point
            used_point = part_status[composed_part_name][instance_id]["used_assembly_points"].keys()

            available_points = list(set(available_points) - set(used_point))

            for point_id in available_points:
                point_dummy = points[point_id]
                
                pos = np.array(point_dummy.get_position())
                distance = np.linalg.norm(connection_pos - pos)
                if distance < min_distance:
                    min_distance = distance
                    target_assembly_point = {
                        "part_name": composed_part_name,
                        "instance_id": instance_id,
                        "point_id": point_id,
                    }
        temp_dummy.remove()

        return target_assembly_point

    def remove(self):
        self.base_obj.remove()
        for composed_part in self.composed_parts:
            composed_part["object"].remove()
        self.composed_parts = []

class PyRepModule(object):
    def __init__(self, logger, headless=False):
        self.logger = logger
        self.callback = {
            PyRepRequestType.initialize_part_to_scene: self.initialize_part_to_scene,
            PyRepRequestType.update_group_to_scene: self.update_group_to_scene,
            PyRepRequestType.get_region_id: self.get_region_id,
            PyRepRequestType.get_assembly_point: self.get_assembly_point,
            PyRepRequestType.update_part_status: self.update_part_status
        }
        self.pr = PyRep()
        self.pr.launch("scene/demo.ttt", headless=headless)
        self.pr.start()
        # self.scene_th = threading.Thread(target=self.scene_binding)
        # self.scene_th.start()
        
        # used to visualize and assembly
        self.part_info = None
        self.part_status = None
        self.primitive_parts = {}
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
                time.sleep(0.1)
                print("threading step")
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
        obj_path = self.part_info[part_name]["obj_file"]
        part_obj = Shape.import_mesh(obj_path, scaling_factor=0.001)
        part_obj.set_name(part_name)
        # import each assembly points to scene
        assembly_points = self.part_info[part_name]["assembly_points"]
        points = {}
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
                                        color=[1,0,0]
                                        )
            pose = position + quaternion         
            assembly_point.set_pose(pose)
            assembly_point.set_name("{}_AP_{}".format(part_name, idx))
            assembly_point.set_parent(part_obj)
            points[idx] = assembly_point
        region_info = self.part_info[part_name]["region_info"]
        region_dummys = {}
        for region_id in region_info.keys():
            position = region_info[region_id]["position"]
            region_dummy = Dummy.create()
            region_dummy.set_name("{}_region_{}".format(part_name, region_id))
            region_dummy.set_parent(part_obj)
            region_dummy.set_position(position)
            region_dummys[region_id] = region_dummy
        self.primitive_parts[part_name] = {
            "object": part_obj,
            "points": points,
            "regions": region_dummys
        }
    
    def update_group_to_scene(self):
        self.logger.info("ready to update group to scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        new_group_info = request["group_info"]
        self.logger.info("...updating group to scene")
        self._update_group_obj(new_group_info)
        self.logger.info("End to update group to scene")
        sendall_pickle(self.connected_client, True)

    def _update_group_obj(self, new_group_info):
        for group_id in self.group_obj.keys():
            self.group_obj[group_id].remove()
        self.group_obj = {}
        for group_id in new_group_info.keys():
            if not new_group_info[group_id]["is_exist"]:
                continue
            self.logger.info("update group_{} to scene".format(group_id))
            group_info = new_group_info[group_id]
            obj_root = group_info["obj_root"]
            file_list = get_file_list(obj_root)
            base_obj = None
            composed_parts = []
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
                    obj = ObjObject.create_object(file_path)
                    obj.set_name("G{}_{}_{}".format(group_id, part_name, instance_id))
                    composed_part = {
                        "part_name": part_name,
                        "instance_id": instance_id,
                        "object": obj
                    }
                    composed_parts.append(composed_part)
            assert base_obj, "No base object"
            for composed_part in composed_parts:
                obj = composed_part["object"]
                obj.set_parent(base_obj.shape)
            self.group_obj[group_id] = GroupObject(base_obj, composed_parts)

    def update_part_status(self):
        self.logger.info("ready to update part_status")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.part_status = request["part_status"]
        self.logger.info("Update part_status")
        sendall_pickle(self.connected_client, True)
        #TODO: delete assembly point

    def get_region_id(self):
        exit()
        self.logger.info("ready to get group region from scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        group_id = request["group_id"]
        region_loc = request["connection_loc"]
        #TODO:
        self.logger.info("...get group region from scene")
        target_group = self.group_obj[group_id]
        target_group.get_region_id(region_loc, self.primitive_parts)
        """
        get group object using "group_id"
        get nearest region id from "region_loc"
        """
        self.logger.info("End to get group region from pyrep scene")
        
        region_id = 0

        sendall_pickle(self.connected_client, region_id)

    def get_assembly_point(self):
        self.logger.info("ready to get assembly point from scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        group_id = request["group_id"]
        connection_loc = request["connection_loc"]
        #TODO:
        self.logger.info("...get assembly point from scene")
        target_group = self.group_obj[group_id]
        assembly_point = target_group.get_assembly_point(connection_loc, self.primitive_parts, self.part_status)
        
        self.logger.info("End to get assembly point from pyrep scene")
        
        sendall_pickle(self.connected_client, assembly_point)
    
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
    


    
    
    