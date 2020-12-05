# Setting
## Python setting
- all python env > 3.7
```
pip install pickle-compat
```
## FreeCAD setting
1. create environment
- using "environment.yml" to create conda environemt
- env name is "freecad"
- env has FreeCAD and A2Plus Mod...

```shell
conda env create -f environment.yml
conda activate freecad
```

2. run FreeCAD
```shell
conda activate freecad
FreeCAD
```
3. in FreeCAD python console(View->Panels->Pythonconsole)
- copy the sys.path used in FreeCAD
```python
import sys
sys.path
=> list of path
```

4. in script.import_fcstd.py
- paste the FreeCAD sys.path to "ENVPATH" and change the "FREECADPATH"
```python
class ENVPATH:
    raeyo_ubunto = ['/home/raeyo/anaconda3/envs/freecad/Mod/Sketcher'...
    raeyo_win = ['C:/Users/KANG/AppData/Roaming/FreeCAD/Mod/A2plus' ...
    joo = ['C:/Users/joo/anaconda3/envs/py36/Library/Mod/Web' ...
    extra = ["sys.path of FreeCAD python console"]

FREEECADPATH = ENVPATH.raeyo_ubuntu
# FREEECADPATH = ENVPATH.extra
```

## PyRep setting
- https://github.com/stepjam/PyRep

# How to Run
## terminal #1 main.py
```shell
# with all other modules
python main.py --instruction -- visualize -- dyros 

# without other modules
python main.py 
```
## terminal #2 freecad_module.py
```shell
python pyrep_module.py 
```
## pyrep_module.py
```shell
python .py 
```


