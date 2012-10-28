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


def find_executable(name, names):
    envname = '%s_EXECUTABLE' % name.upper()
    if os.getenv(envname):
        return os.getenv(envname)
    paths = os.getenv('PATH', os.defpath).split(os.pathsep)
    exts = os.getenv('PATHEXT', os.pathsep).split(os.pathsep)
    for name in names:
        for path in paths:
            for ext in exts:
                fpath = os.path.join(path, name) + ext
                if os.path.exists(fpath) and os.access(fpath, os.X_OK):
                    return fpath


def build_qt():
    print 'Building Qt applications'
    make = find_executable('make', ('gmake', 'make'))
    pyuic4 = find_executable('pyuic4', ('python2-pyuic4', 'pyuic4-2.7', 'pyuic4-2.6', 'pyuic4-2.5', 'pyuic4'))
    if not pyuic4 or not make:
        print >>sys.stderr, 'Install PyQt4-devel or disable Qt applications (with --no-qt).'
        sys.exit(1)

    subprocess.check_call([make, '-C', 'weboob/applications/qboobmsg/ui', 'PYUIC=%s' % pyuic4])
    subprocess.check_call([make, '-C', 'weboob/applications/qhavedate/ui', 'PYUIC=%s' % pyuic4])
    subprocess.check_call([make, '-C', 'weboob/applications/qwebcontentedit/ui', 'PYUIC=%s' % pyuic4])
    subprocess.check_call([make, '-C', 'weboob/applications/qflatboob/ui', 'PYUIC=%s' % pyuic4])
    subprocess.check_call([make, '-C', 'weboob/tools/application/qt', 'PYUIC=%s' % pyuic4])
    if sys.platform != 'win32':
        subprocess.check_call([make, '-C', 'weboob/applications/qvideoob/ui', 'PYUIC=%s' % pyuic4])


class Options(object):
    hildon = False
    qt = True
    xdg = True

options = Options()

args = list(sys.argv)
if '--hildon' in args and '--no-hildon' in args:
    print >>sys.stderr, '--hildon and --no-hildon options are incompatible'
    sys.exit(1)
if '--qt' in args and '--no-qt' in args:
    print >>sys.stderr, '--qt and --no-qt options are incompatible'
    sys.exit(1)
if '--xdg' in args and '--no-xdg' in args:
    print >>sys.stderr, '--xdg and --no-xdg options are incompatible'
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
qt_scripts = set(('qboobmsg', 'qhavedate', 'qvideoob', 'weboob-config-qt', 'qwebcontentedit', 'qflatboob'))

if not options.hildon:
    scripts = scripts - hildon_scripts
if options.qt:
    build_qt()
else:
    scripts = scripts - qt_scripts

hildon_packages = set((
    'weboob.applications.masstransit',
))
qt_packages = set((
    'weboob.applications.qboobmsg',
    'weboob.applications.qboobmsg.ui',
    'weboob.applications.qhavedate',
    'weboob.applications.qhavedate.ui',
    'weboob.applications.qvideoob',
    'weboob.applications.qvideoob.ui',
    'weboob.applications.qweboobcfg',
    'weboob.applications.qweboobcfg.ui',
    'weboob.applications.qwebcontentedit',
    'weboob.applications.qwebcontentedit.ui'
    'weboob.applications.qflatboob',
    'weboob.applications.qflatboob.ui'
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
    version = '0.e',
    description='Weboob, Web Outside Of Browsers',
    long_description=open('README').read(),
    author='Romain Bignon',
    author_email='weboob@weboob.org',
    maintainer='Romain Bignon',
    maintainer_email='romain@weboob.org',
    url='http://weboob.org/',
    license='GNU AGPL 3',
    classifiers=[
        'Environment :: Console',
        'Environment :: X11 Applications :: Qt',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python',
        'Topic :: Communications :: Email',
        'Topic :: Internet :: WWW/HTTP',
    ],

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
