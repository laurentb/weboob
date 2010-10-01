#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from __future__ import with_statement

from setuptools import find_packages, setup

import glob
import os
import subprocess
import sys


def check_executable(executable, error):
    with open('/dev/null', 'w') as devnull:
        process = subprocess.Popen(['which', executable], stdout=devnull)
        return_code = process.wait()
    if return_code == 0:
        return True
    else:
        print >>sys.stderr, 'Error: %s is not installed on your system.' % executable
        if error:
            print >>sys.stderr, error
        sys.exit(1)

def build_qt():
    print 'Building Qt applications'
    check_executable('pyuic4', 'To disable Qt applications, use --no-qt.')

    os.system('make -C weboob/applications/qboobmsg/ui')
    os.system('make -C weboob/applications/qhavesex/ui')
    os.system('make -C weboob/applications/qvideoob/ui')
    os.system('make -C weboob/tools/application/qt')

def install_xdg():
    """
    On xdg-compliant systems, install desktop file and icon
    """
    print 'Installing desktop menu files'
    check_executable('xdg-desktop-menu', 'To disable resources installation, use --no-xdg.')

    os.system('xdg-desktop-menu install --novendor desktop/*.desktop')
    for filepath in glob.glob('icons/*'):
        print 'Installing icon %s' % filepath
        os.system('xdg-icon-resource install --size 64 --novendor %s' % filepath)


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

if '--hildon' in args:
    options.hildon = True
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

hildon_scripts = ('masstransit',)
qt_scripts = ('qboobmsg', 'qhavesex', 'qvideoob', 'weboob-config-qt')
scripts = os.listdir('scripts')

if not options.hildon:
    scripts = set(scripts) - set(hildon_scripts)
if options.qt:
    build_qt()
else:
    scripts = set(scripts) - set(qt_scripts)

hildon_packages = (
    'weboob.applications.masstransit',
    )
qt_packages = (
    'weboob.applications.qboobmsg',
    'weboob.applications.qboobmsg.ui',
    'weboob.applications.qhavesex',
    'weboob.applications.qhavesex.ui',
    'weboob.applications.qvideoob',
    'weboob.applications.qvideoob.ui',
    'weboob.applications.qweboobcfg',
    'weboob.applications.qweboobcfg.ui',
    )
packages = find_packages()

if not options.hildon:
    packages = set(packages) - set(hildon_packages)
if not options.qt:
    packages = set(packages) - set(qt_packages)

setup(
    name='weboob',
    version='0.2',
    description='Weboob, Web Out Of Browsers - development version',
    author='Romain Bignon',
    author_email='weboob@weboob.org',
    maintainer='Christophe Benz',
    maintainer_email='christophe.benz@gmail.com',
    license='GPLv3',
    url='http://www.weboob.org',
    packages=packages,
    scripts=[os.path.join('scripts', script) for script in scripts],
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

if sys.argv[1] in ('install', 'develop') and options.xdg and not options.hildon:
    install_xdg()
