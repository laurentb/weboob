#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

import os

setup(
    name='Weboob',
    version='0.1',
    description='Weboob, web out of the browser',
    author='Romain Bignon',
    author_email='romain@peerfuse.org',
    license='GPLv3',
    url='http://www.weboob.org',
    packages=find_packages(exclude=['ez_setup']),
    scripts=[os.path.join('scripts', script) for script in os.listdir('scripts')],
    install_requires=[
                'pyyaml',
    ]
)
