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


setup(
    name='weboob-bank-backends',
    version='0.1',
    description='Weboob backends implementing bank capability',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapBank',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.bnporc',
        'weboob.backends.bnporc.data',
        'weboob.backends.bnporc.pages',
        'weboob.backends.cragr',
        'weboob.backends.cragr.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-dating-backends',
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

setup(
    name='weboob-messages-backends',
    version='0.1',
    description='Weboob backends implementing messages capability',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapMessages',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.dlfp',
        'weboob.backends.dlfp.pages',
        'weboob.backends.fourchan',
        'weboob.backends.fourchan.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-travel-backends',
    version='0.1',
    description='Weboob backends implementing travel capability',
    author='Romain Bignon, Julien Hébert',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapTravel',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.canaltp',
        'weboob.backends.transilien',
        'weboob.backends.transilien.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-torrent-backends',
    version='0.1',
    description='Weboob backends implementing torrent capability',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapTorrent',
    namespace_packages = ['weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.gazelle',
        'weboob.backends.gazelle.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-video-backends',
    version='0.1',
    description='Weboob backends implementing video capability',
    author='Christophe Benz, Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapVideo',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.ina',
        'weboob.backends.ina.pages',
        'weboob.backends.youtube',
        'weboob.backends.youtube.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-video-backends-nsfw',
    version='0.1',
    description='Weboob backends implementing video capability - non-suitable for work',
    author='Romain Bignon, Roger Philibert',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapVideo',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.youjizz',
        'weboob.backends.youjizz.pages',
        'weboob.backends.youporn',
        'weboob.backends.youporn.pages',
        ],
    install_requires=[
        'weboob-core',
        ],
)

setup(
    name='weboob-weather-backends',
    version='0.1',
    description='Weboob backends implementing weather capability',
    author='Romain Bignon',
    author_email='weboob@lists.symlink.me',
    license='GPLv3',
    url='http://weboob.org/ICapWeather',
    namespace_packages = ['weboob', 'weboob.backends'],
    packages=[
        'weboob',
        'weboob.backends',
        'weboob.backends.yweather',
        ],
    install_requires=[
        'weboob-core',
        ],
)
