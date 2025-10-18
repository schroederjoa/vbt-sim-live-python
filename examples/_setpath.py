# -*- coding: utf-8 -*-

import sys
from pathlib import Path

libpath = Path.cwd()
sys.path.append(str(libpath))

libpath = Path.cwd()
libpath = libpath.parent
sys.path.append(str(libpath))

libpath = Path.cwd()
libpath = libpath.parent
libpath = libpath.joinpath("indicators")
sys.path.append(str(libpath))

libpath = Path.cwd()
libpath = libpath.parent
libpath = libpath.joinpath("vbt_sim_live")
sys.path.append(str(libpath))
