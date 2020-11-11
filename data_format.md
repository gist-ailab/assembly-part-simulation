# part_info.yaml
- extract from cad file
- not refined => 매번 다시 뽑아도 됨
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
# assembly_pair.yaml
- part info 를 기반으로 생성된 결합 가능 쌍
- part 의 결합 지점마다 가능한 모든 결합 쌍을 저장
- 방향 및 offset 정보를 결합이 잘 될 수 있도록 수정한 상태(=> 저장된 파일을 불러서 사용)
```yaml
ikea_stefan_bolt_side: # part name (matching with part_info)
  0: # assembly point id
  - assembly_point: 0
    direction: opposed
    offset: 0
    part_name: ikea_stefan_side_left
  - assembly_point: 3
    direction: opposed
    offset: 0
    part_name: ikea_stefan_side_left
  - assembly_point: 4
    direction: opposed
    offset: 0
    part_name: ikea_stefan_side_left
  - assembly_point: 0
    direction: aligned
    offset: 0
    part_name: ikea_stefan_side_right
  - assembly_point: 3
    direction: aligned
    offset: 0
    part_name: ikea_stefan_side_right
  - assembly_point: 4
    direction: aligned
    offset: 0
    part_name: ikea_stefan_side_right
...
```
# part_instance_status.yaml
- furniture / connector 파트의 인스턴스 정보
- 가구 부품은 1개 씩 존재함
- 미리 개수를 안다고 가정!
- 각 파트의 결합 부위의 결합 상태를 확인
```yaml
# 현재 파트별 인스턴스의 결합 상태 확인
ikea_stefan_long: # part name
  0: # instance id
    used_assembly_points: # 조립 후보 추출 시 사용(사용된 포인트는 후보 제외)
      - 0
      - 2
    # group_id: 0
```

# group_status.yaml
```yaml
# 그룹 별 상태
0:
  composed_part:
  - instance_id: 0
    part_name: ikea_stefan_bottom
  status: []
0:
  composed_part:
  status: # list of assemlby info
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
1:
2:
```
# group_info.yaml
- 설명서에서 사용하는 "group"에 대한 현재 정보
- 가구 부품만을 포함하는 obj 파일을 출력하여 설명서 분석에 제공
- 원래는 group_id 에 따른 instance 를 따로 고려하려 했으나, 실제 미션에서 가구 부품이 최대 1개씩이기 때문에 그룹 instance를 고려하지 않아도 될거 같다.
```yaml
0: # group_id(name)
  composed_group: # MLC 용 이였나 
  - 0
  obj_file: assembly/STEFAN/group_obj/group_0/base.obj # group obj file path
  obj_root: assembly/STEFAN/group_obj/group_0 # group obj root folder
```
# group_obj file
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

# assembly_info
```python
# used when check assembly possibility => FreeCAD Module
assembly_info = {
  "target":{
      0: {
          "part_name": part_0,  # part info의 key(=part name)
          "instance_id": instance_id_0,
          "assembly_point": point_idx_0,
      },
      1: {
          "part_name": part_1,
          "instance_id": instance_id_1,
          "assembly_point": point_idx_1,
      }
  },
  "status": status
}
```

