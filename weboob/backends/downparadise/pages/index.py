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

from weboob.tools.browser import BasePage
from .base import DownparadisePage

from weboob.capabilities.collection import Collection

__all__ = ['IndexPage']

class IndexPage(DownparadisePage):
    
    def on_loaded(self):
        self.collections = []
        self.parse_forums()

    def parse_forums(self):    
        """ Parse all forums """
        
        def do(id):
            self.browser.location(id)
            return self.browser.page.iter_threads()
        
        maintable = self.document.xpath("//div[@id='wrapheader']/table")[3]

        for line in maintable.xpath("./tr"):
            forums = line.xpath(".//a[@class='forumlink']")
            for fo in forums:
                coll = Collection()
                coll.title = fo.text.strip().encode('latin-1')
                coll.id = fo.get("href")
                for link in line.getiterator('a'):
                    if "subforum" in link.attrib.get('class', ""):
                        sub = Collection(title=link.text.strip().encode('latin-1'))
                        sub.id = link.get("href")
                        sub.children = do
                        coll.appendchild(sub)
                if not coll.children:
                    coll.children = do
                self.collections.append(coll)

    def get_collections(self):
        return self.collections
