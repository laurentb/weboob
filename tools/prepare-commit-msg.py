#!/usr/bin/env python3
import os
import subprocess
import sys


def get_files():
    git_updated_files = subprocess.run(
        ['git', 'diff', '--name-status', '--cached', '--diff-filter=ACMR'],
        stdout=subprocess.PIPE, check=True, encoding='utf-8')
    return [(f.partition('\t')[0], f.partition('\t')[-1].split(os.path.sep))
            for f in git_updated_files.stdout.split('\n') if f]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = None

    if 'merge' in sys.argv or 'squash' in sys.argv:
        sys.exit()

    files = get_files()

    updated_modules = list(set(f[1][1] for f in files if f[1][0] == 'modules' and len(f[1]) > 2))

    print(files)

    updates = set()
    modules = set()
    for f in files:
        if f[1][0] == 'modules':
            if len(f[1]) > 2:
                updates.add(f[1][1])
                modules.add(f[1][1])
        elif f[1][0] in ('setup.py', 'setup.cfg', 'README.md'):
            updates.add('setup')
        elif f[1][0:2] == ['weboob', 'applications']:
            if len(f[1]) > 2:
                updates.add(f[1][2])
        elif f[1][0:2] == ['weboob', 'browser', 'filters']:
            updates.add('filters')
        elif f[1][0:2] == ['weboob', 'browser']:
            updates.add('browser')
        elif f[1][0:2] == ['weboob', 'tools']:
            if len(f[1]) > 2:
                updates.add(f[1][2].replace('.py', ''))
        elif f[1][0:1] == ['weboob']:
            updates.add('core')
        elif f[1][0:1] in (['tools'], ['contrib']):
            if len(f[1]) > 1:
                updates.add(f[1][1].replace('.py', ''))

    if filename:
        if len(updates):
            with open(filename) as f:
                text = f.read().splitlines(True)
            if ':' not in text[0]:
                text[0] = '|'.join(updates) + ': ' + text[0]
            with open(filename, 'w') as f:
                f.writelines(text)

    else:
        print(updates)
