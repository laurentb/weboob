#!/usr/bin/env python

from __future__ import with_statement

import sys

for name in sys.argv[1:]:
    with open(name, 'r') as f:
        lines = f.readlines()

    with open(name, 'w') as f:
        f.write('backends:\n')
        for line in lines:
            f.write('  %s' % line)
