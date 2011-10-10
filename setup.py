#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from __future__ import with_statement

from setuptools import find_packages, setup

import glob
import os
import subprocess
import sys


def check_executable_win(executable, error):
    pathsrc = "PATH"        # Where to get the path
    pathextsrc = "PATHEXT"  # Where to get the extension list
    dotfirst = 1            # Should we look in the current directory also?

    path = os.environ[pathsrc]
    path = filter(None, path.split(";"))

    if dotfirst:
        path = ["."]+path

    pathext = os.environ[pathextsrc]
    pathext = filter(None, pathext.split(";"))

    # The command name we are looking for
    cmdName = executable

    # Is the command name really a file name?
    if '.' in cmdName:
        # Fake it by making pathext a list of one empty string.
        pathext = ['']

    # Loop over the directories on the path, looking for the file.
    for d in path:
        for e in pathext:
            filePath = os.path.join(d, cmdName + e)
            if os.path.exists(filePath):
                return filePath.replace( '\\', '/' )

    print >>sys.stderr, 'Error: %s is not installed on your system.' % executable
    if error:
        print >>sys.stderr, error
    sys.exit(1)

def check_executable_unix(executable, error):
    with open('/dev/null', 'w') as devnull:
        process = subprocess.Popen(['which', executable], stdout=devnull)
        return_code = process.wait()
    if return_code == 0:
        return executable
    else:
        print >>sys.stderr, 'Error: %s is not installed on your system.' % executable
        if error:
            print >>sys.stderr, error
        sys.exit(1)

if sys.platform == 'win32':
    check_executable = check_executable_win
else:
    check_executable = check_executable_unix

def build_qt():
    print 'Building Qt applications'
    pyuic4 = check_executable('pyuic4', 'To disable Qt applications, use --no-qt.')

    if sys.platform == 'win32':
        env={ 'PYUIC' : pyuic4, 'PATH':os.environ['PATH']}
        extraMakeFlag = ['-e']
    else:
        env = None
        extraMakeFlag = []

    subprocess.check_call(['make']+extraMakeFlag+['-C','weboob/applications/qboobmsg/ui'], env=env )
    subprocess.check_call(['make']+extraMakeFlag+['-C','weboob/applications/qhavesex/ui'], env=env )
    if sys.platform != 'win32':
        subprocess.check_call(['make']+extraMakeFlag+['-C','weboob/applications/qvideoob/ui'], env=env )
    subprocess.check_call(['make']+extraMakeFlag+['-C','weboob/applications/qwebcontentedit/ui'], env=env )
    subprocess.check_call(['make']+extraMakeFlag+['-C','weboob/tools/application/qt'], env=env )

class Options:
    pass

options = Options()
options.hildon = False
options.qt = True
options.xdg = True

args = list(sys.argv)
if '--hildon' in args and '--no-hildon' in args:
    print '--hildon and --no-hildon options are incompatible'
    sys.exit(1)
if '--qt' in args and '--no-qt' in args:
    print '--qt and --no-qt options are incompatible'
    sys.exit(1)
if '--xdg' in args and '--no-xdg' in args:
    print '--xdg and --no-xdg options are incompatible'
    sys.exit(1)

if '--hildon' in args or os.environ.get('HILDON') == 'true':
    options.hildon = True
    if '--hildon' in args:
        args.remove('--hildon')
elif '--no-hildon' in args:
    options.hildon = False
    args.remove('--no-hildon')

if '--qt' in args:
    options.qt = True
    args.remove('--qt')
elif '--no-qt' in args:
    options.qt = False
    args.remove('--no-qt')

if '--xdg' in args:
    options.xdg = True
    args.remove('--xdg')
elif '--no-xdg' in args:
    options.xdg = False
    args.remove('--no-xdg')

sys.argv = args

scripts = set(os.listdir('scripts'))
packages = set(find_packages())

hildon_scripts = set(('masstransit',))
qt_scripts = set(('qboobmsg', 'qhavesex', 'qvideoob', 'weboob-config-qt', 'qwebcontentedit'))

if not options.hildon:
    scripts = scripts - hildon_scripts
if options.qt:
    build_qt()
else:
    scripts = scripts - qt_scripts

hildon_packages = set((
    'weboob.applications.masstransit',
    ),)
qt_packages = set((
    'weboob.applications.qboobmsg',
    'weboob.applications.qboobmsg.ui',
    'weboob.applications.qhavesex',
    'weboob.applications.qhavesex.ui',
    'weboob.applications.qvideoob',
    'weboob.applications.qvideoob.ui',
    'weboob.applications.qweboobcfg',
    'weboob.applications.qweboobcfg.ui',
    'weboob.applications.qwebcontentedit',
    'weboob.applications.qwebcontentedit.ui'
    ))

if not options.hildon:
    packages = packages - hildon_packages
if not options.qt:
    packages = packages - qt_packages

data_files = [
    ('share/man/man1', glob.glob('man/*')),
    ]
if options.xdg:
    data_files.extend([
        ('share/applications', glob.glob('desktop/*')),
        ('share/icons/hicolor/64x64/apps', glob.glob('icons/*')),
        ])

setup(
    name='weboob',
    version = '0.a',
    description='Weboob, Web Out Of Browsers',
    author='Romain Bignon',
    author_email='weboob@weboob.org',
    maintainer='Christophe Benz',
    maintainer_email='christophe.benz@gmail.com',
    license='AGPLv3+',
    url='http://www.weboob.org',
    packages=packages,
    scripts=[os.path.join('scripts', script) for script in scripts],

    data_files=data_files,

    install_requires=[
        # 'ClientForm', # python-clientform
        # 'elementtidy', # python-elementtidy
        # 'FeedParser', # python-feedparser
        # 'gdata', # python-gdata
        # 'html5lib', # python-html5lib
        # 'lxml', # python-lxml
        # 'Mako', # python-mako
        # 'mechanize', # python-mechanize
        # 'PIL', # python-imaging
        # 'PyQt', # python-qt4
        # 'python-dateutil', # python-dateutil
        # 'PyYAML', # python-yaml
        # 'Routes', # python-routes
        # 'simplejson', # python-simplejson
        # 'WebOb', # python-webob
        ],
)
