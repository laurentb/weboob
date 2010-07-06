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


from setuptools import setup

import os


os.system('make -C weboob/applications/qweboobcfg/ui')

setup(
    name='weboob-qweboobcfg',
    version='0.1',
    description='QWeboobCfg, the Weboob GUI configuration tool',
    long_description='Configure backends',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/QWeboobCfg',
    namespace_packages = ['weboob', 'weboob.applications'],
    packages=[
        'weboob',
        'weboob.applications',
        'weboob.applications.qweboobcfg',
        'weboob.applications.qweboobcfg.ui',
        ],
    scripts=[
        'scripts/qweboobcfg',
        ],
    install_requires=[
        'weboob-core',
        ],
)
