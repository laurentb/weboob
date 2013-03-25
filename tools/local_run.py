#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

if len(sys.argv) < 2:
    print "Usage: %s SCRIPTNAME [args]" % sys.argv[0]
    sys.exit(1)
else:
    script = sys.argv[1]
    args = sys.argv[2:]

project = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
wd = os.path.join(project, 'localconfig')
if not os.path.isdir(wd):
    os.path.makedirs(wd)

env = os.environ.copy()
env['PYTHONPATH'] = project
env['WEBOOB_WORKDIR'] = wd

shutil.copyfile(
    os.path.expanduser('~/.config/weboob/backends'),
    os.path.join(project, wd, 'backends'))

with open(os.path.join(wd, 'sources.list'), 'w') as f:
    f.write("file://%s\n" % os.path.join(project, 'modules'))

# Hide output unless there is an error
p = subprocess.Popen(
    [sys.executable, os.path.join(project, 'scripts', 'weboob-config'), 'update'],
    env=env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
s = p.communicate()
if p.returncode != 0:
    print s[0]
    sys.exit(p.returncode)

os.execvpe(
    sys.executable,
    ['-Wall', os.path.join(project, 'scripts', script)] + args,
    env)
