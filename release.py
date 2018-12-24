#!/usr/bin/python
from __future__ import print_function

import argparse
import os
import sys
from subprocess import check_call

WORKTREE = 'release_tmp'
OPTIONS = ['--qt', '--xdg']


def make_tarball(tag, wheel):
    # Create and enter a temporary worktree
    if os.path.isdir(WORKTREE):
        check_call(['git', 'worktree', 'remove', '--force', WORKTREE])
    check_call(['git', 'worktree', 'add', WORKTREE, tag])
    assert os.path.isdir(WORKTREE)
    os.chdir(WORKTREE)

    check_call([sys.executable, 'setup.py'] + OPTIONS +
               ['sdist',
                '--keep',
                '--dist-dir', '../dist'])
    if wheel:
        check_call([sys.executable, 'setup.py'] + OPTIONS +
                   ['bdist_wheel',
                    '--keep',
                    '--dist-dir', '../dist'])

    # Clean up the temporary worktree
    os.chdir(os.pardir)
    check_call(['git', 'worktree', 'remove', '--force', WORKTREE])
    assert not os.path.isdir(WORKTREE)

    files = ['dist/weboob-%s.tar.gz' % tag]
    if wheel:
        files.append('dist/weboob-%s-py2.py3-none-any.whl' % tag)
    for f in files:
        if not os.path.exists(f):
            raise Exception('Generated file not found at %s' % f)
        else:
            print('Generated file: %s' % f)
    print('To upload to PyPI, run: twine upload -s %s' % ' '.join(files))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    tarball_parser = subparsers.add_parser('tarball')
    tarball_parser.add_argument('tag')
    tarball_parser.add_argument('--no-wheel', action='store_false', dest='wheel')
    tarball_parser.set_defaults(mode='tarball')

    args = parser.parse_args()
    if args.mode == 'tarball':
        make_tarball(args.tag, args.wheel)
