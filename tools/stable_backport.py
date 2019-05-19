#!/usr/bin/env python3

from __future__ import print_function

import time
import sys
import re
from contextlib import contextmanager
from os import system, path, makedirs, getenv
from subprocess import check_output, STDOUT, CalledProcessError
from collections import defaultdict
import shutil

from termcolor import colored


STABLE_VERSION = getenv('WEBOOB_BACKPORT_STABLE', '1.3')
DEVEL_BRANCH = getenv('WEBOOB_BACKPORT_DEVEL', 'master')


@contextmanager
def log(message, success='done'):
    print('%s... ' % message, end='', flush=True)
    start = time.time()
    try:
        yield
    except KeyboardInterrupt:
        print(colored('abort', 'red'))
        sys.exit(1)
    except Exception as e:
        print(colored('fail: %s' % e, 'red'))
        raise
    else:
        print('%s %s' % (colored(success, 'green'),
                         colored('(%.2fs)' % (time.time() - start), 'blue')))


def create_compat_dir(name):
    if not path.exists(name):
        makedirs(name)
    with open(path.join(name, '__init__.py'), 'w'):
        pass


MANUAL_PORTS = [
    'weboob.tools.captcha.virtkeyboard',
]

MANUAL_PORT_DIR = path.join(path.dirname(__file__), 'stable_backport_data')


class Error(object):
    def __init__(self, filename, linenum, message):
        self.filename = filename
        self.linenum = linenum
        self.message = message
        self.compat_dir = path.join(path.dirname(filename), 'compat')

    def __repr__(self):
        return '<%s filename=%r linenum=%s message=%r>' % (type(self).__name__, self.filename, self.linenum, self.message)

    def reimport_module(self, module):
        # not a weboob module, probably a false positive.
        if not module.startswith('weboob'):
            return

        dirname = module.replace('.', '/')
        filename = dirname + '.py'
        new_module = module.replace('.', '_')
        target = path.join(self.compat_dir, '%s.py' % new_module)
        base_module = '.'.join(module.split('.')[:-1])

        try:
            r = check_output('git show %s:%s' % (DEVEL_BRANCH, filename), shell=True, stderr=STDOUT).decode('utf-8')
        except CalledProcessError:
            # this file does not exist, perhaps a directory.
            return

        if module in MANUAL_PORTS:
            shutil.copyfile(path.join(MANUAL_PORT_DIR, path.basename(target)), target)
        else:
            # Copy module from devel to a compat/ sub-module
            with open(target, 'w') as fp:
                for line in r.split('\n'):
                    # Replace relative imports to absolute ones
                    m = re.match(r'^from (\.\.?)([\w_\.]+) import (.*)', line)
                    if m:
                        if m.group(1) == '..':
                            base_module = '.'.join(base_module.split('.')[:-1])
                        fp.write('from %s.%s import %s\n' % (base_module, m.group(2), m.group(3)))
                        continue

                    # Inherit all classes by previous ones, if they already existed.
                    m = re.match(r'^class (\w+)\(([\w,\s]+)\):(.*)', line)
                    if m and path.exists(filename) and system('grep "^class %s" %s >/dev/null' % (m.group(1), filename)) == 0:
                        symbol = m.group(1)
                        trailing = m.group(3)
                        fp.write('from %s import %s as _%s\n' % (module, symbol, symbol))
                        fp.write('class %s(_%s):%s\n' % (symbol, symbol, trailing))
                        continue

                    fp.write('%s\n' % line)

        # Particular case, in devel some imports have been added to
        # weboob/browser/__init__.py
        system(r'sed -i -e "s/from weboob.browser import/from weboob.browser.browsers import/g" %s'
               % self.filename)
        # Replace import to this module by a relative import to the copy in
        # compat/
        system(r'sed -i -e "%ss/from \([A-Za-z0-9_\.]\+\) import \(.*\)/from .compat.%s import \2/g" %s'
               % (self.linenum, new_module, self.filename))


def remove_block(name, start):
    lines = []
    with open(name, 'r') as fd:
        it = iter(fd)
        for n in range(start - 1):
            lines.append(next(it))
        line = next(it)

        level = len(re.match(r'^( *)', line).group(1))
        for line in it:
            if not line.strip():
                continue
            new = len(re.match(r'^( *)', line).group(1))
            if new <= level:
                lines.append(line)
                break

        lines.extend(it)

    with open(name, 'w') as fd:
        fd.write(''.join(lines))


class NoNameInModuleError(Error):
    def fixup(self):
        m = re.match(r"No name '(\w+)' in module '([\w\.]+)'", self.message)
        module = m.group(2)
        self.reimport_module(module)


class ImportErrorError(Error):
    def fixup(self):
        m = re.match(r"Unable to import '([\w\.]+)'", self.message)
        module = m.group(1)
        self.reimport_module(module)


class ManualBackport(Error):
    def fixup(self):
        self.reimport_module(self.message)


def replace_all(expr, dest):
    system(r"""for file in $(git ls-files modules | grep '\.py$');
               do
                   sed -i -e "s/""" + expr + '/' + dest + """/g" $file
               done""")


def output_lines(cmd):
    return check_output(cmd, shell=True, stderr=STDOUT).decode('utf-8').rstrip().split('\n')


class StableBackport(object):
    errors = {'E0611': NoNameInModuleError,
              'E0401': ImportErrorError,
             }

    def main(self):
        with log('Removing previous compat files'):
            system('git rm -q "modules/*/compat/*.py"')

        with log('Copying last version of modules from devel'):
            system('git checkout --theirs %s modules' % DEVEL_BRANCH)

        with log('Replacing version number'):
            replace_all(r"""^\(\s*\)\(VERSION\)\( *\)=\( *\)[\"'][0-9]\+\..\+[\"']\(,\?\)$""",
                        r"""\1\2\3=\4'""" + STABLE_VERSION + r"""'\5""")

        with log('Removing staling data'):
            system('tools/stale_pyc.py')
            system('find modules -type d -empty -delete')
            system('git add -u')

        with log('Lookup modules errors'):
            r = check_output("pylint modules/* -f parseable -E -d all -e no-name-in-module,import-error; exit 0", shell=True, stderr=STDOUT).decode('utf-8')

        dirnames = defaultdict(list)
        for line in r.split('\n'):
            m = re.match(r'([\w\./]+):(\d+): \[(\w+)[^\]]+\] (.*)', line)
            if not m:
                continue

            filename = m.group(1)
            linenum = m.group(2)
            error = m.group(3)
            msg = m.group(4)

            dirnames[path.dirname(filename)].append(self.errors[error](filename, linenum, msg))

        with log('Searching manual backports'):
            for manual in MANUAL_PORTS:
                r = check_output("grep -nEr '^from %s import ' modules" % manual, shell=True).strip().decode('utf-8')
                for line in r.split('\n'):
                    m = re.match(r'([\w\./]+):(\d+):.*', line)
                    filename = m.group(1)
                    linenum = m.group(2)
                    target = dirnames[path.dirname(filename)]
                    for err in target:
                        if err.filename == filename and err.linenum == linenum:
                            # an error was already spot on this line
                            break
                    else:
                        target.append(ManualBackport(filename, linenum, manual))

        for dirname, errors in sorted(dirnames.items()):
            with log('Fixing up %s errors in %s' % (colored(str(len(errors)), 'magenta'),
                                                    colored(dirname, 'yellow'))):
                compat_dirname = path.join(dirname, 'compat')
                create_compat_dir(compat_dirname)
                for error in errors:
                    error.fixup()
                system('git add %s' % compat_dirname)

        system('git add -u')


if __name__ == '__main__':
    StableBackport().main()
