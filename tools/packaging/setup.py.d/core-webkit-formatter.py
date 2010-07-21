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
    name='weboob-core-webkit-formatter',
    version='0.1',
    description='Weboob, Web Out Of Browsers - core library, WebKit formatter',
    author='Christophe Benz',
    author_email='weboob@lists.symlink.me',
    maintainer='Christophe Benz',
    maintainer_email='christophe.benz@gmail.com',
    license='GPLv3',
    url='http://www.weboob.org',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Internet',
        ],
    namespace_packages = [
        'weboob',
        'weboob.tools',
        'weboob.tools.application',
        'weboob.tools.application.formatters',
	],
    packages=[
        'weboob',
        'weboob.tools.application.formatters.webkit',
        ],
    # data_files=[
        # ('weboob/tools', ['weboob/tools/__init__.py']),
        # ('weboob/tools/application', ['weboob/tools/application/__init__.py']),
        # ('weboob/tools/application/formatters', ['weboob/tools/application/formatters/__init__.py']),
        # ],
    install_requires=[
        'weboob-core', # python-weboob-core
        # not Pypi packages:
        # Depends
        # python-gtk
        # python-webkit
        ],
)
