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
from weboob.capabilities.video import Video

class IndexPage(PornPage):
    def iter_videos(self):
        for h1 in self.document.getiterator('h1'):
            a = h1.find('a')
            if a is None:
                continue

            url = a.attrib['href']
            _id = url[len('/watch/'):]
            _id = _id[:_id.find('/')]
            title = a.text
            yield Video(int(_id), title)
