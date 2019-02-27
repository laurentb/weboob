#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Christophe Benz, Laurent Bachelier
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import glob
import os
import subprocess
import sys
from distutils.cmd import Command
from distutils.log import WARN

from setuptools import find_packages, setup


PY3 = sys.version_info.major >= 3


class BuildQt(Command):
    description = 'build Qt applications'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.announce('Building Qt applications...', WARN)
        make = self.find_executable('make', ('gmake', 'make'))
        if not PY3:
            pyuic5 = self.find_executable(
                'pyuic5',
                ('python2-pyuic5', 'pyuic5-python2.7', 'pyuic5'))
        else:
            pyuic5 = self.find_executable(
                'pyuic5',
                ('python3-pyuic5', 'pyuic5-python3.7', 'pyuic5-python3.6', 'pyuic5-python3.5', 'pyuic5'))
        if not pyuic5 or not make:
            print('Install missing component(s) (see above) or disable Qt applications (with --no-qt).',
                  file=sys.stderr)
            sys.exit(1)

        subprocess.check_call(
            [make,
             '-f', 'build.mk',
             '-s', '-j2',
             'all',
             'PYUIC=%s%s' % (pyuic5, ' WIN32=1' if sys.platform == 'win32' else '')])

    @staticmethod
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
        print('Could not find executable: %s' % name, file=sys.stderr)


def install_weboob(qt, xdg):
    scripts = set(os.listdir('scripts'))
    packages = set(find_packages(exclude=['modules', 'modules.*']))

    qt_scripts = set(('qboobmsg',
                      'qhavedate',
                      'qgalleroob',
                      'qboobtracker',
                      'qvideoob',
                      'weboob-config-qt',
                      'qwebcontentedit',
                      'qflatboob',
                      'qcineoob',
                      'qcookboob',
                      'qbooblyrics',
                      'qhandjoob'))

    if not qt:
        scripts = scripts - qt_scripts

    qt_packages = set((
        'weboob.applications.qboobmsg',
        'weboob.applications.qboobmsg.ui',
        'weboob.applications.qcineoob',
        'weboob.applications.qcineoob.ui',
        'weboob.applications.qcookboob',
        'weboob.applications.qcookboob.ui',
        'weboob.applications.qbooblyrics',
        'weboob.applications.qbooblyrics.ui',
        'weboob.applications.qhandjoob',
        'weboob.applications.qhandjoob.ui',
        'weboob.applications.qhavedate',
        'weboob.applications.qhavedate.ui',
        'weboob.applications.qvideoob',
        'weboob.applications.qvideoob.ui',
        'weboob.applications.qweboobcfg',
        'weboob.applications.qweboobcfg.ui',
        'weboob.applications.qwebcontentedit',
        'weboob.applications.qwebcontentedit.ui'
        'weboob.applications.qflatboob',
        'weboob.applications.qflatboob.ui',
        'weboob.applications.qboobtracker',
        'weboob.applications.qboobtracker.ui',
        'weboob.applications.qgalleroob',
        'weboob.applications.qgalleroob.ui',
    ))

    if not qt:
        packages = packages - qt_packages

    data_files = [
        ('share/man/man1', glob.glob('man/*')),
    ]
    if xdg:
        data_files.extend([
            ('share/applications', glob.glob('desktop/*')),
            ('share/icons/hicolor/64x64/apps', glob.glob('icons/*')),
        ])

    # Do not put PyQt, it does not work properly.
    requirements = [
        'lxml',
        'cssselect',
        'requests>=2.0.0',
        'python-dateutil',
        'PyYAML',
        'html2text>=3.200',
        'six',
        'unidecode',
        'Pillow',
        'futures; python_version < "3.2"',
    ]

    try:
        if sys.argv[1] == 'requirements':
            print('\n'.join(requirements))
            sys.exit(0)
    except IndexError:
        pass

    setup(
        name='weboob',
        version='1.5',
        description='Weboob, Web Outside Of Browsers',
        long_description=open('README.md').read(),
        author='Romain Bignon',
        author_email='weboob@weboob.org',
        maintainer='Romain Bignon',
        maintainer_email='romain@weboob.org',
        url='http://weboob.org/',
        license='GNU LGPL 3',
        classifiers=[
            'Environment :: Console',
            'Environment :: X11 Applications :: Qt',
            'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python',
            'Topic :: Communications :: Email',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Internet :: WWW/HTTP :: Browsers',
            'Topic :: Software Development :: Libraries :: Application Frameworks',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Text Processing :: Markup :: HTML',
        ],

        packages=packages,
        scripts=[os.path.join('scripts', script) for script in scripts],
        data_files=data_files,

        install_requires=requirements,
        python_requires='>=2.7',
        tests_require=[
            'flake8',
            'nose',
            'xunitparser',
            'coverage',
        ],
        cmdclass={
            'build_qt': BuildQt,
        },
    )


def extract_args(args, options, optlist):
    for option in optlist:
        yes = '--%s' % option
        no = '--no-%s' % option
        if yes in args and no in args:
            print('%s and %s options are incompatible' % (yes, no), file=sys.stderr)
            sys.exit(1)
        if yes in args:
            args.remove(yes)
            options[option] = True
        elif no in args:
            args.remove(no)
            options[option] = False


if os.getenv('WEBOOB_SETUP'):
    args = os.getenv('WEBOOB_SETUP').split()
else:
    args = sys.argv[1:]

options = {'qt': False, 'xdg': True}
extract_args(args, options, ('qt', 'xdg'))

if options['qt']:
    args.insert(0, 'build_qt')


sys.argv = [sys.argv[0]] + args

install_weboob(**options)
