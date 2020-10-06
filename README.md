# Assembly Simulation
assembly using freecad

# Assembly Process
## 1. Extract Assembly Point from CAD Files(*.STEP)
## 2. Use A2Plus Workbench to assemble 2 Part
## 3. Extract Assembly Sequence

# 주된 폴더 정리
```sh
assembly # 조립 과정에서 생성 혹은 사용되는 모든 파일
└── STEFAN
    ├── connector_info.yaml # 커넥터 개수 정보를 담고 있음
    ├── freecad_documents # freecad document로 조립시 사용됨
    │   ├── flat_head_screw_iso(6ea).FCStd
    │   ├── ikea_l_bracket(4ea).FCStd
    │   ├── ikea_stefan_bottom.FCStd
    │   ├── ikea_stefan_long.FCStd
    │   ├── ikea_stefan_middle.FCStd
    │   ├── ikea_stefan_short.FCStd
    │   ├── ikea_stefan_side_left.FCStd
    │   ├── ikea_stefan_side_right.FCStd
    │   ├── ikea_wood_pin(14ea).FCStd
    │   └── pan_head_screw_iso(4ea).FCStd
    ├── group_info # 단계별 group 정보
    │   └── group_info_0.yaml
    └── group_obj # 기본 혹은 조립된 부품의 unique obj 파일들
        ├── flat_head_screw_iso(6ea).mtl
        ├── flat_head_screw_iso(6ea).obj
        ├── ikea_l_bracket(4ea).mtl
        ├── ikea_l_bracket(4ea).obj
        ├── ikea_stefan_bottom.mtl
        ├── ikea_stefan_bottom.obj
        ├── ikea_stefan_long.mtl
        ├── ikea_stefan_long.obj
        ├── ikea_stefan_middle.mtl
        ├── ikea_stefan_middle.obj
        ├── ikea_stefan_short.mtl
        ├── ikea_stefan_short.obj
        ├── ikea_stefan_side_left.mtl
        ├── ikea_stefan_side_left.obj
        ├── ikea_stefan_side_right.mtl
        ├── ikea_stefan_side_right.obj
        ├── ikea_wood_pin(14ea).mtl
        ├── ikea_wood_pin(14ea).obj
        ├── pan_head_screw_iso(4ea).mtl
        └── pan_head_screw_iso(4ea).obj
cad_file # 처음 조립 시 받는 캐드 파일(*.STEP)
└── STEFAN
    ├── connector_part
    │   ├── flat_head_screw_iso(6ea).STEP
    │   ├── ikea_l_bracket(4ea).STEP
    │   ├── ikea_wood_pin(14ea).STEP
    │   └── pan_head_screw_iso(4ea).STEP
    ├── furniture_part
    │   ├── ikea_stefan_bottom.STEP
    │   ├── ikea_stefan_long.STEP
    │   ├── ikea_stefan_middle.STEP
    │   ├── ikea_stefan_short.STEP
    │   ├── ikea_stefan_side_left.STEP
    │   └── ikea_stefan_side_right.STEP
    └── part_info.yaml # cad file에 대한 assembly points 정보를 담고 있음
instruction # 설명서에서 생성된 데이터
└── STEFAN
```


# Part assembly
- get instruction information
- 

# assembly status
- each assembly status is Full assemble for parts in instruction step
- initial_status.yaml has all statuses before assemble current instruction step


# setting
- [setuplink](http://ubuntuhandbook.org/index.php/2019/04/install-freecad-0-18-ubuntu-18-04-16-04/)
- when using external python script, add freecad lib to sys.path 
- pip3 install --user numpy scipy matplotlib ipython jupyter pandas sympy nose
## issue for setting
- abort(core dumped)
    - sudo python3 $python file
- module 'yaml' has no attribute 'FullLoader'
    - pip3 install PyYAML
