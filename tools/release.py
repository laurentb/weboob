#!/usr/bin/env python3

import argparse
import configparser
import os
import re
import sys
import datetime
from subprocess import check_call, check_output

from weboob.tools.misc import to_unicode

WORKTREE = 'release_tmp'


def make_tarball(tag, wheel):
    # Create and enter a temporary worktree
    if os.path.isdir(WORKTREE):
        check_call(['git', 'worktree', 'remove', '--force', WORKTREE])
    check_call(['git', 'worktree', 'add', WORKTREE, tag])
    assert os.path.isdir(WORKTREE)
    os.chdir(WORKTREE)

    check_call([sys.executable, 'setup.py'] +
               ['sdist',
                '--keep',
                '--dist-dir', '../dist'])
    if wheel:
        check_call([sys.executable, 'setup.py'] +
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


def changed_modules(changes, changetype):
    for change in changes:
        change = change.decode('utf-8').split()
        if change[0] == changetype:
            m = re.match(r'modules/([^/]+)/__init__\.py', change[1])
            if m:
                yield m.group(1)


def get_caps(module, config):
    try:
        return sorted(c for c in config[module]['capabilities'].split() if c != 'CapCollection')
    except KeyError:
        return ['**** FILL ME **** (running weboob update could help)']

def new_modules(start, end):
    os.chdir(os.path.join(os.path.dirname(__file__), os.path.pardir))
    modules_info = configparser.ConfigParser()
    with open('modules/modules.list') as f:
        modules_info.read_file(f)
    git_cmd = ['git', 'diff', '--no-renames', '--name-status', '%s..%s' % (start, end), '--', 'modules/']

    added_modules = sorted(changed_modules(check_output(git_cmd).splitlines(), 'A'))
    deleted_modules = sorted(changed_modules(check_output(git_cmd).splitlines(), 'D'))

    for added_module in added_modules:
        yield 'New %s module (%s)' % (added_module, ', '.join(get_caps(added_module, modules_info)))
    for deleted_module in deleted_modules:
        yield 'Deleted %s module' % deleted_module


def changelog(start, end='HEAD'):
    def sortkey(d):
        """Put the commits with multiple domains at the end"""
        return (len(d), d)

    commits = {}
    for commithash in check_output(['git', 'rev-list', '{}..{}'.format(start, end)]).splitlines():
        title, domains = commitinfo(commithash)
        commits.setdefault(domains, []).append(title)

    for line in new_modules(start, end):
        commits.setdefault(('General',), []).append(line)

    cl = ''
    for domains in sorted(commits.keys(), key=sortkey):
        cl += '\n\n\t' + '\n\t'.join(domains)
        for title in commits[domains]:
            cl += '\n\t* ' + title

    return cl.lstrip('\n')


def domain(path):
    dirs = os.path.dirname(path).split('/')
    if dirs == ['']:
        return 'General: Core'
    if dirs[0] == 'man' or path == 'tools/py3-compatible.modules':
        return None
    if dirs[0] == 'weboob':
        try:
            if dirs[1] in ('core', 'tools'):
                return 'General: Core'
            elif dirs[1] == 'capabilities':
                return 'Capabilities'
            elif dirs[1] == 'browser':
                try:
                    if dirs[2] == 'filters':
                        return 'Browser: Filters'
                except IndexError:
                    return 'Browser'
            elif dirs[1] == 'applications':
                try:
                    return 'Applications: {}'.format(dirs[2])
                except IndexError:
                    return 'Applications'
            elif dirs[1] == 'application':
                try:
                    return 'Applications: {}'.format(dirs[2].title())
                except IndexError:
                    return 'Applications'
        except IndexError:
            return 'General: Core'
    if dirs[0] in ('contrib', 'tools'):
        return 'Tools'
    if dirs[0] in ('docs', 'icons'):
        return 'Documentation'
    if dirs[0] == 'modules':
        try:
            return 'Modules: {}'.format(dirs[1])
        except IndexError:
            return 'General: Core'
    return 'Unknown'


def commitinfo(commithash):
    info = check_output(['git', 'show', '--format=%s', '--name-only', commithash]).decode('utf-8').splitlines()
    title = to_unicode(info[0])
    domains = set([domain(p) for p in info[2:] if domain(p)])
    if 'Unknown' in domains and len(domains) > 1:
        domains.remove('Unknown')
    if not domains or len(domains) > 5:
        domains = set(['Unknown'])

    if 'Unknown' not in domains:
        # When the domains are known, hide the title prefixes
        title = re.sub(r'^(?:[\w\./\s]+:|\[[\w\./\s]+\])\s*', '', title, flags=re.UNICODE)

    return title, tuple(sorted(domains))


def previous_version():
    """
    Get the highest version tag
    """
    for v in check_output(['git', 'tag', '-l', '*.*', '--sort=-v:refname']).splitlines():
        return v.decode()


def prepare(start, end, version):
    print('Weboob %s (%s)\n' % (version, datetime.date.today().strftime('%Y-%m-%d')))
    print(changelog(start, end))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepare and export a release.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog='This is mostly meant to be called from release.sh for now.',
    )

    subparsers = parser.add_subparsers()

    prepare_parser = subparsers.add_parser(
        'prepare',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    prepare_parser.add_argument('version')
    prepare_parser.add_argument('--start', default=previous_version(), help='Commit of the previous release')
    prepare_parser.add_argument('--end', default='HEAD', help='Last commit before the new release')
    prepare_parser.set_defaults(mode='prepare')

    tarball_parser = subparsers.add_parser(
        'tarball',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    tarball_parser.add_argument('tag')
    tarball_parser.add_argument('--no-wheel', action='store_false', dest='wheel')
    tarball_parser.set_defaults(mode='tarball')

    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.start, args.end, args.version)
    elif args.mode == 'tarball':
        make_tarball(args.tag, args.wheel)
