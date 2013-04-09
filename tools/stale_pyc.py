#!/usr/bin/env python
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
verbose = '-v' in sys.argv
for dirpath, dirnames, filenames in os.walk(root):
    for filename in filenames:
        if filename.endswith('.pyc') or filename.endswith('pyo'):
            if not os.path.exists(os.path.join(dirpath, filename[:-1])):
                os.unlink(os.path.join(dirpath, filename))
                if verbose:
                    print os.path.join(dirpath, filename)
