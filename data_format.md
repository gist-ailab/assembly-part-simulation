# Instruction_info.yaml
```yaml
sequence: 1 # instruction step
file_name: stefan-chair__AA-21977-9_pub_1.png # instruction file
group_info: assembly/STEFAN/group_info/group_info_0.yaml # matched group_info path
Group: # groups in instruction image
  - group_id: 1 # group id matched with group_info
    instance_id: 0 # 
    connector: # used connector
    pose: # pose
      X: -1
      Y: 1
      Z: 1
      roll: 0
      yaw: 0
      pitch: 0
  - ...
connector_info: assembly/STEFAN/connector_info.yaml # connector info file path
Connector: # used connector
  - model_name: chair pin(14ea).obj # model?
    connector_id: 1 # connector id(match with connector info)
    number_of_connector: 4 # num of used connector
Connection: # connection info
  total_num_connect: 4 # num of connection in instruction step
  connections: 
    - connection_id: 0 # connection id
      num_component: 2 # num of component(group or connector)
      components: 
        - type: group          
          id: 1                    
          instance_id: 0           
          order: 1                
          connect_point:
            X: -1
            Y: 10
            Z: 1
        - type: connector       
          id: 1                 
          instance_id:           
          order: 0                
          connect_point: 
    - ...
```

# Part_info.yaml
```yaml
ikea_stefan_long: # part name
  assembly_points: #assembly point(dict) list
  - depth: 0.022999999999999972 # depth of hole
    direction: # direction of z axis
    - -1.0
    - 0.0
    - 0.0
    edge_index: # matched hole edge in shape file(.STEP)
    - 2
    - aligned # direction
    id: 0 # hole id
    pose: # hole pose related to STEP file coordinate
      position:
      - 0.17
      - 0.016
      - 0.010000000000000002
      quaternion:
      - 0.0
      - 0.7071067811865475
      - 0.0
      - 0.7071067811865475
    radius: 4.0 # radius of hole
    type: hole # type of hole
  document: ./assembly/STEFAN/part_documents/ikea_stefan_long.FCStd # document file path
  part_id: 5 # part id
  step_file: ./cad_file/STEFAN/furniture_part/ikea_stefan_long.STEP # step file path
  type: furniture_part # part type(connector / furniture)
```

# part_instance_info.yaml
```yaml
# 현재 파트별 인스턴스의 결합 상태 확인
ikea_stefan_long: # part name
  0: # instance id
    used_assembly_points: # 조립 후보 추출 시 사용(사용된 포인트는 후보 제외)
      - 0
      - 2
    instance_group_id: 0 # 0 is primitive group
```
# instance_group_info.yaml
```yaml
# 그룹 별 상태
0: [] # primitive
1:
- 0:
    part_name:
    instance_id:
    assembly_point:
  1:
    part_name:
    instance_id:
    assembly_point:
- 0:
  1:
2:
```
# assembly_info
```python
# used when check assembly possibility => FreeCAD Module
assembly_info = {
    0: {
        "part_name": part_0,  # part info의 key(=part name)
        "instance_id": instance_id_0,
        "assembly_point": point_idx_0,
        "status": status_0
    },
    1: {
        "part_name": part_1,
        "instance_id": instance_id_1,
        "assembly_point": point_idx_1,
        "status": status_1
    }
}
```
# Group_info.yaml
```yaml
0: # group_id(name)
  composed_part: [] # compose group ids
  group_id: 0 # group_id(필요한 건지) #TODO
  obj_file: assembly/STEFAN/group_obj/group_0/base.obj # group obj file path
  obj_root: assembly/STEFAN/group_obj/group_0 # group obj root folder
  part_name: ikea_stefan_bottom # if group obj is primitive part then has part name
  instance: [] # matched with group instance
```
# Group_obj
```shell
assembly/STEFAN//group_obj
├── group_0 # group + str(group_id)
│   └── base.obj # group .obj file
...
├── group_n
│   ├── base.obj # group .obj file(composed by primitive group 0, 1, 2)
│   ├── group_0.obj # composed part
│   ├── group_1.obj # composed part
│   └── group_2.obj # composed part
...
```
# Group_instance_info.yaml
```yaml
0: # group id(matched with group_info)
  instance_id: 0
  obj_file: assembly/STEFAN/group_obj/group_1/base.obj
  connector:
    ikea_l_bracket(4ea): 2 # 결합이 가능한 connector들(설명서 이미지 상 인식이 가능한 connector)
  assembly: # group 조립과정 :: assembly point들간의 결합으로 표기
            # 어떤 furniture part의 assembly point들끼리 결합했는지
4:
  group_id: 0
  obj_file: assembly/STEFAN/group_obj/group_7/base.obj
  connector:
    ikea_l_bracket(4ea): 2
  assembly:
    - 
      - right_0_4
      - short_0_5
    -
      - right_0_6
      - short_0_5
```
