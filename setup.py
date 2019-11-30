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

    entry_points = {
        'console_scripts': [
            'boobank = weboob.applications.boobank:Boobank.run',
            'boobathon = weboob.applications.boobathon:Boobathon.run',
            'boobcoming = weboob.applications.boobill:Boobcoming.run',
            'boobill = weboob.applications.boobank:Boobill.run',
            'booblyrics = weboob.applications.booblyrics:Booblyrics.run',
            'boobmsg = weboob.applications.boobmsg:Boobmsg.run',
            'boobooks = weboob.applications.boobooks:Boobooks.run',
            'boobsize = weboob.applications.boobsize:Boobsize.run',
            'boobtracker = weboob.applications.boobtracker:BoobTracker.run',
            'boomoney = weboob.applications.boomoney:Boomoney.run',
            'cineoob = weboob.applications.cineoob:Cineoob.run',
            'comparoob = weboob.applications.comparoob:Comparoob.run',
            'cookboob = weboob.applications.cookboob:Cookboob.run',
            'flatboob = weboob.applications.flatboob:Flatboob.run',
            'galleroob = weboob.applications.galleroob:Galleroob.run',
            'geolooc = weboob.applications.geolooc:Geolooc.run',
            'handjoob = weboob.applications.handjoob:Handjoob.run',
            'havedate = weboob.applications.havedate:HaveDate.run',
            'monboob = weboob.applications.monboob:Monboob.run',
            'parceloob = weboob.applications.parceloob:Parceloob.run',
            'pastoob = weboob.applications.pastoob:Pastoob.run',
            'radioob = weboob.applications.radioob:Radioob.run',
            'shopoob = weboob.applications.shopoob:Shopoob.run',
            'suboob = weboob.applications.suboob:Suboob.run',
            'translaboob = weboob.applications.translaboob:Translaboob.run',
            'traveloob = weboob.applications.traveloob:Traveloob.run',
            'videoob = weboob.applications.videoob:Videoob.run',
            'webcontentedit = weboob.applications.webcontentedit:WebContentEdit.run',
            'weboob-cli = weboob.applications.weboobcli:WeboobCli.run',
            'weboob-config = weboob.applications.weboobcfg:WeboobCfg.run',
            'weboob-debug = weboob.applications.weboobdebug:WeboobDebug.run',
            'weboob-repos = weboob.applications.weboobrepos:WeboobRepos.run',
            'weboorrents = weboob.applications.weboorrents:Weboorrents.run',
            'wetboobs = weboob.applications.wetboobs:WetBoobs.run',
            'weboob = weboob.applications.weboobmain:WeboobMain.run',
        ],
    }

    data_files = [
        ('share/man/man1', glob.glob('man/*')),
    ]

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
        'Babel',
    ]

    try:
        if sys.argv[1] == 'requirements':
            print('\n'.join(requirements))
            sys.exit(0)
    except IndexError:
        pass

    setup(
        name='weboob',
        version='1.6',
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
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python',
            'Topic :: Communications :: Email',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Internet :: WWW/HTTP :: Browsers',
            'Topic :: Software Development :: Libraries :: Application Frameworks',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Text Processing :: Markup :: HTML',
        ],

        packages=packages,
        entry_points=entry_points,
        data_files=data_files,

        install_requires=requirements,
        python_requires='>=3.5',
        tests_require=[
            'flake8',
            'nose',
            'xunitparser',
            'coverage',
        ],
    )


if os.getenv('WEBOOB_SETUP'):
    args = os.getenv('WEBOOB_SETUP').split()
else:
    args = sys.argv[1:]

sys.argv = [sys.argv[0]] + args

install_weboob()
