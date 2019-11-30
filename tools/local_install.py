#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import subprocess
import sys

if '--local-modules' in sys.argv:
    local_modules = True
    sys.argv.remove('--local-modules')
else:
    local_modules = False

print("Weboob local installer")
print()

if len(sys.argv) < 2:
    print("This tool will install Weboob to be usuable without requiring")
    print("messing with your system, which should only be touched by a package manager.")
    print()
    print("Usage: %s DESTINATION" % sys.argv[0])
    print()
    print("Error: Please provide a destination, "
          "for example ‘%s/bin’" % os.getenv('HOME'), file=sys.stderr)
    sys.exit(1)
else:
    dest = os.path.expanduser(sys.argv[1])

print("Installing weboob applications into ‘%s’." % dest)


if local_modules:
    sourceslist = os.path.join(
        os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')),
        'weboob', 'sources.list')
    if not os.path.isdir(os.path.dirname(sourceslist)):
        os.makedirs(os.path.dirname(sourceslist))
    if not os.path.exists(sourceslist):
        with open(sourceslist, 'w') as f:
            f.write('file://' + os.path.realpath(
                os.path.join(os.path.dirname(__file__), os.pardir, 'modules')
            ))

subprocess.check_call(
    [sys.executable, 'setup.py',
        'install', '--user', '--install-scripts=%s' % dest] + sys.argv[2:],
    cwd=os.path.join(os.path.dirname(__file__), os.pardir))

subprocess.call([sys.executable, os.path.join(dest, 'weboob-config'), 'update'])

print()
print("Installation done. Applications are available in ‘%s’." % dest)
print("You can remove the source files.")
print()
print("To have easy access to the Weboob applications,")
print("you should add the following line to your ~/.bashrc or ~/.zshrc file:")
print("export PATH=\"$PATH:%s\"" % dest)
print("And then restart your shells.")
