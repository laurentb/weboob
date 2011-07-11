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

import sys
import os
from re import search, sub

from weboob.tools.application.repl import ReplApplication
from weboob.capabilities.base import NotLoaded
from weboob.capabilities.gallery import ICapGallery
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Galleroob']


class GalleryListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title')

    count = 0

    def flush(self):
        self.count = 0

    def format_dict(self, item):
        result = u'%s* (%s) %s%s' % (
                ReplApplication.BOLD,
                item['id'],
                item['title'],
                ReplApplication.NC)
        if item['cardinality'] is not NotLoaded:
            result += u' (%d pages)' % item['cardinality']
        if item['description'] is not NotLoaded:
            result += u'\n    %-70s' % item['description']
        return result


class Galleroob(ReplApplication):
    APPNAME = 'galleroob'
    VERSION = '0.8.4'
    COPYRIGHT = u'Copyright(C) 2011 Noé Rubinstein'
    DESCRIPTION = 'galleroob browses and downloads web image galleries'
    CAPS = ICapGallery
    EXTRA_FORMATTERS = {'gallery_list': GalleryListFormatter}
    COMMANDS_FORMATTERS = {'search': 'gallery_list'}

    def __init__(self, *args, **kwargs):
        ReplApplication.__init__(self, *args, **kwargs)

    def do_search(self, pattern=None):
        """
        search PATTERN

        List galleries matching a PATTERN.

        If PATTERN is not given, the command will list all the galleries
        """

        self.set_formatter_header(u'Search pattern: %s' %
            pattern if pattern else u'Latest galleries')
        for backend, gallery in self.do('iter_search_results',
                pattern=pattern, max_results=self.options.count):
            self.add_object(gallery)
            self.format(gallery)

    def do_download(self, line):
        """
        download ID [FIRST [FOLDER]]

        Download a gallery.

        Begins at page FIRST (default: 0) and saves to FOLDER (default: title)
        """
        _id, first, dest = self.parse_command_args(line, 3, 1)

        if first is None:
            first = 0
        else:
            first = int(first)

        gallery = None
        _id, backend = self.parse_id(_id)
        for backend, result in self.do('get_gallery', _id, backends=backend):
            if result:
                backend = backend
                gallery = result

        if not gallery:
            print >>sys.stderr, 'Gallery not found: %s' % _id
            return 3

        backend.fillobj(gallery, ('title',))
        if dest is None:
            dest = sub('/', ' ', gallery.title)

        print "Downloading to %s" % dest

        try:
            os.mkdir(dest)
        except OSError:
            pass # ignore error on existing directory
        os.chdir(dest) # fail here if dest couldn't be created

        i = 0
        for img in backend.iter_gallery_images(gallery):
            i += 1
            if i < first:
                continue

            backend.fillobj(img, ('url','data'))
            if img.data is None:
                backend.fillobj(img, ('url','data'))
                if img.data is None:
                    print >>sys.stderr, "Couldn't get page %d, exiting" % i
                    break

            ext = search(r"\.([^\.]{1,5})$", img.url)
            if ext:
                ext = ext.group(1)
            else:
                ext = "jpg"


            name = '%03d.%s' % (i, ext)
            print 'Writing file %s' % name

            with open(name, 'w') as f:
                f.write(img.data)

        os.chdir(os.path.pardir)

    def do_info(self, line):
        """
        info ID

        Get information about a gallery.
        """
        _id, = self.parse_command_args(line, 1, 1)

        gallery = self.get_object(_id, 'get_gallery')
        if not gallery:
            print >>sys.stderr, 'Gallery not found: %s' %  _id
            return 3
        self.format(gallery)
        self.flush()
