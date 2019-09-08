#!/usr/bin/env python3
from __future__ import print_function

import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
verbose = '-v' in sys.argv
excludes = ('.git', '.svn', '__pycache__')

for dirpath, dirnames, filenames in os.walk(root):
    for exclude in excludes:
        try:
            dirnames.remove(exclude)
        except ValueError:
            pass
    for filename in filenames:
        if filename.endswith('.pyc') or filename.endswith('pyo'):
            if not os.path.exists(os.path.join(dirpath, filename[:-1])):
                os.unlink(os.path.join(dirpath, filename))
                if verbose:
                    print(os.path.join(dirpath, filename))
