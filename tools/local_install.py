#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import os

print "Weboob local installer"
print
if len(sys.argv) < 2:
    print "This tool will install Weboob to be usuable without requiring"
    print "messing with your system, which should only be touched by a package manager."
    print
    print "Usage: %s DESTINATION" % sys.argv[0]
    print
    print >>sys.stderr, "Error: Please provide a destination, " \
                        "for example ‘%s/bin’" % os.getenv('HOME')
    sys.exit(1)
else:
    dest = os.path.expanduser(sys.argv[1])

print "Installing weboob applications into ‘%s’." % dest
subprocess.check_call(
    [sys.executable, 'setup.py',
        'install', '--user', '--install-scripts', dest] + sys.argv[2:],
    cwd=os.path.join(os.path.dirname(__file__), os.pardir))

subprocess.check_call([sys.executable, os.path.join(dest, 'weboob-config'), 'update'])

print
print "Installation done. Applications are available in ‘%s’." % dest
print "You can remove the source files."
print
print "To have easy access to the Weboob applications,"
print "you should add the following line to your ~/.bashrc or ~/.zshrc file:"
print "export PATH=\"$PATH:%s\"" % dest
print "And then restart your shells."
