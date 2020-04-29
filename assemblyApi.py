import import_fcstd
import FreeCADGui

import Part
import a2plib
import os
from os import listdir
import os.path
from os.path import join, isfile, isdir

# file path
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
STATUS_PATH = join(CURRENT_PATH, "assemble_status")



