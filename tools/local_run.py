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


def get_project_dir(name):
    wd = os.path.join(project, name)
    if not os.path.isdir(wd):
        os.makedirs(wd)
    return wd


wd = get_project_dir('localconfig')
venv = get_project_dir('localenv')

env = os.environ.copy()
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
def run_quiet(cmd):
    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    s = p.communicate()
    if p.returncode != 0:
        print(s[0].decode('utf-8'))
        if p.returncode > 1:
            sys.exit(p.returncode)


venv_exe = os.path.join(venv, 'bin', 'python')
run_quiet([
    sys.executable, '-m', 'virtualenv', '--system-site-packages',
    '--python', sys.executable, venv,
])
run_quiet([
    venv_exe, '-m', 'pip', 'install', '--no-deps', '--editable', project,
])
run_quiet([os.path.join(venv, 'bin', 'weboob-config'), 'update', '-d'])

if os.path.exists(script):
    spath = script
else:
    spath = os.path.join(venv, 'bin', script)

os.execvpe(
    venv_exe,
    [venv_exe, '-s'] + pyargs + [spath] + args,
    env)
