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


setup(
    name='weboob-backends-dating',
    version='0.1',
    description='Weboob backends implementing dating capability',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapDating',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.aum',
        'weboob.backends.aum.data',
        'weboob.backends.aum.optim',
        'weboob.backends.aum.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)
