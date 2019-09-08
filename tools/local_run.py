#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import subprocess
import sys
import tempfile

if len(sys.argv) < 2:
    print("Usage: %s SCRIPTNAME [args]" % sys.argv[0])
    sys.exit(1)
else:
    args = sys.argv[1:]
    pyargs = []
    while args and args[0].startswith('-'):
        pyargs.append(args.pop(0))
    script = args.pop(0)


project = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
wd = os.path.join(project, 'localconfig')
if not os.path.isdir(wd):
    os.makedirs(wd)

paths = os.getenv('PYTHONPATH', None)
if not paths:
    paths = sys.path
else:
    paths = paths.split(':')
if project not in paths:
    paths.insert(0, project)
env = os.environ.copy()
env['PYTHONPATH'] = ':'.join(p for p in paths if p)
env['WEBOOB_WORKDIR'] = wd
env['WEBOOB_DATADIR'] = wd
env['WEBOOB_BACKENDS'] = os.getenv('WEBOOB_LOCAL_BACKENDS',
                                   os.getenv('WEBOOB_BACKENDS',
                                             os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')), 'weboob', 'backends')))

modpath = os.getenv('WEBOOB_MODULES', os.path.join(project, 'modules'))

with tempfile.NamedTemporaryFile(mode='w', dir=wd, delete=False) as f:
    f.write("file://%s\n" % modpath)
os.rename(f.name, os.path.join(wd, 'sources.list'))

# Hide output unless there is an error
p = subprocess.Popen(
    [sys.executable, os.path.join(project, 'scripts', 'weboob-config'), 'update', '-d'],
    env=env,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
s = p.communicate()
if p.returncode != 0:
    print(s[0])
    if p.returncode > 1:
        sys.exit(p.returncode)

if os.path.exists(script):
    spath = script
else:
    spath = os.path.join(project, 'scripts', script)

os.execvpe(
    sys.executable,
    [sys.executable, '-s'] + pyargs + [spath] + args,
    env)
