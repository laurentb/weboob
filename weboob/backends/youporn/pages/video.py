# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from .base import PornPage

class VideoPage(PornPage):
    def loaded(self):
        if not PornPage.loaded(self):
            return

        el = self.document.getroot().cssselect('div[id=download]')
        if el:
            self.url = el[0].cssselect('a')[0].attrib['href']
        else:
            self.url = None

        el = self.document.getroot().cssselect('h1')
        if el:
            self.title = unicode(el[0].getchildren()[0].tail).strip()
