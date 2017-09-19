#!/usr/bin/env python3
import os
import re
import subprocess
import sys

import configparser

since = sys.argv[1]


def changed_modules(changes, changetype):
    for change in changes:
        change = change.decode('utf-8').split()
        if change[0] == changetype:
            m = re.match('modules/([^/]+)/__init__\.py', change[1])
            if m:
                yield m.group(1)


def get_caps(module, config):
    try:
        return sorted(c for c in config[module]['capabilities'].split() if c != 'CapCollection')
    except KeyError:
        return ['**** FILL ME **** (running weboob update could help)']

os.chdir(os.path.join(os.path.dirname(__file__), os.path.pardir))
modules_info = configparser.ConfigParser()
with open('modules/modules.list') as f:
    modules_info.read_file(f)
git_cmd = ['git', 'diff', '--no-renames', '--name-status', '%s..HEAD' % since, '--', 'modules/']

added_modules = sorted(changed_modules(subprocess.check_output(git_cmd).splitlines(), 'A'))
deleted_modules = sorted(changed_modules(subprocess.check_output(git_cmd).splitlines(), 'D'))

for added_module in added_modules:
    print('        * New %s module (%s)' % (added_module, ', '.join(get_caps(added_module, modules_info))))
for deleted_module in deleted_modules:
    print('        * Deleted %s module' % deleted_module)
