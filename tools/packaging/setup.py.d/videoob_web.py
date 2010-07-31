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
    name='weboob-videoob-web',
    version='0.1',
    description='Videoob-web, the Weboob video swiss-knife, web server version',
    long_description='Search for videos on many websites, and get info about them',
    author='Christophe Benz',
    author_email='weboob@lists.symlink.me',
    maintainer='Christophe Benz',
    maintainer_email='christophe.benz@gmail.com',
    license='GPLv3',
    url='http://www.weboob.org/VideoobWeb',
    namespace_packages = ['weboob', 'weboob.applications'],
    packages=[
        'weboob',
        'weboob.applications',
        'weboob.applications.videoob_web',
        'weboob.applications.videoob_web.public',
        'weboob.applications.videoob_web.templates',
        ],
    scripts=[
        'scripts/videoob-web-server',
        ],
    install_requires=[
        'weboob-backends-video', # python-weboob-backends-video
        'Mako', # python-mako
        'Routes', # python-routes
        'WebOb', # python-webob
        ],
)
