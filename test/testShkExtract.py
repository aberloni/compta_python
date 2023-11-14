import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import configs

import library.system

path = library.system.getExtractShkPath(configs.pathDatabase+"bills.lnk")

print(path)