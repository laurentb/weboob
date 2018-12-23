#!/usr/bin/python
from __future__ import print_function

import argparse
import os
import sys
from subprocess import check_call

WORKTREE = 'release_tmp'
OPTIONS = ['--qt', '--xdg']

def make_tarball(tag):
    # Create and enter a temporary worktree
    if os.path.isdir(WORKTREE):
        check_call(['git', 'worktree', 'remove', '--force', WORKTREE])
    check_call(['git', 'worktree', 'add', WORKTREE, tag])
    assert os.path.isdir(WORKTREE)
    os.chdir(WORKTREE)

    check_call([sys.executable, 'setup.py'] + OPTIONS + ['sdist',
               '--keep',
               '--dist-dir', '../dist'])

    # Clean up the temporary worktree
    os.chdir(os.pardir)
    check_call(['git', 'worktree', 'remove', '--force', WORKTREE])
    assert not os.path.isdir(WORKTREE)

    tarball = 'dist/weboob-%s.tar.gz' % tag
    if os.path.exists(tarball):
        print('Generated tarball: %s' % tarball)
        print('To upload to PyPI, run: twine upload -s %s' % tarball)
    else:
        raise Exception('Generated tarball not found at %s' % tarball)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    tarball_parser = subparsers.add_parser('tarball')
    tarball_parser.add_argument('tag')
    tarball_parser.set_defaults(mode='tarball')

    args = parser.parse_args()
    if args.mode == 'tarball':
        make_tarball(args.tag)
