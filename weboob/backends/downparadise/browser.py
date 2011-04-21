# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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
import urllib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.collection import Collection, CollectionNotFound

from .pages import IndexPage, UcpPage, ViewforumPage


class Downparadise(BaseBrowser):
    DOMAIN = 'forum.downparadise.ws'
    PROTOCOL = 'http'
    PAGES = {'http://forum.downparadise.ws/index.php'       : IndexPage,
             'http://forum.downparadise.ws/ucp.php.*'       : UcpPage,
             'http://forum.downparadise.ws/viewforum.php.*' : ViewforumPage,
            }

    def home(self):
        return self.location('http://forum.downparadise.ws/index.php')

    def login(self):
        data = {'login':	'Connexion',
                'password':	self.password,
                'username': self.username}
        self.location('http://forum.downparadise.ws/ucp.php?mode=login', urllib.urlencode(data) , no_login=True)
        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def is_logged(self):
        return (self.page and self.page.is_logged())

    def iter_forums(self, splited_path):
        if not self.is_on_page(IndexPage):
            self.home()

        collections = self.page.get_collections()

        def walk_res(path, collections):
            if len(path) == 0 or not isinstance(collections, (list, Collection)):
                return collections
            i = path[0]
            if i not in [collection.title for collection in collections]:
                raise CollectionNotFound()

            return walk_res(path[1:], [collection.children for collection in collections if collection.title == i][0])

        return walk_res(splited_path, collections)
