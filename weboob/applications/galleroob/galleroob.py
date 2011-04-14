# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Noé Rubinstein
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import subprocess
import sys
import os
from weboob.tools.application.repl import ReplApplication
from weboob.capabilities.gallery import ICapGallery
from re import search

__all__ = ['Galleroob']

class Galleroob(ReplApplication):
    APPNAME = 'galleroob'
    VERSION = '0.0'
    COPYTIGHT = 'Copyright(C) 2011 Noé Rubinstein'
    DESCRIPTION = 'galleroob browses and downloads web image galleries'
    CAPS = ICapGallery

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)

    def do_download(self, line):
        """
        download ID FOLDER

        Download a gallery
        """
        _id, dest = self.parse_command_args(line, 2, 2)
        gallery = None
        for backend, result in self.do('get_gallery', _id):
            if result:
                backend = backend
                gallery = result

        if not gallery:
            print 'Gallery not found: %s' % _id
            return 1

        with open('/dev/null', 'w') as devnull:
            process = subprocess.Popen(['which', 'wget'], stdout=devnull)
            if process.wait() != 0:
                print >>sys.stderr, 'Please install "wget"'
                return 1

        os.system('mkdir "%s"' % dest)

        i = 0
        for img in backend.iter_gallery_images(gallery):
            backend.fillobj(img, ('url',))

            ext = search(r"\.([^\.]{1,5})$", img.url)
            if ext:
                ext = ext.group(1)
            else:
                ext = "jpg"

            i += 1

            os.system('wget "%s" -O "%s/%03d.%s"' % (img.url, dest, i, ext))


