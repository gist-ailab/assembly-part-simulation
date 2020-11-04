from os.path import join, splitext
import socket, threading

from pyrep import PyRep
from pyrep.objects.dummy import Dummy
from pyrep.objects.shape import Shape
from pyrep.const import PrimitiveShape

from script.fileApi import *
from script.const import SocketType

    
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

class PyRepModule(object):
    def __init__(self, headless=False):
        self.pr = PyRep()
        self.pr.launch(headless=headless)
        self.pr.start()


        # self._initialize_server()
        # try:
        #     client_socket, addr = self.server_socket.accept()
        #     self.client_th = threading.Thread(target=self.binding, args = (client_socket, addr))
        #     self.client_th.start()
        # except:
        #     print("pyrep server error")
    
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

    def close(self):
        self.server_socket.close()
        self.pr.stop()
        self.pr.shutdown()
    
    def step(self):
        self.pr.step()
    
    def save_scene(self, path):
        self.pr.export_scene(path)

    #region socket
    def _initialize_server(self):
        socket_type = SocketType.pyrep.value
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((socket_type["host"], socket_type["port"]))
        self.server_socket.listen()

    def get_callback(self, request_type: str):
        if request_type == "get_region":
            pass

    @staticmethod
    def binding(client_socket, addr):
        print("Connected by", addr)
        try:
            # 접속 상태에서는 클라이언트로 부터 받을 데이터를 무한 대기한다.
            # 만약 접속이 끊기게 된다면 except가 발생해서 접속이 끊기게 된다.
            while True:
                # socket의 recv함수는 연결된 소켓으로부터 데이터를 받을 대기하는 함수입니다. 최초 4바이트를 대기합니다.
                data = client_socket.recv(4)
                # 최초 4바이트는 전송할 데이터의 크기이다. 그 크기는 little 엔디언으로 byte에서 int형식으로 변환한다.
                length = int.from_bytes(data, "little")
                # 다시 데이터를 수신한다.
                data = client_socket.recv(length)
                # 수신된 데이터를 str형식으로 decode한다.
                request_type = data.decode()

                # 수신된 메시지를 콘솔에 출력한다.
                msg = request_type
                print('Received from', addr, msg)
                # 수신된 메시지 앞에 「echo:」 라는 메시지를 붙힌다.
                msg = "echo : " + msg
                # 바이너리(byte)형식으로 변환한다.
                data = msg.encode()
                # 바이너리의 데이터 사이즈를 구한다.
                length = len(data)
                # 데이터 사이즈를 little 엔디언 형식으로 byte로 변환한 다음 전송한다.
                client_socket.sendall(length.to_bytes(4, byteorder="little"))
                # 데이터를 클라이언트로 전송한다.
                client_socket.sendall(data)
        except:
            # 접속이 끊기면 except가 발생한다.
            print("except : " , addr)
        finally:
        # 접속이 끊기면 socket 리소스를 닫는다.
            client_socket.close()


    def recvall(self, data, length):
        pass
    def sendall(self, data):
        pass
    
    #endregion

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
        


# 1. initialize pyrep scene
# 2. add each group to scene: dict -> json -> pickle
# Instruction_info["Group"]
if __name__ == "__main__":
    pyrep_module = PyRepModule()
    part_info = load_yaml_to_dic("./assembly/STEFAN/part_info.yaml")
    primitive_group_info = load_yaml_to_dic("./assembly/STEFAN/group_info/group_info_0.yaml")

    # initialize each primitive group using part info
    for group_id in primitive_group_info.keys():
        part_name = primitive_group_info[group_id]["part_name"]
        info = part_info[part_name]
        pyrep_module.import_primitive_part(part_name, info)
    


    
    
    