# Assembly Simulation
assembly using freecad
# Assembly Process
## 1. Extract Assembly Point from CAD Files(*.STEP)
## 2. Use A2Plus Workbench to assemble 2 Part
## 3. Extract Assembly Sequence

# Data Structure
```sh
├─FCDocument: FreeCAD Document for each part
|   flat_head_screw_iso.FCStd
|   ikea_l_bracket.FCStd
|   ikea_stefan_bottom.FCStd
|   ikea_stefan_long.FCStd
|   ...
|
├─furniture_info
|   STEFAN.yaml
|   ...
|
├─part_info
|   ├─STEFAN_part_info
|   |   flat_head_screw_iso_0.yaml
|   |   flat_head_screw_iso_1.yaml
|   |   flat_head_screw_iso_2.yaml
|   |   ...
│   └─FURNITURE_NAME_part_info
|      
├─step_file
|   ├─STEFAN
|   |   flat_head_screw_iso(6ea).STEP
|   |   ikea_l_bracket(4ea).STEP
|   |   ikea_stefan_bottom.STEP
|   |   ...


```