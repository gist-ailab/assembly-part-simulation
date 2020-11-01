# Instruction_info.yaml

```yaml
sequence: 1 # instruction step
file_name: stefan-chair__AA-21977-9_pub_1.png # instruction file
group_info: assembly/STEFAN/group_info/group_info_0.yaml # matched group_info path
Group: # groups in instruction image
  - group_id: 1 # group id matched with group_info
    instance_id : 0 # 
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
  total_num_connect : 4 # num of connection in instruction step
  connections: 
    - connection_id : 0 # connection id
      num_component : 2 # num of component(group or connector)
      components : 
        - type : group          
          id : 1                    
          instance_id : 0           
          order : 1                
          connect_point :
            X: -1
            Y: 10
            Z: 1
        - type : connector       
          id : 1                 
          instance_id :           
          order : 0                
          connect_point : 
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
...