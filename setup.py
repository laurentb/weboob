#! /usr/bin/env python3
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
import sys

from setuptools import find_packages, setup


PY3 = sys.version_info.major >= 3


def install_weboob():
    packages = set(find_packages(exclude=['modules', 'modules.*']))

    data_files = [
        ('share/man/man1', glob.glob('man/*')),
    ]

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
        'Babel',
    ]

    try:
        if sys.argv[1] == 'requirements':
            print('\n'.join(requirements))
            sys.exit(0)
    except IndexError:
        pass

    setup(
        packages=packages,
        data_files=data_files,
    )


if os.getenv('WEBOOB_SETUP'):
    args = os.getenv('WEBOOB_SETUP').split()
else:
    args = sys.argv[1:]

sys.argv = [sys.argv[0]] + args

install_weboob()
