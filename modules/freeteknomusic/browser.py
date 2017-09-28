# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.browser import PagesBrowser, URL

from .pages import FolderPage


class FreeteknomusicBrowser(PagesBrowser):
    BASEURL = 'http://archive.freeteknomusic.org/'

    folder = URL('/', FolderPage)

    def ls_content(self, split_path):
        self.location('/' + '/'.join(split_path))
        for el in self.page.iter_dirs():
            yield el
        for el in self.page.iter_files():
            yield el

    def get_file(self, id):
        split_path = id.split('/')[:-1]
        self.location('/' + '/'.join(split_path))
        id = 'audio.%s' % id
        for el in self.page.iter_files():
            if el.id == id:
                return el
