#!/usr/bin/env python
import glob
import subprocess
import os
import sys

def check_executable(executable):
    with open('/dev/null', 'w') as devnull:
        process = subprocess.Popen(['which', executable], stdout=devnull)
        return_code = process.wait()
    if return_code == 0:
        return True
    else:
        print >>sys.stderr, 'Error: %s is not installed on your system.' % executable
        sys.exit(1)

def install_xdg():
    print 'installing desktop menu files'
    check_executable('xdg-desktop-menu')

    os.system('xdg-desktop-menu install --novendor desktop/*.desktop')
    for filepath in glob.glob('icons/*'):
        print 'installing icon %s' % filepath
        os.system('xdg-icon-resource install --size 64 --novendor %s' % filepath)

install_xdg()
