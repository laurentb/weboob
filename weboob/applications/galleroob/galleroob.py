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
    VERSION = '0.8'
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
        _id, dest, first = self.parse_command_args(line, 3, 2)

        if first is None:
            first = 0
        else:
            first = int(first)

        gallery = None
        for backend, result in self.do('get_gallery', _id):
            if result:
                backend = backend
                gallery = result

        if not gallery:
            print 'Gallery not found: %s' % _id
            return 1

        backend.fillobj(gallery, ('title',))
        if dest is None:
            dest = sub('/', ' ', gallery.title)

        print "Downloading to %s" % dest

        os.system('mkdir "%s"' % dest)

        i = 0
        for img in backend.iter_gallery_images(gallery):
            i += 1
            if i < first:
                continue

            backend.fillobj(img, ('url','data'))
            if img.data is None:
                backend.fillobj(img, ('url','data'))
                if img.data is None:
                    print "Couldn't get page %d, exiting" % i
                    break

            ext = search(r"\.([^\.]{1,5})$", img.url)
            if ext:
                ext = ext.group(1)
            else:
                ext = "jpg"


            name = '%s/%03d.%s' % (dest, i, ext)
            print 'Writing file %s' % name

            with open(name, 'w') as f:
                f.write(img.data)

