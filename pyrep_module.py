from os.path import join, splitext
import socket, threading
import time
from numpy.core.fromnumeric import prod

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape
from pyrep.objects.camera import Camera

from script.fileApi import *
from script.const import SocketType, PyRepRequestType
from script.socket_utils import *
from itertools import combinations, permutations, product

import numpy as np
import copy

#TODO
ASSEMBLY_PAIR = None
def get_available_points(part_name, instance_id, connector_name, part_status=None):
    assert ASSEMBLY_PAIR
    available_points = []
    point_pair_info = ASSEMBLY_PAIR[part_name]
    for point_idx in point_pair_info.keys():
        pair_list = point_pair_info[point_idx]
        for pair_info in pair_list:
            if pair_info["part_name"] == connector_name:
                available_points.append(point_idx)
    available_points = set(available_points)
    # 3.2.2 remove used points
    if part_status:
        part_intance_status = part_status[part_name][instance_id]
        used_point = part_intance_status["used_assembly_points"].keys()
        available_points = available_points - set(used_point)

    return list(available_points)

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
    def get_pose(self, relative_to=None):
        return self.shape.get_pose(relative_to=relative_to)
    
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
        self.instruction_frame.set_name("{}_manual".format(name))

    def remove(self):
        self.shape.remove()
        self.frame.remove()
        self.instruction_frame.remove()

class GroupObject():
    def __init__(self, base_obj: ObjObject, composed_parts, composed_objects):
        """Group
        Args:
            base_obj (ObjObject): [description]
            composed_parts: tuple of part_instance(dict)
                part_instance = {
                    "part_name": part name(string)
                    "instance_id: id(int)
                }
            composed_objects: tuple of composed object(dict)
                composed_object = {
                    "group_object": ObjObject
                    "primitive": PartObject
                }
            }
        """
        self.base_obj = base_obj
        self.composed_parts = composed_parts
        self.composed_objects = composed_objects

    def get_assembly_points(self, locations, connector_name, part_status):
        target_assembly_points = {idx: None for idx in range(len(locations))}
        # 1. import connection locs to scene
        """
        connection_points = tuple of Connection_point(Dummy)
            => idx is same as locations
        """
        connection_points = self._create_connection_points(locations)
        # 2. get available region and points in group
        """
        - used connector name to available region, points
        - remove used points and regions
        - get region, points_list for each parts
        
        available_region = tuple of region_info
            region_info = {
                "part_id": part_idx(matched with self.composed_parts)
                "shape": Shape
                "points": [] (list of available_points)
            }
            ...
        """
        available_regions = self._get_available_regions(connector_name, part_status)
        #region 3. search best region to use
        """
        - use distance cost to decide best region for each connection point
            - move each primitive(which parent of region shape) to group composed parts
            - calculate distance
        - consider each regions' available point num
        """
        connection_2_region_cost = np.zeros((len(connection_points), len(available_regions)))
        for connection_idx, connection_dummy in enumerate(connection_points):
            target_position = np.array(connection_dummy.get_position())
            
            for region_idx, region_info in enumerate(available_regions):
                part_idx = region_info["part_id"]
                object_info = self.composed_objects[part_idx]
                group_object = object_info["group_object"]
                primitive_object = object_info["primitive"]
                composed_part_pose = self.composed_parts[part_idx]["pose"]
                primitive_object.set_pose(composed_part_pose, relative_to=self.base_obj.frame)
                primitive_object.object.set_parent(self.base_obj.shape)
                region_shape = region_info["shape"]
                region_position = np.array(region_shape.get_position())
                distance = np.linalg.norm(target_position - region_position)
                
                connection_2_region_cost[connection_idx][region_idx] = distance
        
        connection_idx_list = range(len(connection_points))
        region_idx_list = range(len(available_regions))
        all_possible_matching = product(region_idx_list, repeat=len(connection_points))
        
        min_cost = np.inf
        connection_2_region = None
        for candidate in all_possible_matching:
            cost = 0
            for connection_idx, region_idx in zip(connection_idx_list, candidate):
                cost += connection_2_region_cost[connection_idx, region_idx]

            if cost < min_cost:
                is_possible = True
                candidate = np.array(candidate)
                unique_region_idx = np.unique(candidate)
                for unique_region in unique_region_idx:
                    candidate_num = np.count_nonzero(candidate == unique_region)
                    available_num = len(available_regions[unique_region]["points"])
                    if candidate_num > available_num:
                        is_possible = False
                        break
                if is_possible:
                    min_cost = cost
                    connection_2_region = candidate

        assert len(connection_2_region) > 0, "Fail to search region for connections"
        #endregion

        #region 4. calculate cost for each used region
        # 4.1 region_2_connection_list
        used_region = np.unique(np.array(connection_2_region))
        region_2_connection = {region_idx: [] for region_idx in used_region}
        for connection_idx, region_idx in enumerate(connection_2_region):
            connection_dummy = connection_points[connection_idx]
            region_2_connection[region_idx].append(connection_idx)

        connection_2_point = {connection_idx: {} for connection_idx in range(len(connection_points))}
        # 4.2 searching points matching for each region
        for region_idx in region_2_connection.keys():
            region_info = available_regions[region_idx]
            connection_idx_list = region_2_connection[region_idx]    
            part_id = region_info["part_id"]
            available_points_idx_list = region_info["points"]
            candidate_point_matching_list = permutations(available_points_idx_list, len(connection_idx_list))

            connection_2_point_cost = {connection_idx: {} for connection_idx in connection_idx_list}

            for candidate_point_matching in candidate_point_matching_list:
                
                for connection_idx, point_idx in zip(connection_idx_list, candidate_point_matching):
                    connection_dummy = connection_points[connection_idx]
                    connection_position = np.array(connection_dummy.get_position())
                    
                    primitive_object = self.composed_objects[part_id]["primitive"]
                    target_point = primitive_object.assembly_points[point_idx]
                    target_position = np.array(target_point.get_position())

                    cost = np.linalg.norm(connection_position - target_position)
                    connection_2_point_cost[connection_idx][point_idx] = float(cost)
                
            for connection_idx in connection_idx_list:
                part_info = self.composed_parts[part_id]
                connection_2_point[connection_idx] = {
                    "part_name": part_info["part_name"],
                    "instance_id": part_info["instance_id"],
                    "region_id": region_idx,
                    "point_cost": connection_2_point_cost[connection_idx]
                }
            print(connection_2_point_cost)
        target_assembly_points = copy.deepcopy(connection_2_point)                

        return target_assembly_points

    def _create_connection_points(self, connection_locations):
        connection_points = []
        for idx, location in enumerate(connection_locations):
            connection_point = Dummy.create()
            rand = float(np.random.rand())
            dummy_name = "connection_point_{0:04f}_".format(rand).replace(".", "")
            dummy_name += str(idx)
            connection_point.set_name(dummy_name)
            # relative to bounding box center
            #TODO: connection frame
            connection_point.set_position(location, relative_to=self.base_obj.frame)
            connection_point.set_parent(self.base_obj.frame)
            connection_points.append(connection_point)
        
        return tuple(connection_points)
    def _get_available_regions(self, connector_name, part_status):
        available_regions = []
        for part_idx , object_dict in enumerate(self.composed_objects):
            part_name = self.composed_parts[part_idx]["part_name"]
            instance_id = self.composed_parts[part_idx]["instance_id"]
            available_points = set(get_available_points(part_name, instance_id, connector_name, part_status))

            primitive_object = object_dict["primitive"]
            region_info = primitive_object.region_info
            for region_id in region_info.keys():
                region_points = set(region_info[region_id]["points"])
                region_available_points = list(region_points.intersection(available_points))
                if not len(available_points) > 0:
                    continue
                region_shape = region_info[region_id]["shape"]
                available_regions.append({
                    "part_id": part_idx,
                    "shape": region_shape,
                    "points": region_available_points
                })

        return tuple(available_regions)
    
    def remove(self):
        self.base_obj.remove()
        self.composed_parts = None
        for composed_object in self.composed_objects:
            composed_object["group_object"].remove()
        self.composed_objects = None

class PartObject():
    def __init__(self, part_object: Shape, assembly_points, region_info):
        """[summary]

        Args:
            part_object (Shape): [description]
            assembly_points (dict of Dummy): [description]
            regions (dict of Dummy): [description]
        """
        self.object = part_object
        self.assembly_points = assembly_points        
        self.region_info = region_info

    def set_pose(self, pose, relative_to=None):
        self.object.set_pose(pose, relative_to=relative_to)

class PyRepModule(object):
    def __init__(self, logger, headless=False):
        self.logger = logger
        self.callback = {
            PyRepRequestType.initialize_part_to_scene: self.initialize_part_to_scene,
            PyRepRequestType.update_group_to_scene: self.update_group_to_scene,
            PyRepRequestType.get_assembly_point: self.get_assembly_point,
            PyRepRequestType.update_part_status: self.update_part_status
        }
        self.pr = PyRep()
        self.pr.launch(headless=headless)
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
        global ASSEMBLY_PAIR
        self.logger.info("ready to initialize part to scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.part_info = request["part_info"]
        ASSEMBLY_PAIR = request["pair_info"]
        self.logger.info("...initializing pyrep scene")
        for part_name in self.part_info.keys():
            self._import_part_info(part_name)
        self.logger.info("End to initialize pyrep scene")
        sendall_pickle(self.connected_client, True)

    def _import_part_info(self, part_name):
        assert self.part_info
        self.logger.info("import part info of {}".format(part_name))
        obj_path = self.part_info[part_name]["obj_file"]
        # part_obj = Shape.import_mesh(obj_path, scaling_factor=0.001)
        part_obj = ObjObject.create_object(obj_path=obj_path)
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
            assembly_point.set_parent(part_obj.shape)
            points[idx] = assembly_point
        part_region_info = self.part_info[part_name]["region_info"]
        region_info = {}
        for region_id in part_region_info.keys():
            position = part_region_info[region_id]["position"]
            point_list = part_region_info[region_id]["points"]
            region_shape = Shape.create(PrimitiveShape.SPHERE,
                                        size=[0.05]*3,
                                        respondable=False,
                                        static=True,
                                        color=[0,1,0]
                                        )
            region_shape.set_name("{}_region_{}".format(part_name, region_id))
            region_shape.set_parent(part_obj.shape)
            region_shape.set_position(position)
            for point_idx in point_list:
                points[point_idx].set_parent(region_shape)
            region_info[region_id] = {
                "shape": region_shape,
                "points": point_list
            }
        self.primitive_parts[part_name] = PartObject(part_object=part_obj,
                                                    assembly_points=points,
                                                    region_info=region_info)
        
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
            composed_objects = []
            composed_part_idx = 0
            group_pose = load_yaml_to_dic(join(obj_root, "group_pose.yaml"))
            for file_path in file_list:
                obj_name, ext = get_file_name(file_path)
                if not ext == ".obj":
                    continue
                if obj_name == "base": # import base object
                    base_obj = ObjObject.create_object(file_path)
                    base_obj.set_name("G{}".format(group_id))
                else: # ikea_stefan_bottom_0
                    instance_id = obj_name.split("_")[-1]
                    part_name = obj_name.replace("_{}".format(instance_id), "")
                    obj = ObjObject.create_object(file_path)
                    obj.set_name("G{}_{}_{}".format(group_id, part_name, instance_id))
                    part_instance = {
                        "part_name": part_name,
                        "instance_id": int(instance_id),
                        "pose": group_pose[obj_name]
                    }
                    composed_parts.append(part_instance)
                    object_dict = {
                        "group_object": obj,
                        "primitive": self.primitive_parts[part_name]
                    }
                    composed_objects.append(object_dict)
                    composed_part_idx += 1
            assert base_obj, "No base object"
            composed_parts = tuple(composed_parts)
            composed_objects = tuple(composed_objects)
            for object_dict in composed_objects:
                obj = object_dict["group_object"]
                obj.set_parent(base_obj.shape)
            self.group_obj[group_id] = GroupObject(base_obj, composed_parts, composed_objects)

    def update_part_status(self):
        self.logger.info("ready to update part_status")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        self.part_status = request["part_status"]
        self.logger.info("Update part_status")
        sendall_pickle(self.connected_client, True)
        #TODO: delete assembly point

    def get_assembly_point(self):
        self.logger.info("ready to get assembly point from scene")
        sendall_pickle(self.connected_client, True)
        request = recvall_pickle(self.connected_client)
        group_id = int(request["group_id"])
        connection_locs = request["connection_locs"]
        connector_name = request["connector_name"]
        #TODO:
        self.logger.info("...get assembly points of group {} from scene".format(group_id))
        target_group = self.group_obj[group_id]
        assembly_points = None        
        try:
            assembly_points = target_group.get_assembly_points(locations=connection_locs, 
                                                            connector_name=connector_name, 
                                                            part_status=self.part_status)
            
        except Exception as e:
            self.logger.info("Error occur {}".format(e))
            self.save_scene("test_error_scene/error_scene_{}.ttt".format(get_time_stamp()))    
        self.logger.info("End to get assembly point from pyrep scene")
        sendall_pickle(self.connected_client, assembly_points)
        self.save_scene("test_scene/test_scene_{}.ttt".format(get_time_stamp()))
    #endregion
    
if __name__ == "__main__":
    logger = get_logger("PyRep_Module")
    pyrep_module = PyRepModule(logger, headless=True)
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
    


    
    
    